"""
test_brain.py - AI 두뇌 모듈 단위 테스트
"""

from __future__ import annotations

import asyncio
import sys
import os

import pytest

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Persona 테스트 ─────────────────────────────────────────────────

class TestPersona:
    """Persona 클래스 테스트."""

    def test_default_persona_loaded(self) -> None:
        """기본 페르소나가 YAML 파일 없이도 로드되는지 테스트."""
        from src.brain.persona import Persona

        persona = Persona(config_path="nonexistent.yaml")
        assert isinstance(persona.name, str)
        assert isinstance(persona.personality, str)
        assert isinstance(persona.interests, list)
        assert isinstance(persona.boundaries, list)

    def test_persona_from_yaml(self, tmp_path) -> None:
        """YAML 파일에서 페르소나가 올바르게 로드되는지 테스트."""
        import yaml
        from src.brain.persona import Persona

        persona_data = {
            "persona": {
                "name": "테스트 BJ",
                "personality": "재미있음",
                "speaking_style": "반말",
                "interests": ["게임", "음악"],
                "catchphrase": "레전드!",
                "mood_default": "신남",
                "boundaries": ["욕설 금지"],
            }
        }
        config_file = tmp_path / "persona.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(persona_data, f, allow_unicode=True)

        persona = Persona(config_path=str(config_file))
        assert persona.name == "테스트 BJ"
        assert persona.personality == "재미있음"
        assert "게임" in persona.interests
        assert persona.catchphrase == "레전드!"

    def test_system_prompt_generation(self, tmp_path) -> None:
        """시스템 프롬프트가 페르소나 정보를 포함하는지 테스트."""
        import yaml
        from src.brain.persona import Persona

        persona_data = {
            "persona": {
                "name": "AI 진행자",
                "personality": "유머러스",
                "speaking_style": "반말",
                "interests": ["게임"],
                "catchphrase": "레전드!",
                "mood_default": "밝음",
                "boundaries": [],
            }
        }
        config_file = tmp_path / "persona.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(persona_data, f, allow_unicode=True)

        persona = Persona(config_path=str(config_file))
        prompt = persona._fallback_prompt()
        assert "AI 진행자" in prompt

    def test_persona_update(self, tmp_path) -> None:
        """런타임 페르소나 업데이트가 동작하는지 테스트."""
        import yaml
        from src.brain.persona import Persona

        persona_data = {"persona": {"name": "원래 이름"}}
        config_file = tmp_path / "persona.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(persona_data, f, allow_unicode=True)

        persona = Persona(config_path=str(config_file))
        persona.update(name="새 이름")
        assert persona.name == "새 이름"


# ── ConversationMemory 테스트 ──────────────────────────────────────

class TestConversationMemory:
    """ConversationMemory 클래스 테스트."""

    def test_save_and_retrieve(self) -> None:
        """저장된 메시지가 올바르게 조회되는지 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory(window_size=10)

        async def _run() -> None:
            await memory.save("안녕하세요!")
            await memory.save("반갑습니다!")
            history = memory.get_recent_history()
            assert len(history) == 2
            assert history[0]["content"] == "안녕하세요!"
            assert history[1]["content"] == "반갑습니다!"

        asyncio.run(_run())

    def test_sliding_window(self) -> None:
        """슬라이딩 윈도우가 최대 크기를 유지하는지 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory(window_size=3)

        async def _run() -> None:
            for i in range(5):
                await memory.save(f"메시지 {i}")
            history = memory.get_recent_history()
            assert len(history) == 3
            # 마지막 3개만 유지
            assert history[-1]["content"] == "메시지 4"

        asyncio.run(_run())

    def test_save_chat_message(self) -> None:
        """채팅 메시지 저장이 올바르게 동작하는지 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory()

        async def _run() -> None:
            await memory.save_chat("시청자1", "안녕하세요!")
            history = memory.get_recent_history()
            assert len(history) == 1
            assert history[0]["username"] == "시청자1"
            assert history[0]["role"] == "user"

        asyncio.run(_run())

    def test_to_openai_messages(self) -> None:
        """OpenAI 메시지 형식 변환이 올바른지 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory()

        async def _run() -> None:
            await memory.save_chat("시청자", "질문입니다")
            await memory.save("대답입니다")
            messages = memory.to_openai_messages()
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"

        asyncio.run(_run())

    def test_clear_memory(self) -> None:
        """메모리 초기화가 올바르게 동작하는지 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory()

        async def _run() -> None:
            await memory.save("테스트")
            memory.clear()
            assert len(memory.get_recent_history()) == 0

        asyncio.run(_run())

    def test_important_events(self) -> None:
        """중요 이벤트 저장 및 조회 테스트."""
        from src.brain.memory import ConversationMemory

        memory = ConversationMemory()

        async def _run() -> None:
            await memory.save_important_event("donation", {"amount": 10000})
            events = memory.get_important_events()
            assert len(events) == 1
            assert events[0]["type"] == "donation"

        asyncio.run(_run())


# ── ActionDecider 테스트 ───────────────────────────────────────────

class TestActionDecider:
    """ActionDecider 클래스 테스트."""

    def test_chat_reply_when_chat_exists(self) -> None:
        """채팅이 있을 때 CHAT_REPLY 행동을 선택하는지 테스트."""
        from src.brain.action_decider import ActionDecider, ActionType

        decider = ActionDecider()
        context = {
            "recent_chat": [{"username": "user1", "message": "안녕하세요"}],
            "events": [],
            "viewer_count": 10,
        }
        action = decider.decide(context)
        assert action.action_type == ActionType.CHAT_REPLY
        assert action.target_user == "user1"

    def test_donation_react_for_donation_event(self) -> None:
        """후원 이벤트가 있을 때 DONATION_REACT 행동을 선택하는지 테스트."""
        from src.brain.action_decider import ActionDecider, ActionType

        decider = ActionDecider()
        context = {
            "recent_chat": [],
            "events": [{"type": "donation", "username": "donor", "amount": 5000}],
            "viewer_count": 10,
        }
        action = decider.decide(context)
        assert action.action_type == ActionType.DONATION_REACT
        assert action.priority == 10

    def test_subscription_react_for_subscription_event(self) -> None:
        """구독 이벤트에 대해 SUBSCRIBE_REACT 행동을 선택하는지 테스트."""
        from src.brain.action_decider import ActionDecider, ActionType

        decider = ActionDecider()
        context = {
            "recent_chat": [],
            "events": [{"type": "subscription", "username": "newbie"}],
            "viewer_count": 5,
        }
        action = decider.decide(context)
        assert action.action_type == ActionType.SUBSCRIBE_REACT

    def test_default_action_without_stimuli(self) -> None:
        """자극이 없을 때 기본 행동이 반환되는지 테스트."""
        from src.brain.action_decider import ActionDecider, ActionType

        decider = ActionDecider()
        context = {"recent_chat": [], "events": [], "viewer_count": 0}

        # 여러 번 호출해도 유효한 ActionType이 반환되어야 함
        for _ in range(10):
            action = decider.decide(context)
            assert action.action_type in ActionType
