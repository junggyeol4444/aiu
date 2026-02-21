"""
event_detector.py - 이벤트 감지 모듈
후원/도네이션, 구독/팔로우 등 방송 이벤트를 감지합니다.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Optional

from loguru import logger


@dataclass
class BroadcastEvent:
    """방송 이벤트를 나타내는 데이터 클래스."""

    type: str                              # donation, subscription, follow, stream_start 등
    username: Optional[str] = None        # 이벤트 발생자 이름
    amount: Optional[float] = None        # 후원 금액
    message: Optional[str] = None        # 후원 메시지
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "username": self.username,
            "amount": self.amount,
            "message": self.message,
            **self.metadata,
        }


class EventDetector:
    """방송 이벤트를 감지하고 큐에 저장하는 클래스."""

    def __init__(self) -> None:
        self._event_queue: Deque[BroadcastEvent] = deque(maxlen=50)

    def add_event(self, event: BroadcastEvent) -> None:
        """이벤트를 큐에 추가합니다."""
        self._event_queue.append(event)
        logger.info(f"이벤트 감지: {event.type} - {event.username}")

    def get_pending_events(self) -> list[dict[str, Any]]:
        """대기 중인 이벤트 목록을 반환하고 큐를 비웁니다."""
        events = [e.to_dict() for e in self._event_queue]
        self._event_queue.clear()
        return events

    def has_events(self) -> bool:
        """처리 대기 중인 이벤트가 있는지 확인합니다."""
        return len(self._event_queue) > 0

    # ── 이벤트 생성 편의 메서드 ──────────────────────────────────────

    def add_donation(
        self, username: str, amount: float, message: str = ""
    ) -> None:
        """후원 이벤트를 추가합니다."""
        self.add_event(
            BroadcastEvent(
                type="donation",
                username=username,
                amount=amount,
                message=message,
            )
        )

    def add_subscription(self, username: str, months: int = 1) -> None:
        """구독 이벤트를 추가합니다."""
        self.add_event(
            BroadcastEvent(
                type="subscription",
                username=username,
                metadata={"months": months},
            )
        )

    def add_follow(self, username: str) -> None:
        """팔로우 이벤트를 추가합니다."""
        self.add_event(
            BroadcastEvent(
                type="follow",
                username=username,
            )
        )

    def signal_stream_start(self) -> None:
        """방송 시작 이벤트를 추가합니다."""
        self.add_event(BroadcastEvent(type="stream_start"))
