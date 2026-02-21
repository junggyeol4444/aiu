"""
platform_adapter.py - 플랫폼별 어댑터 모듈
YouTube, Twitch, AfreecaTV 등 방송 플랫폼별 API 어댑터를 제공합니다.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from loguru import logger


class BasePlatformAdapter(ABC):
    """방송 플랫폼 어댑터의 기본 추상 클래스."""

    @abstractmethod
    async def get_viewer_count(self) -> int:
        """현재 시청자 수를 반환합니다."""
        ...

    @abstractmethod
    async def send_message(self, message: str) -> bool:
        """채팅에 메시지를 전송합니다."""
        ...

    @abstractmethod
    async def get_stream_info(self) -> dict[str, Any]:
        """방송 정보를 반환합니다."""
        ...


class YouTubeAdapter(BasePlatformAdapter):
    """YouTube Live API 어댑터."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.api_key = os.environ.get(config.get("api_key_env", "YOUTUBE_API_KEY"), "")
        self.channel_id = os.environ.get(
            config.get("channel_id_env", "YOUTUBE_CHANNEL_ID"), ""
        )

    async def get_viewer_count(self) -> int:
        """YouTube 동시 시청자 수를 조회합니다."""
        try:
            from googleapiclient.discovery import build  # type: ignore

            service = build("youtube", "v3", developerKey=self.api_key)
            request = service.videos().list(
                part="liveStreamingDetails",
                id=self.channel_id,
            )
            response = request.execute()
            items = response.get("items", [])
            if items:
                details = items[0].get("liveStreamingDetails", {})
                return int(details.get("concurrentViewers", 0))
        except Exception as e:
            logger.warning(f"YouTube 시청자 수 조회 실패: {e}")
        return 0

    async def send_message(self, message: str) -> bool:
        """YouTube 라이브 채팅에 메시지를 전송합니다."""
        logger.info(f"[YouTube] 채팅 전송: {message}")
        # 실제 구현은 OAuth 인증이 필요합니다.
        return False

    async def get_stream_info(self) -> dict[str, Any]:
        """YouTube 방송 정보를 조회합니다."""
        return {"platform": "youtube", "channel_id": self.channel_id}


class TwitchAdapter(BasePlatformAdapter):
    """Twitch API 어댑터."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.token = os.environ.get(config.get("token_env", "TWITCH_TOKEN"), "")
        self.channel = os.environ.get(config.get("channel_env", "TWITCH_CHANNEL"), "")
        self.client_id = os.environ.get(
            config.get("client_id_env", "TWITCH_CLIENT_ID"), ""
        )

    async def get_viewer_count(self) -> int:
        """Twitch 동시 시청자 수를 조회합니다."""
        try:
            import aiohttp

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Client-Id": self.client_id,
            }
            url = f"https://api.twitch.tv/helix/streams?user_login={self.channel}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    streams = data.get("data", [])
                    if streams:
                        return streams[0].get("viewer_count", 0)
        except Exception as e:
            logger.warning(f"Twitch 시청자 수 조회 실패: {e}")
        return 0

    async def send_message(self, message: str) -> bool:
        """Twitch 채팅에 메시지를 전송합니다."""
        logger.info(f"[Twitch] 채팅 전송: {message}")
        return False

    async def get_stream_info(self) -> dict[str, Any]:
        """Twitch 방송 정보를 조회합니다."""
        return {"platform": "twitch", "channel": self.channel}


class PlatformAdapterFactory:
    """플랫폼에 맞는 어댑터 인스턴스를 생성하는 팩토리 클래스."""

    @staticmethod
    def create(platform: str, config: dict[str, Any]) -> Optional[BasePlatformAdapter]:
        """
        플랫폼 이름에 맞는 어댑터를 생성합니다.

        Args:
            platform: 플랫폼 이름 ("youtube", "twitch", "afreecatv")
            config: platform.yaml의 해당 플랫폼 설정

        Returns:
            플랫폼 어댑터 인스턴스
        """
        adapters: dict[str, type[BasePlatformAdapter]] = {
            "youtube": YouTubeAdapter,
            "twitch": TwitchAdapter,
        }

        adapter_class = adapters.get(platform)
        if not adapter_class:
            logger.warning(f"지원하지 않는 플랫폼: {platform}")
            return None

        return adapter_class(config)
