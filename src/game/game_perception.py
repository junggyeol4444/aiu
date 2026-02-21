"""
game_perception.py - 게임 상황 인지 모듈
게임 화면 캡처, 프로세스 상태 모니터링, 게임 이벤트 감지를 담당합니다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger


class GamePerception:
    """
    게임 방송 모드에서 게임 상황을 인지하는 클래스.

    - 게임 화면 캡처 (screenshot) → 간단한 상태 파악
    - 게임 프로세스 상태 모니터링 (실행 중/종료됨)
    - 게임 관련 이벤트 감지 (키워드 기반)
    """

    def __init__(self, game_config: dict[str, Any]) -> None:
        """
        Args:
            game_config: settings.yaml의 game 섹션 설정
        """
        self._speech_cfg = game_config.get("speech", {})
        self._reaction_keywords: list[str] = self._speech_cfg.get(
            "reaction_keywords",
            ["kill", "death", "win", "lose", "목표", "클리어"],
        )
        self._last_screenshot_time: Optional[datetime] = None
        self._pending_events: list[dict[str, Any]] = []

    def capture_game_state(self) -> dict[str, Any]:
        """
        게임 화면을 캡처하여 간단한 상태 정보를 반환합니다.

        스크린샷 기능이 없는 환경에서는 기본값을 반환합니다.

        Returns:
            게임 상태 딕셔너리
        """
        state: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screenshot_available": False,
            "status": "running",
        }

        try:
            # PIL이 설치된 경우 스크린샷 시도
            from PIL import ImageGrab  # type: ignore

            screenshot = ImageGrab.grab()
            state["screenshot_available"] = True
            state["width"] = screenshot.width
            state["height"] = screenshot.height
            self._last_screenshot_time = datetime.now(timezone.utc)
            logger.debug("게임 스크린샷 캡처 완료")
        except ImportError:
            logger.debug("PIL 없음 - 스크린샷 캡처 생략")
        except Exception as e:
            logger.debug(f"스크린샷 캡처 실패: {e}")

        return state

    def detect_events_from_chat(self, chat_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        채팅 메시지에서 게임 관련 이벤트를 감지합니다.
        반응 키워드가 포함된 채팅에 우선 반응합니다.

        Args:
            chat_messages: 최근 채팅 메시지 목록

        Returns:
            감지된 게임 이벤트 목록
        """
        events: list[dict[str, Any]] = []
        for msg in chat_messages:
            content = msg.get("message", "").lower()
            for keyword in self._reaction_keywords:
                if keyword.lower() in content:
                    events.append({
                        "type": "game_chat_keyword",
                        "keyword": keyword,
                        "message": msg.get("message", ""),
                        "username": msg.get("username", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    break  # 메시지당 하나의 이벤트만
        return events

    def add_game_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        게임 이벤트를 큐에 추가합니다.

        Args:
            event_type: 이벤트 유형 (예: "kill", "death", "win")
            data: 이벤트 상세 데이터
        """
        event = {
            "type": f"game_{event_type}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._pending_events.append(event)
        logger.debug(f"게임 이벤트 추가: {event_type}")

    def get_pending_events(self) -> list[dict[str, Any]]:
        """대기 중인 게임 이벤트를 반환하고 큐를 비웁니다."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    async def get_game_context(
        self,
        game_info: dict[str, Any],
        chat_messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        게임 관련 컨텍스트 정보를 수집하여 반환합니다.
        broadcast_loop의 컨텍스트에 추가됩니다.

        Args:
            game_info: 현재 게임 정보 (game_manager.current_game)
            chat_messages: 최근 채팅 메시지

        Returns:
            게임 컨텍스트 딕셔너리
        """
        game_state = self.capture_game_state()
        game_events = self.detect_events_from_chat(chat_messages)
        game_events.extend(self.get_pending_events())

        return {
            "game_name": game_info.get("name", "") if game_info else "",
            "game_state": game_state,
            "game_events": game_events,
            "min_pause_seconds": self._speech_cfg.get("min_pause_seconds", 3.0),
            "max_pause_seconds": self._speech_cfg.get("max_pause_seconds", 10.0),
        }
