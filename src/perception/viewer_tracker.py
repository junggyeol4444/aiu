"""
viewer_tracker.py - 시청자 수 추적 모듈
시청자 수 변화를 추적하고 급격한 변화를 감지합니다.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from loguru import logger


class ViewerTracker:
    """실시간 시청자 수를 추적하는 클래스."""

    def __init__(self, platform_config: dict[str, Any]) -> None:
        self.config = platform_config
        self.platform = platform_config.get("active", "youtube")
        self._current_count: int = 0
        self._previous_count: int = 0
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

        # 급격한 변화 감지 임계값 (%)
        self._surge_threshold = 0.5   # 50% 이상 증가 = 급등
        self._drop_threshold = 0.3    # 30% 이상 감소 = 급감

    async def start(self) -> None:
        """시청자 수 추적을 시작합니다."""
        self._running = True
        self._task = asyncio.create_task(self._track_loop())
        logger.info("시청자 수 추적 시작")

    async def stop(self) -> None:
        """시청자 수 추적을 중단합니다."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def current_count(self) -> int:
        """현재 시청자 수를 반환합니다."""
        return self._current_count

    def get_change_status(self) -> str:
        """
        시청자 수 변화 상태를 반환합니다.

        Returns:
            "surge" (급등), "drop" (급감), "stable" (안정)
        """
        if self._previous_count == 0:
            return "stable"

        ratio = (self._current_count - self._previous_count) / self._previous_count
        if ratio >= self._surge_threshold:
            return "surge"
        if ratio <= -self._drop_threshold:
            return "drop"
        return "stable"

    async def _track_loop(self) -> None:
        """주기적으로 시청자 수를 갱신하는 루프."""
        while self._running:
            try:
                count = await self._fetch_viewer_count()
                self._previous_count = self._current_count
                self._current_count = count

                status = self.get_change_status()
                if status != "stable":
                    logger.info(
                        f"시청자 수 변화 감지: {self._previous_count} → {count} ({status})"
                    )

                await asyncio.sleep(30)  # 30초마다 갱신
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"시청자 수 조회 오류: {e}")
                await asyncio.sleep(30)

    async def _fetch_viewer_count(self) -> int:
        """플랫폼 API를 통해 현재 시청자 수를 조회합니다."""
        if self.platform == "youtube":
            return await self._fetch_youtube_viewers()
        # Twitch 등 추가 플랫폼은 추후 구현
        return self._current_count

    async def _fetch_youtube_viewers(self) -> int:
        """YouTube API에서 현재 동시 시청자 수를 조회합니다."""
        try:
            from googleapiclient.discovery import build  # type: ignore

            yt_config = self.config.get("youtube", {})
            api_key = os.environ.get(yt_config.get("api_key_env", "YOUTUBE_API_KEY"), "")
            channel_id = os.environ.get(
                yt_config.get("channel_id_env", "YOUTUBE_CHANNEL_ID"), ""
            )

            if not api_key or not channel_id:
                return self._current_count

            service = build("youtube", "v3", developerKey=api_key)
            # 라이브 방송의 동시 시청자 수 조회
            request = service.videos().list(
                part="liveStreamingDetails",
                id=channel_id,
            )
            response = request.execute()
            items = response.get("items", [])
            if items:
                details = items[0].get("liveStreamingDetails", {})
                count_str: str = details.get("concurrentViewers", "0")
                return int(count_str)
        except Exception as e:
            logger.warning(f"YouTube 시청자 수 조회 실패: {e}")

        return self._current_count
