"""
persona.py - 페르소나 관리 모듈
YAML 설정 파일에서 AI 성격/말투/관심사 등을 로드하여 시스템 프롬프트에 주입합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class Persona:
    """AI 방송인의 페르소나(성격, 말투 등)를 관리하는 클래스."""

    def __init__(self, config_path: str = "config/persona.yaml") -> None:
        self.config_path = Path(config_path)
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """YAML 파일에서 페르소나 설정을 로드합니다."""
        if not self.config_path.exists():
            logger.warning(f"페르소나 설정 파일을 찾을 수 없습니다: {self.config_path}")
            self._data = {}
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self._data = raw.get("persona", {})
        logger.info(f"페르소나 로드 완료: {self.name}")

    # ── 속성 접근자 ──────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._data.get("name", "AI BJ")

    @property
    def personality(self) -> str:
        return self._data.get("personality", "친근하고 유머러스함")

    @property
    def speaking_style(self) -> str:
        return self._data.get("speaking_style", "반말 위주, 자연스러운 구어체")

    @property
    def interests(self) -> list[str]:
        return self._data.get("interests", [])

    @property
    def catchphrase(self) -> str:
        return self._data.get("catchphrase", "")

    @property
    def mood(self) -> str:
        return self._data.get("mood_default", "밝고 에너지 넘침")

    @property
    def boundaries(self) -> list[str]:
        return self._data.get("boundaries", [])

    # ── 시스템 프롬프트 생성 ──────────────────────────────────────────

    def build_system_prompt(self, base_prompt_path: str = "src/brain/prompts/base_prompt.txt") -> str:
        """기본 프롬프트 템플릿에 페르소나 정보를 주입하여 시스템 프롬프트를 생성합니다."""
        path = Path(base_prompt_path)
        if not path.exists():
            logger.warning(f"기본 프롬프트 파일을 찾을 수 없습니다: {path}")
            return self._fallback_prompt()

        with open(path, "r", encoding="utf-8") as f:
            template = f.read()

        interests_str = ", ".join(self.interests) if self.interests else "다양한 주제"
        boundaries_str = "\n".join(f"- {b}" for b in self.boundaries) if self.boundaries else "- 없음"

        prompt = template.format(
            name=self.name,
            personality=self.personality,
            speaking_style=self.speaking_style,
            interests=interests_str,
            catchphrase=self.catchphrase,
            mood=self.mood,
            boundaries=boundaries_str,
        )
        return prompt

    def _fallback_prompt(self) -> str:
        """기본 프롬프트 파일이 없을 때 사용하는 폴백 프롬프트."""
        return (
            f"당신은 {self.name}이라는 AI 라이브 방송 진행자입니다. "
            f"성격: {self.personality}. "
            f"말투: {self.speaking_style}. "
            "한국어로 자연스럽게 시청자와 소통하세요."
        )

    def update(self, **kwargs: Any) -> None:
        """런타임에서 페르소나 속성을 동적으로 업데이트합니다."""
        self._data.update(kwargs)
        logger.info(f"페르소나 업데이트: {kwargs}")
