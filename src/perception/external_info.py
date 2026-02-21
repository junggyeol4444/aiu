"""
external_info.py - 외부 정보 수집 모듈
외부 API 없이 동작하는 스텁 구현입니다.
날씨/뉴스 API 의존성이 제거되었습니다.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger


class ExternalInfoCollector:
    """외부 정보 수집 클래스 (API 의존성 없는 스텁 구현)."""

    def __init__(self, settings: dict[str, Any]) -> None:
        """
        Args:
            settings: settings.yaml의 external 섹션 (현재 미사용)
        """
        self.settings = settings

    async def get_weather(self) -> Optional[str]:
        """날씨 정보를 반환합니다. 외부 API 제거로 인해 None을 반환합니다."""
        return None

    async def get_trending_topics(self) -> list[str]:
        """트렌드 주제를 반환합니다. 외부 API 제거로 인해 빈 목록을 반환합니다."""
        return []
