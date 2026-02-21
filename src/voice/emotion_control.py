"""
emotion_control.py - 감정/톤 제어 모듈
텍스트의 감정을 분석하고 TTS 파라미터(속도, 피치 등)를 조절합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Emotion(str, Enum):
    """지원하는 감정 유형."""

    NEUTRAL = "neutral"       # 기본
    HAPPY = "happy"           # 기쁨
    EXCITED = "excited"       # 흥분/신남
    SURPRISED = "surprised"   # 놀라움
    SAD = "sad"               # 슬픔
    CALM = "calm"             # 차분함
    LAUGHING = "laughing"     # 웃음


@dataclass
class ToneParameters:
    """TTS 엔진에 전달할 톤 파라미터."""

    speed: float = 1.0        # 말하기 속도 (0.5 ~ 2.0)
    temperature: float = 0.65 # XTTS 감정 온도 (0.0 ~ 1.0)
    emotion_tag: str = ""     # 텍스트 앞에 붙일 감정 태그


class EmotionController:
    """텍스트에서 감정을 감지하고 TTS 파라미터를 결정하는 클래스."""

    # 감정별 키워드 패턴
    _EMOTION_PATTERNS: dict[Emotion, list[str]] = {
        Emotion.EXCITED: ["대박", "레전드", "미쳤다", "와", "ㅋㅋ", "!!!"],
        Emotion.HAPPY: ["고마워", "감사", "좋아", "최고", "행복", "즐거"],
        Emotion.SURPRISED: ["헐", "진짜?", "어?", "엥", "설마", "와우"],
        Emotion.SAD: ["슬프", "아쉽", "속상", "힘들", "울"],
        Emotion.LAUGHING: ["ㅋㅋㅋ", "하하", "히히", "웃겨", "재밌"],
    }

    # 감정별 TTS 파라미터
    _TONE_MAP: dict[Emotion, ToneParameters] = {
        Emotion.NEUTRAL: ToneParameters(speed=1.0, temperature=0.65),
        Emotion.HAPPY: ToneParameters(speed=1.1, temperature=0.75),
        Emotion.EXCITED: ToneParameters(speed=1.25, temperature=0.85),
        Emotion.SURPRISED: ToneParameters(speed=1.15, temperature=0.80),
        Emotion.SAD: ToneParameters(speed=0.85, temperature=0.55),
        Emotion.CALM: ToneParameters(speed=0.90, temperature=0.50),
        Emotion.LAUGHING: ToneParameters(speed=1.10, temperature=0.80),
    }

    def detect_emotion(self, text: str) -> Emotion:
        """
        텍스트에서 감정을 감지합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            감지된 감정 유형
        """
        text_lower = text.lower()
        scores: dict[Emotion, int] = {e: 0 for e in Emotion}

        for emotion, keywords in self._EMOTION_PATTERNS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    scores[emotion] += 1

        # 가장 높은 점수의 감정 반환
        best_emotion = max(scores, key=lambda e: scores[e])
        if scores[best_emotion] == 0:
            return Emotion.NEUTRAL

        return best_emotion

    def get_tone_parameters(self, text: str) -> ToneParameters:
        """
        텍스트에 맞는 TTS 톤 파라미터를 반환합니다.

        Args:
            text: 발화할 텍스트

        Returns:
            TTS 파라미터
        """
        emotion = self.detect_emotion(text)
        return self._TONE_MAP.get(emotion, ToneParameters())

    def apply_emotion(self, text: str, emotion: Emotion) -> str:
        """
        텍스트에 감정 태그를 추가합니다 (일부 TTS 엔진 지원).

        Args:
            text: 원본 텍스트
            emotion: 적용할 감정

        Returns:
            감정 태그가 적용된 텍스트
        """
        params = self._TONE_MAP.get(emotion, ToneParameters())
        if params.emotion_tag:
            return f"{params.emotion_tag} {text}"
        return text
