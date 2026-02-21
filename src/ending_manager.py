"""
ending_manager.py - 자연스러운 방종 관리 모듈
갑자기 방송을 끊지 않고 3단계로 자연스럽게 방종합니다.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from src.broadcast_loop import BroadcastLoop


class EndingManager:
    """
    3단계 자연스러운 방종 프로세스 관리자.

    1단계: 방종 분위기 전환 (종료 15분 전) - WIND_DOWN
    2단계: 방종 예고 (종료 5분 전) - ENDING_ANNOUNCE
    3단계: 최종 인사 및 종료 - FINAL_GOODBYE
    """

    def __init__(
        self,
        broadcast_loop: "BroadcastLoop",
        ending_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            broadcast_loop: 방송 루프 인스턴스
            ending_config: schedule.yaml의 ending 섹션 설정
        """
        self.broadcast_loop = broadcast_loop
        cfg = ending_config or {}
        self.wind_down_minutes: int = cfg.get("wind_down_minutes", 15)
        self.final_goodbye_seconds: int = cfg.get("final_goodbye_seconds", 30)

    async def run(self) -> None:
        """
        전체 방종 프로세스를 순서대로 실행합니다.

        방종 프로세스 타임라인:
        t=0        : 1단계 시작 (방종 분위기 전환)
        t=10분     : 2단계 시작 (방종 예고)
        t=15분     : 3단계 (최종 인사)
        t=15분+30초: 방송 종료
        """
        logger.info("🌙 방종 1단계: 분위기 전환 시작")
        await self._phase_wind_down()

        # 2단계까지 대기 (방종 준비 시간 - 5분)
        phase2_wait = max(0, (self.wind_down_minutes - 5) * 60)
        await asyncio.sleep(phase2_wait)

        logger.info("🌙 방종 2단계: 방종 예고")
        await self._phase_ending_announce()

        # 3단계까지 5분 대기
        await asyncio.sleep(5 * 60)

        logger.info("🌙 방종 3단계: 최종 인사")
        await self._phase_final_goodbye()

        # 최종 인사 후 대기
        await asyncio.sleep(self.final_goodbye_seconds)

        logger.info("✅ 방종 프로세스 완료")

    async def _phase_wind_down(self) -> None:
        """1단계: 방종 분위기 전환 - AI에게 마무리 분위기를 유도합니다."""
        self.broadcast_loop.set_ending_mode("wind_down")
        # 방종 분위기 발화를 한 번 즉시 트리거
        await self._trigger_ending_speech("wind_down")

    async def _phase_ending_announce(self) -> None:
        """2단계: 방종 예고 - 시청자에게 방종을 알립니다."""
        self.broadcast_loop.set_ending_mode("ending_announce")
        await self._trigger_ending_speech("ending_announce")

    async def _phase_final_goodbye(self) -> None:
        """3단계: 최종 인사 - 마지막 작별 인사를 합니다."""
        self.broadcast_loop.set_ending_mode("final_goodbye")
        await self._trigger_ending_speech("final_goodbye")

        # OBS 엔딩 화면 전환 시도
        try:
            await self.broadcast_loop.obs.switch_to_ending_scene()
        except Exception as e:
            logger.warning(f"OBS 엔딩 화면 전환 실패 (무시): {e}")

    async def _trigger_ending_speech(self, ending_type: str) -> None:
        """
        방종 관련 발화를 즉시 생성하고 출력합니다.

        Args:
            ending_type: "wind_down", "ending_announce", "final_goodbye" 중 하나
        """
        from src.brain.action_decider import Action, ActionType

        action_map = {
            "wind_down": ActionType.WIND_DOWN,
            "ending_announce": ActionType.ENDING_ANNOUNCE,
            "final_goodbye": ActionType.FINAL_GOODBYE,
        }
        action_type = action_map.get(ending_type, ActionType.WIND_DOWN)

        try:
            context = await self.broadcast_loop.perception.get_current_context()
            # 방종 상태 컨텍스트 추가
            context["ending_mode"] = ending_type
            context["broadcast_mode"] = self.broadcast_loop.current_mode

            action = Action(action_type=action_type, priority=10)
            speech_text = await self.broadcast_loop.brain.generate_speech(action, context)

            if speech_text:
                logger.info(f"🗣 방종 발화 ({ending_type}): {speech_text[:80]}")
                await self.broadcast_loop.voice.speak_realtime(speech_text)
                await self.broadcast_loop.brain.memory.save(speech_text, context)
        except Exception as e:
            logger.error(f"방종 발화 생성 오류: {e}")
