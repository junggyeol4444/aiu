"""
title_generator.py - 방송 제목 자동 생성 모듈
AI(Ollama)를 사용하여 현재 방송 모드와 분위기에 맞는 제목을 자동으로 생성합니다.
"""

from __future__ import annotations

from typing import Any, Optional

import aiohttp
from loguru import logger


class TitleGenerator:
    """
    Ollama LLM을 이용해 방송 제목과 카테고리를 자동 생성하는 클래스.

    - 토크 모드: "심야 토크! 아무 말 대잔치 🎙️"
    - 게임 모드: "마크 생존기! 오늘은 엔더드래곤 잡는다 ⚔️"
    """

    def __init__(self, llm_settings: dict[str, Any]) -> None:
        """
        Args:
            llm_settings: settings.yaml의 llm 섹션 설정
        """
        ollama_url = llm_settings.get("ollama_url", "http://localhost:11434")
        self._chat_url = f"{ollama_url}/api/chat"
        self._model = llm_settings.get("model", "llama3")

    async def generate_title(
        self,
        mode: str = "talk",
        game_name: Optional[str] = None,
        persona_name: str = "AI",
    ) -> str:
        """
        방송 제목을 생성합니다.

        Args:
            mode: 방송 모드 ("talk" 또는 "game")
            game_name: 게임 방송 시 게임 이름 (game 모드일 때)
            persona_name: AI BJ 이름

        Returns:
            생성된 방송 제목 문자열
        """
        if mode == "game" and game_name:
            prompt = (
                f"당신은 '{persona_name}'라는 버츄얼 스트리머입니다. "
                f"'{game_name}' 게임 방송 제목을 한 줄로 만들어주세요. "
                "재미있고 클릭하고 싶은 제목으로, 이모지 1-2개 포함. "
                "제목만 답변하세요."
            )
            default = f"{game_name} 라이브 방송! 🎮"
        else:
            prompt = (
                f"당신은 '{persona_name}'라는 버츄얼 스트리머입니다. "
                "토크/잡담 라이브 방송 제목을 한 줄로 만들어주세요. "
                "친근하고 재미있는 제목으로, 이모지 1-2개 포함. "
                "제목만 답변하세요."
            )
            default = "AI와 함께하는 라이브 토크 🎙️"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._chat_url,
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"temperature": 0.9, "num_predict": 50},
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    title: str = data["message"]["content"].strip()
                    logger.info(f"방송 제목 생성: {title}")
                    return title
        except Exception as e:
            logger.warning(f"방송 제목 생성 실패, 기본값 사용: {e}")
            return default
