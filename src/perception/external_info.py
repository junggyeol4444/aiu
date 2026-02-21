"""
external_info.py - 외부 정보 수집 모듈
뉴스, 날씨, 트렌드 등 외부 정보를 수집합니다.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import aiohttp
from loguru import logger


class ExternalInfoCollector:
    """외부 API를 통해 실시간 정보를 수집하는 클래스."""

    def __init__(self, settings: dict[str, Any]) -> None:
        """
        Args:
            settings: settings.yaml의 external 섹션
        """
        self.settings = settings
        self._weather_cache: Optional[str] = None
        self._news_cache: list[str] = []
        self._cache_ttl = 300  # 5분 캐시
        self._last_weather_fetch: float = 0.0
        self._last_news_fetch: float = 0.0

    async def get_weather(self) -> Optional[str]:
        """
        현재 날씨 정보를 가져옵니다.

        Returns:
            날씨 설명 문자열 (예: "서울 맑음 15°C") 또는 None
        """
        import time

        now = time.time()
        if self._weather_cache and now - self._last_weather_fetch < self._cache_ttl:
            return self._weather_cache

        api_key_env = self.settings.get("weather_api_key_env", "WEATHER_API_KEY")
        api_key = os.environ.get(api_key_env, "")
        city = self.settings.get("weather_city", "Seoul")

        if not api_key:
            return None

        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={api_key}&units=metric&lang=kr"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        desc = data["weather"][0]["description"]
                        temp = round(data["main"]["temp"])
                        self._weather_cache = f"{city} {desc} {temp}°C"
                        self._last_weather_fetch = now
                        return self._weather_cache
        except Exception as e:
            logger.warning(f"날씨 정보 조회 실패: {e}")

        return self._weather_cache

    async def get_trending_topics(self) -> list[str]:
        """
        현재 인기 뉴스/트렌드 주제를 가져옵니다.

        Returns:
            트렌드 주제 문자열 목록
        """
        import time

        now = time.time()
        if self._news_cache and now - self._last_news_fetch < self._cache_ttl:
            return self._news_cache

        api_key_env = self.settings.get("news_api_key_env", "NEWS_API_KEY")
        api_key = os.environ.get(api_key_env, "")

        if not api_key:
            return []

        url = (
            "https://newsapi.org/v2/top-headlines"
            f"?country=kr&apiKey={api_key}&pageSize=5"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        topics = [
                            article["title"]
                            for article in data.get("articles", [])
                            if article.get("title")
                        ]
                        self._news_cache = topics[:5]
                        self._last_news_fetch = now
                        return self._news_cache
        except Exception as e:
            logger.warning(f"뉴스 정보 조회 실패: {e}")

        return self._news_cache
