"""
memory.py - 대화 기억/맥락 관리 모듈
최근 대화 히스토리와 중요 이벤트를 관리합니다.
인메모리 방식을 사용합니다.
"""

from __future__ import annotations

import warnings
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Optional

from loguru import logger


class ConversationMemory:
    """대화 히스토리와 중요 이벤트를 관리하는 메모리 클래스."""

    def __init__(
        self,
        window_size: int = 50,
        backend: str = "inmemory",
    ) -> None:
        """
        Args:
            window_size: 유지할 최근 대화 수 (슬라이딩 윈도우)
            backend: 저장 방식 (현재 "inmemory"만 지원)
        """
        self.window_size = window_size
        self.backend = backend
        self._history: Deque[dict[str, Any]] = deque(maxlen=window_size)
        self._important_events: list[dict[str, Any]] = []

    # ── 대화 히스토리 ─────────────────────────────────────────────────

    async def save(self, text: str, context: Optional[dict[str, Any]] = None) -> None:
        """발화한 텍스트와 컨텍스트를 메모리에 저장합니다."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "assistant",
            "content": text,
            "context_summary": self._summarize_context(context),
        }
        self._history.append(entry)

    async def save_chat(self, username: str, message: str) -> None:
        """시청자 채팅 메시지를 히스토리에 저장합니다."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "user",
            "username": username,
            "content": message,
        }
        self._history.append(entry)

    async def save_important_event(self, event_type: str, data: dict[str, Any]) -> None:
        """후원, 구독 같은 중요 이벤트를 장기 기억에 저장합니다."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "data": data,
        }
        self._important_events.append(event)
        logger.debug(f"중요 이벤트 저장: {event_type}")

    def get_recent_history(self, n: Optional[int] = None) -> list[dict[str, Any]]:
        """최근 대화 히스토리를 반환합니다."""
        history = list(self._history)
        if n is not None:
            return history[-n:]
        return history

    def get_important_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """최근 중요 이벤트 목록을 반환합니다."""
        return self._important_events[-limit:]

    def to_messages(self) -> list[dict[str, str]]:
        """LLM API 형식의 메시지 목록으로 변환합니다."""
        messages = []
        for entry in self._history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        return messages

    def to_openai_messages(self) -> list[dict[str, str]]:
        """하위 호환성을 위해 유지되는 메서드. to_messages()를 사용하세요.

        .. deprecated::
            to_openai_messages() 대신 to_messages()를 사용하세요.
        """
        warnings.warn(
            "to_openai_messages()는 더 이상 사용되지 않습니다. to_messages()를 사용하세요.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.to_messages()

    def clear(self) -> None:
        """메모리를 초기화합니다."""
        self._history.clear()
        self._important_events.clear()
        logger.info("메모리 초기화 완료")

    @staticmethod
    def _summarize_context(context: Optional[dict[str, Any]]) -> str:
        """컨텍스트 딕셔너리를 간단한 요약 문자열로 변환합니다."""
        if not context:
            return ""
        parts = []
        if "viewer_count" in context:
            parts.append(f"시청자:{context['viewer_count']}명")
        if "recent_chat" in context:
            parts.append(f"최근채팅:{len(context['recent_chat'])}건")
        return ", ".join(parts)
