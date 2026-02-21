"""
chat_listener.py - 실시간 채팅 수신 모듈
YouTube Live Chat API 또는 Twitch IRC와 연동하여 채팅 메시지를 실시간으로 수신합니다.
"""

from __future__ import annotations

import asyncio
import os
from collections import deque
from typing import Any, Deque, Optional

from loguru import logger


class ChatMessage:
    """채팅 메시지를 나타내는 데이터 클래스."""

    __slots__ = ("username", "message", "timestamp", "platform", "badges")

    def __init__(
        self,
        username: str,
        message: str,
        timestamp: str = "",
        platform: str = "unknown",
        badges: Optional[list[str]] = None,
    ) -> None:
        self.username = username
        self.message = message
        self.timestamp = timestamp
        self.platform = platform
        self.badges: list[str] = badges or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "message": self.message,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "badges": self.badges,
        }


class ChatListener:
    """플랫폼별 실시간 채팅을 수신하는 클래스."""

    def __init__(self, platform_config: dict[str, Any]) -> None:
        """
        Args:
            platform_config: platform.yaml 설정
        """
        self.config = platform_config
        self.platform = platform_config.get("active", "youtube")
        self._message_queue: Deque[ChatMessage] = deque(maxlen=100)
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """채팅 수신을 시작합니다."""
        self._running = True
        if self.platform == "youtube":
            self._task = asyncio.create_task(self._listen_youtube())
        elif self.platform == "twitch":
            self._task = asyncio.create_task(self._listen_twitch())
        else:
            logger.warning(f"지원하지 않는 플랫폼: {self.platform}")
        logger.info(f"채팅 리스너 시작: {self.platform}")

    async def stop(self) -> None:
        """채팅 수신을 중단합니다."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("채팅 리스너 중단")

    def get_recent_messages(self, n: int = 5) -> list[dict[str, Any]]:
        """최근 채팅 메시지 목록을 반환합니다."""
        messages = list(self._message_queue)
        return [m.to_dict() for m in messages[-n:]]

    def clear_queue(self) -> None:
        """채팅 큐를 비웁니다."""
        self._message_queue.clear()

    # ── YouTube ───────────────────────────────────────────────────────

    async def _listen_youtube(self) -> None:
        """YouTube Live Chat API를 폴링하여 채팅 메시지를 수신합니다."""
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            logger.error("google-api-python-client 패키지가 필요합니다.")
            return

        yt_config = self.config.get("youtube", {})
        api_key = os.environ.get(yt_config.get("api_key_env", "YOUTUBE_API_KEY"), "")
        live_chat_id = os.environ.get(
            yt_config.get("live_chat_id_env", "YOUTUBE_LIVE_CHAT_ID"), ""
        )
        poll_interval = yt_config.get("poll_interval_seconds", 2.0)

        if not api_key or not live_chat_id:
            logger.warning("YouTube API 키 또는 Live Chat ID가 설정되지 않았습니다.")
            return

        service = build("youtube", "v3", developerKey=api_key)
        next_page_token: Optional[str] = None

        while self._running:
            try:
                request = service.liveChatMessages().list(
                    liveChatId=live_chat_id,
                    part="snippet,authorDetails",
                    pageToken=next_page_token,
                )
                response = request.execute()
                next_page_token = response.get("nextPageToken")

                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    author = item.get("authorDetails", {})
                    msg = ChatMessage(
                        username=author.get("displayName", "익명"),
                        message=snippet.get("displayMessage", ""),
                        timestamp=snippet.get("publishedAt", ""),
                        platform="youtube",
                    )
                    self._message_queue.append(msg)

                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"YouTube 채팅 수신 오류: {e}")
                await asyncio.sleep(5)

    # ── Twitch ────────────────────────────────────────────────────────

    async def _listen_twitch(self) -> None:
        """Twitch IRC에 연결하여 채팅 메시지를 수신합니다."""
        try:
            from twitchio.ext import commands  # type: ignore
            import twitchio  # type: ignore
        except ImportError:
            logger.error("twitchio 패키지가 필요합니다: pip install twitchio")
            return

        twitch_config = self.config.get("twitch", {})
        token = os.environ.get(twitch_config.get("token_env", "TWITCH_TOKEN"), "")
        channel = os.environ.get(twitch_config.get("channel_env", "TWITCH_CHANNEL"), "")

        if not token or not channel:
            logger.warning("Twitch 토큰 또는 채널이 설정되지 않았습니다.")
            return

        queue = self._message_queue

        class TwitchBot(twitchio.Client):
            async def event_message(self, message: Any) -> None:
                if message.echo:
                    return
                chat_msg = ChatMessage(
                    username=message.author.name,
                    message=message.content,
                    platform="twitch",
                )
                queue.append(chat_msg)

        bot = TwitchBot(token=token)
        try:
            await bot.start()
        except asyncio.CancelledError:
            await bot.close()
