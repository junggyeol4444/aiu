"""
context_builder.py - 상황 컨텍스트 생성 모듈
모든 인지 정보를 종합하여 AI Brain에 전달할 단일 컨텍스트 객체를 생성합니다.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from src.perception.chat_listener import ChatListener
from src.perception.event_detector import EventDetector
from src.perception.external_info import ExternalInfoCollector
from src.perception.viewer_tracker import ViewerTracker


class ContextBuilder:
    """
    모든 인지 소스(채팅, 시청자, 이벤트, 외부 정보)를 종합하여
    AI Brain이 소비할 컨텍스트 딕셔너리를 생성합니다.
    """

    def __init__(
        self,
        chat_listener: ChatListener,
        viewer_tracker: ViewerTracker,
        event_detector: EventDetector,
        external_collector: ExternalInfoCollector,
    ) -> None:
        self.chat_listener = chat_listener
        self.viewer_tracker = viewer_tracker
        self.event_detector = event_detector
        self.external_collector = external_collector

    async def get_current_context(self) -> dict[str, Any]:
        """
        현재 방송 상황의 전체 컨텍스트를 수집하여 반환합니다.

        Returns:
            AI Brain에 전달할 컨텍스트 딕셔너리
        """
        # 날씨와 트렌드는 병렬로 가져옴
        import asyncio
        weather_task = asyncio.create_task(self.external_collector.get_weather())
        trends_task = asyncio.create_task(self.external_collector.get_trending_topics())

        weather = await weather_task
        trending_topics = await trends_task

        context: dict[str, Any] = {
            # 시청자 정보
            "viewer_count": self.viewer_tracker.current_count,
            "viewer_change": self.viewer_tracker.get_change_status(),

            # 최근 채팅 메시지
            "recent_chat": self.chat_listener.get_recent_messages(n=5),

            # 대기 중인 이벤트 (후원, 구독 등)
            "events": self.event_detector.get_pending_events(),

            # 외부 정보
            "weather": weather,
            "trending_topics": trending_topics,
        }

        logger.debug(
            f"컨텍스트 생성: 시청자={context['viewer_count']}명, "
            f"채팅={len(context['recent_chat'])}건, "
            f"이벤트={len(context['events'])}건"
        )

        # 채팅 큐를 비워 다음 루프에서 중복 처리 방지
        self.chat_listener.clear_queue()

        return context
