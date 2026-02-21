"""
memory.py - 대화 기억/맥락 관리 모듈
최근 대화 히스토리와 중요 이벤트를 관리합니다.
Redis 또는 인메모리 방식을 지원합니다.
"""

from __future__ import annotations

import json
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
        redis_url: Optional[str] = None,
    ) -> None:
        """
        Args:
            window_size: 유지할 최근 대화 수 (슬라이딩 윈도우)
            backend: 저장 방식 ("inmemory" 또는 "redis")
            redis_url: Redis 연결 URL (redis 백엔드일 때만 사용)
        """
        self.window_size = window_size
        self.backend = backend
        self._history: Deque[dict[str, Any]] = deque(maxlen=window_size)
        self._important_events: list[dict[str, Any]] = []
        self._redis_client: Any = None

        if backend == "redis" and redis_url:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: str) -> None:
        """Redis 클라이언트를 초기화합니다."""
        try:
            import redis  # type: ignore

            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info("Redis 메모리 백엔드 연결 성공")
        except Exception as e:
            logger.warning(f"Redis 연결 실패, 인메모리로 전환: {e}")
            self._redis_client = None

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

        if self._redis_client:
            try:
                self._redis_client.rpush("history", json.dumps(entry, ensure_ascii=False))
                self._redis_client.ltrim("history", -self.window_size, -1)
            except Exception as e:
                logger.warning(f"Redis 저장 오류: {e}")

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

    def to_openai_messages(self) -> list[dict[str, str]]:
        """OpenAI API 형식의 메시지 목록으로 변환합니다."""
        messages = []
        for entry in self._history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        return messages

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
