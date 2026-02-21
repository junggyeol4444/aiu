"""
context_builder.py - 상황 컨텍스트 생성 모듈
모든 인지 정보를 종합하여 AI Brain에 전달할 단일 컨텍스트 객체를 생성합니다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from src.perception.chat_listener import ChatListener
from src.perception.event_detector import EventDetector
from src.perception.viewer_tracker import ViewerTracker


class ContextBuilder:
    """
    모든 인지 소스(채팅, 시청자, 이벤트)를 종합하여
    AI Brain이 소비할 컨텍스트 딕셔너리를 생성합니다.
    """

    def __init__(
        self,
        chat_listener: ChatListener,
        viewer_tracker: ViewerTracker,
        event_detector: EventDetector,
        external_collector: Optional[Any] = None,
    ) -> None:
        self.chat_listener = chat_listener
        self.viewer_tracker = viewer_tracker
        self.event_detector = event_detector
        self._broadcast_start_time: Optional[datetime] = None
        # 방송 모드 및 방종 상태 (broadcast_loop에서 주입)
        self.broadcast_mode: str = "talk"
        self.ending_mode: str = ""
        self.game_name: str = ""

    def set_broadcast_started(self) -> None:
        """방송 시작 시간을 기록합니다."""
        self._broadcast_start_time = datetime.now(timezone.utc)

    def _get_elapsed_time_str(self) -> str:
        """방송 경과 시간을 '시간 분' 형식 문자열로 반환합니다."""
        if self._broadcast_start_time is None:
            return ""
        elapsed = datetime.now(timezone.utc) - self._broadcast_start_time
        total_minutes = int(elapsed.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        return f"{minutes}분"

    async def get_current_context(self) -> dict[str, Any]:
        """
        현재 방송 상황의 전체 컨텍스트를 수집하여 반환합니다.

        Returns:
            AI Brain에 전달할 컨텍스트 딕셔너리
        """
        context: dict[str, Any] = {
            # 시청자 정보
            "viewer_count": self.viewer_tracker.current_count,
            "viewer_change": self.viewer_tracker.get_change_status(),

            # 최근 채팅 메시지 (최근 10개)
            "recent_chat": self.chat_listener.get_recent_messages(n=10),

            # 대기 중인 이벤트 (후원, 구독 등)
            "events": self.event_detector.get_pending_events(),

            # 방송 경과 시간
            "elapsed_time": self._get_elapsed_time_str(),

            # 현재 방송 모드 (talk / game)
            "broadcast_mode": self.broadcast_mode,

            # 게임 이름 (게임 모드일 때)
            "game_name": self.game_name,

            # 방종 상태
            "ending_mode": self.ending_mode,
        }

        logger.debug(
            f"컨텍스트 생성: 시청자={context['viewer_count']}명, "
            f"채팅={len(context['recent_chat'])}건, "
            f"이벤트={len(context['events'])}건, "
            f"모드={context['broadcast_mode']}"
        )

        # 채팅 큐를 비워 다음 루프에서 중복 처리 방지
        self.chat_listener.clear_queue()

        return context
