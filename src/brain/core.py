"""
core.py - 핵심 판단 엔진
Ollama 로컬 LLM과 연동하여 현재 상황에서 무슨 말을 할지 실시간으로 결정합니다.
스트리밍 응답을 지원합니다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import aiohttp
from loguru import logger

from src.brain.action_decider import Action, ActionDecider, ActionType
from src.brain.memory import ConversationMemory
from src.brain.persona import Persona


class BrainCore:
    """Ollama 로컬 LLM과 연동하여 AI 방송인의 두뇌 역할을 수행하는 핵심 클래스."""

    def __init__(
        self,
        persona: Persona,
        memory: ConversationMemory,
        settings: dict[str, Any],
    ) -> None:
        """
        Args:
            persona: 페르소나 관리 객체
            memory: 대화 기억 관리 객체
            settings: settings.yaml의 llm 섹션
        """
        self.persona = persona
        self.memory = memory
        self.settings = settings
        self.action_decider = ActionDecider()

        # Ollama 설정
        ollama_url = self.settings.get("ollama_url", "http://localhost:11434")
        self._ollama_chat_url = f"{ollama_url}/api/chat"
        self._model = self.settings.get("model", "llama3")
        logger.info(f"Ollama LLM 초기화 완료: {self._ollama_chat_url} (모델: {self._model})")

        # 반응 가이드 프롬프트 로드
        self._reaction_guide = self._load_reaction_guide()

    @staticmethod
    def _load_reaction_guide() -> str:
        """상황별 반응 가이드 파일을 로드합니다."""
        path = Path("src/brain/prompts/reaction.txt")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    # ── 외부 인터페이스 ───────────────────────────────────────────────

    async def decide_action(self, context: dict[str, Any]) -> Action:
        """현재 컨텍스트를 분석하여 다음 행동을 결정합니다."""
        return self.action_decider.decide(context)

    async def generate_speech(
        self,
        action: Action,
        context: dict[str, Any],
    ) -> str:
        """
        결정된 행동과 컨텍스트를 바탕으로 발화할 텍스트를 생성합니다.

        Args:
            action: 결정된 행동
            context: 현재 상황 컨텍스트

        Returns:
            생성된 발화 텍스트
        """
        if action.action_type == ActionType.SILENCE:
            return ""  # 침묵 - 아무 말도 하지 않음

        messages = self._build_messages(action, context)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._ollama_chat_url,
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.settings.get("temperature", 0.8),
                            "num_predict": self.settings.get("max_tokens", 300),
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    result = await response.json()
                    text: str = result["message"]["content"]
                    logger.debug(f"생성된 발화: {text[:80]}...")
                    return text.strip()
        except Exception as e:
            logger.error(f"Ollama LLM 호출 오류: {e}")
            return self._fallback_speech(action)

    async def generate_speech_stream(
        self,
        action: Action,
        context: dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        스트리밍 방식으로 발화 텍스트를 생성합니다.
        문장이 완성되기 전에 앞부분부터 처리할 수 있습니다.

        Yields:
            텍스트 청크 (토큰 단위)
        """
        if action.action_type == ActionType.SILENCE:
            return

        messages = self._build_messages(action, context)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._ollama_chat_url,
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": self.settings.get("temperature", 0.8),
                            "num_predict": self.settings.get("max_tokens", 300),
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    async for line in response.content:
                        line = line.strip()
                        if line:
                            data = json.loads(line.decode("utf-8"))
                            if not data.get("done", False):
                                yield data["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama LLM 스트리밍 오류: {e}")
            yield self._fallback_speech(action)

    # ── 내부 헬퍼 ────────────────────────────────────────────────────

    def _build_messages(
        self,
        action: Action,
        context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Ollama API에 전달할 메시지 목록을 구성합니다."""
        system_prompt = self.persona.build_system_prompt()
        if self._reaction_guide:
            system_prompt += f"\n\n{self._reaction_guide}"

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # 최근 대화 히스토리 추가
        messages.extend(self.memory.to_messages())

        # 현재 상황 컨텍스트를 사용자 메시지로 추가
        user_content = self._build_user_content(action, context)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, action: Action, context: dict[str, Any]) -> str:
        """행동과 컨텍스트를 기반으로 사용자 프롬프트를 구성합니다."""
        parts: list[str] = []

        # 현재 상황 정보
        viewer_count = context.get("viewer_count", 0)
        parts.append(f"[현재 상황] 시청자 수: {viewer_count}명")

        # 행동 유형별 지시
        action_instruction = self._get_action_instruction(action)
        parts.append(f"\n[지시] {action_instruction}")

        return "\n".join(parts)

    @staticmethod
    def _get_action_instruction(action: Action) -> str:
        """행동 유형에 따른 구체적 지시문을 반환합니다."""
        instructions: dict[ActionType, str] = {
            ActionType.FREE_TALK: "지금 떠오르는 생각이나 일상적인 이야기를 자연스럽게 해주세요.",
            ActionType.CHAT_REPLY: (
                f"시청자 '{action.target_user}'의 채팅 '{action.trigger_message}'에 자연스럽게 답변해주세요."
            ),
            ActionType.TOPIC_CHANGE: "새로운 주제로 자연스럽게 전환하며 이야기를 시작해주세요.",
            ActionType.REACTION: "현재 상황에 맞는 감정적인 리액션을 해주세요.",
            ActionType.ASK_VIEWERS: "시청자들에게 흥미로운 질문을 던져 참여를 유도해주세요.",
            ActionType.ANNOUNCEMENT: "방송 관련 공지나 알림을 자연스럽게 전달해주세요.",
            ActionType.GREETING: "시청자들에게 따뜻하게 인사해주세요.",
            ActionType.DONATION_REACT: "후원에 진심으로 감사를 표현해주세요.",
            ActionType.SUBSCRIBE_REACT: f"'{action.target_user}'님의 구독/팔로우를 환영해주세요.",
        }
        return instructions.get(action.action_type, "자연스럽게 이야기해주세요.")

    @staticmethod
    def _fallback_speech(action: Action) -> str:
        """LLM 호출 실패 시 사용하는 기본 발화."""
        fallbacks: dict[ActionType, str] = {
            ActionType.FREE_TALK: "오늘도 방송에 와줘서 고마워!",
            ActionType.GREETING: "안녕하세요! 방송 시작합니다~",
            ActionType.DONATION_REACT: "후원 감사합니다! 정말 감동이에요~",
            ActionType.SUBSCRIBE_REACT: "구독해주셔서 진심으로 감사합니다!",
            ActionType.ASK_VIEWERS: "여러분은 오늘 어떻게 지내고 있나요?",
        }
        return fallbacks.get(action.action_type, "잠깐, 뭔가 생각 중이에요!")
