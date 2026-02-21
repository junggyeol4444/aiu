"""
scheduler.py - 방송 스케줄링 모듈
설정된 시간에 자동으로 방송을 시작하고 종료하는 스케줄러입니다.
asyncio 기반으로 구현되어 외부 의존성이 없습니다.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml
from loguru import logger

if TYPE_CHECKING:
    from src.broadcast_loop import BroadcastLoop

# 요일 이름 → weekday() 인덱스 매핑 (0=월요일)
_DAY_MAP: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class BroadcastScheduler:
    """
    방송 스케줄러.

    schedule.yaml 설정에 따라 지정된 시간에 방송을 자동 시작/종료합니다.
    asyncio 기반으로 구현되어 cron 같은 외부 의존성이 없습니다.
    """

    def __init__(
        self,
        broadcast_loop: "BroadcastLoop",
        schedule_config_path: str = "config/schedule.yaml",
    ) -> None:
        """
        Args:
            broadcast_loop: 방송 루프 인스턴스
            schedule_config_path: 스케줄 설정 파일 경로
        """
        self.broadcast_loop = broadcast_loop
        self._config = self._load_config(schedule_config_path)
        self._running = False
        self._broadcast_end_time: Optional[datetime] = None

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        """스케줄 설정 파일을 로드합니다."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"스케줄 설정 파일 없음: {path}. 기본값 사용.")
            return {}
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def schedule_cfg(self) -> dict[str, Any]:
        """schedule 섹션 설정을 반환합니다."""
        return self._config.get("schedule", {})

    @property
    def enabled(self) -> bool:
        """스케줄러 활성화 여부."""
        return self.schedule_cfg.get("enabled", False)

    def get_next_broadcast_time(self) -> Optional[datetime]:
        """
        현재 시간 기준으로 다음 방송 시작 시간을 계산합니다.

        Returns:
            다음 방송 시작 datetime, 스케줄이 없으면 None
        """
        start_times = self.schedule_cfg.get("start_times", [])
        if not start_times:
            return None

        now = datetime.now()
        candidates: list[datetime] = []

        for entry in start_times:
            day_name = entry.get("day", "").lower()
            time_str = entry.get("time", "00:00")
            day_idx = _DAY_MAP.get(day_name)
            if day_idx is None:
                continue

            try:
                hour, minute = map(int, time_str.split(":"))
            except ValueError:
                logger.warning(f"잘못된 시간 형식: {time_str}")
                continue

            # 이번 주 해당 요일의 방송 시간 계산
            days_ahead = (day_idx - now.weekday()) % 7
            candidate = now.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            ) + timedelta(days=days_ahead)

            # 이미 지났으면 다음 주 같은 시간
            if candidate <= now:
                candidate += timedelta(weeks=1)

            candidates.append(candidate)

        if not candidates:
            return None

        return min(candidates)

    def get_broadcast_duration_seconds(self) -> int:
        """
        설정된 방송 시간(초)을 랜덤으로 반환합니다.

        Returns:
            방송 지속 시간 (초)
        """
        duration_cfg = self.schedule_cfg.get("broadcast_duration", {})
        min_min = duration_cfg.get("min_minutes", 360)
        max_min = duration_cfg.get("max_minutes", 420)
        minutes = random.randint(min_min, max_min)
        return minutes * 60

    def get_schedule_summary(self) -> list[dict[str, str]]:
        """
        현재 스케줄 설정 요약을 반환합니다.
        대시보드에서 스케줄 표시에 사용됩니다.

        Returns:
            요일, 시간 딕셔너리 리스트
        """
        return [
            {"day": e.get("day", ""), "time": e.get("time", "")}
            for e in self.schedule_cfg.get("start_times", [])
        ]

    async def run(self) -> None:
        """
        스케줄 루프를 시작합니다.

        다음 방송 시간까지 대기 → 방송 시작 → 방송 시간 경과 후 방종 시작을 반복합니다.
        """
        if not self.enabled:
            logger.info("스케줄러 비활성화 상태입니다.")
            return

        self._running = True
        logger.info("📅 방송 스케줄러 시작")

        while self._running:
            next_time = self.get_next_broadcast_time()
            if next_time is None:
                logger.warning("다음 방송 스케줄이 없습니다. 스케줄러를 종료합니다.")
                break

            wait_seconds = (next_time - datetime.now()).total_seconds()
            logger.info(
                f"다음 방송: {next_time.strftime('%Y-%m-%d %H:%M')} "
                f"({int(wait_seconds // 3600)}시간 {int((wait_seconds % 3600) // 60)}분 후)"
            )

            # 방송 시작 시간까지 대기 (1분마다 체크)
            while wait_seconds > 0 and self._running:
                await asyncio.sleep(min(60, wait_seconds))
                wait_seconds = (next_time - datetime.now()).total_seconds()

            if not self._running:
                break

            # 방송 시작
            duration = self.get_broadcast_duration_seconds()
            self._broadcast_end_time = datetime.now() + timedelta(seconds=duration)
            logger.info(
                f"🎙 스케줄 방송 시작! 예정 종료: "
                f"{self._broadcast_end_time.strftime('%H:%M')} "
                f"({duration // 60}분)"
            )

            # 방송 루프와 방종 타이머를 동시에 실행
            await asyncio.gather(
                self._run_broadcast_with_ending(duration),
            )

    async def _run_broadcast_with_ending(self, duration_seconds: int) -> None:
        """
        방송을 시작하고 지정된 시간 후 방종 프로세스를 시작합니다.

        Args:
            duration_seconds: 방송 지속 시간 (초)
        """
        from src.ending_manager import EndingManager

        ending_cfg = self.schedule_cfg.get("ending", {})
        wind_down_minutes = ending_cfg.get("wind_down_minutes", 15)

        # 방송 시작
        broadcast_task = asyncio.create_task(self.broadcast_loop.start())

        # 방종 준비 시작 시간까지 대기
        wind_down_wait = duration_seconds - wind_down_minutes * 60
        if wind_down_wait > 0:
            await asyncio.sleep(wind_down_wait)

        if not self._running:
            broadcast_task.cancel()
            return

        # 방종 프로세스 시작
        logger.info("🌙 방종 프로세스 시작")
        ending_manager = EndingManager(self.broadcast_loop, ending_cfg)
        await ending_manager.run()

        # 방송 중단
        broadcast_task.cancel()
        await self.broadcast_loop.stop()

    def stop(self) -> None:
        """스케줄러를 중단합니다."""
        self._running = False
        logger.info("스케줄러 중단")
