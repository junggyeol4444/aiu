"""
broadcast_loop.py - 메인 방송 루프
감지→판단→발화→기억의 사이클을 반복하는 AI 자율 방송 시스템의 심장부입니다.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.brain.core import BrainCore
from src.brain.memory import ConversationMemory
from src.brain.persona import Persona
from src.perception.chat_listener import ChatListener
from src.perception.context_builder import ContextBuilder
from src.perception.event_detector import EventDetector
from src.perception.external_info import ExternalInfoCollector
from src.perception.viewer_tracker import ViewerTracker
from src.streaming.obs_controller import OBSController
from src.voice.audio_stream import AudioStream
from src.voice.realtime_tts import RealtimeTTS


class PerceptionEngine:
    """인지 엔진 - 모든 인지 모듈을 통합 관리합니다."""

    def __init__(
        self,
        platform_config: dict[str, Any],
        settings: dict[str, Any],
    ) -> None:
        self.chat_listener = ChatListener(platform_config)
        self.viewer_tracker = ViewerTracker(platform_config)
        self.event_detector = EventDetector()
        self.external_collector = ExternalInfoCollector(settings.get("external", {}))
        self.context_builder = ContextBuilder(
            chat_listener=self.chat_listener,
            viewer_tracker=self.viewer_tracker,
            event_detector=self.event_detector,
            external_collector=self.external_collector,
        )

    async def start(self) -> None:
        """모든 인지 모듈을 시작합니다."""
        await self.chat_listener.start()
        await self.viewer_tracker.start()
        self.context_builder.set_broadcast_started()
        logger.info("인지 엔진 시작 완료")

    async def stop(self) -> None:
        """모든 인지 모듈을 중단합니다."""
        await self.chat_listener.stop()
        await self.viewer_tracker.stop()
        logger.info("인지 엔진 중단 완료")

    async def get_current_context(self) -> dict[str, Any]:
        """현재 방송 상황 컨텍스트를 반환합니다."""
        return await self.context_builder.get_current_context()


class BroadcastLoop:
    """
    AI 자율 방송의 메인 루프.

    감지 → 판단 → 생성 → 발화 → 기억 사이클을 반복합니다.
    """

    def __init__(self, settings: dict[str, Any], platform_config: dict[str, Any]) -> None:
        """
        Args:
            settings: settings.yaml 전체 설정
            platform_config: platform.yaml 설정
        """
        self.settings = settings
        self.platform_config = platform_config

        broadcast_cfg = settings.get("broadcast", {})
        self.min_pause = broadcast_cfg.get("min_pause_seconds", 1.0)
        self.max_pause = broadcast_cfg.get("max_pause_seconds", 5.0)

        # ── 모듈 초기화 ───────────────────────────────────────────────

        # 페르소나
        persona = Persona()

        # 메모리
        memory_cfg = settings.get("memory", {})
        import os
        redis_url = os.environ.get(
            memory_cfg.get("redis_url_env", "REDIS_URL"), ""
        ) if memory_cfg.get("backend") == "redis" else None

        memory = ConversationMemory(
            window_size=broadcast_cfg.get("memory_window_size", 50),
            backend=memory_cfg.get("backend", "inmemory"),
            redis_url=redis_url or None,
        )

        # AI 두뇌
        self.brain = BrainCore(
            persona=persona,
            memory=memory,
            settings=settings.get("llm", {}),
        )

        # 인지 엔진
        self.perception = PerceptionEngine(platform_config, settings)

        # 음성 엔진
        voice_cfg = settings.get("voice", {})
        audio_stream = AudioStream(sample_rate=voice_cfg.get("sample_rate", 22050))
        self.voice = RealtimeTTS(voice_cfg, audio_stream)
        self._audio_stream = audio_stream

        # OBS 컨트롤러
        self.obs = OBSController(settings.get("streaming", {}))

        self._broadcasting = False
        self._last_speech: str = ""

        # 방송 모드 및 방종 상태
        self._mode: str = settings.get("broadcast", {}).get("mode", "talk")
        self._ending_mode: str = ""
        self._broadcast_start_time: datetime | None = None

        # 게임 모드 관련 모듈 (게임 설정이 있을 때만 초기화)
        game_cfg = settings.get("game", {})
        self._game_manager = None
        self._game_perception = None
        if game_cfg.get("enabled", False):
            from src.game.game_manager import GameManager
            from src.game.game_perception import GamePerception
            self._game_manager = GameManager(game_cfg)
            self._game_perception = GamePerception(game_cfg)
            logger.info("게임 모드 모듈 초기화 완료")

    @property
    def current_mode(self) -> str:
        """현재 방송 모드 ('talk' 또는 'game')를 반환합니다."""
        return self._mode

    def set_ending_mode(self, mode: str) -> None:
        """
        방종 모드를 설정합니다.

        Args:
            mode: "wind_down", "ending_announce", "final_goodbye" 중 하나
        """
        self._ending_mode = mode
        self.perception.context_builder.ending_mode = mode
        logger.info(f"방종 모드 설정: {mode}")

    def set_broadcast_mode(self, mode: str, game_name: str = "") -> None:
        """
        방송 모드를 전환합니다 ('talk' 또는 'game').

        Args:
            mode: 새 방송 모드
            game_name: 게임 방송 시 게임 이름
        """
        self._mode = mode
        self.perception.context_builder.broadcast_mode = mode
        self.perception.context_builder.game_name = game_name
        logger.info(f"방송 모드 전환: {mode}" + (f" ({game_name})" if game_name else ""))

    async def initialize(self) -> None:
        """방송 시작 전 초기화를 수행합니다."""
        logger.info("AI 방송 시스템 초기화 중...")

        # 오디오 스트림 시작
        self._audio_stream.start()

        # TTS 모델 로드
        tts_ready = self.voice.initialize()
        if not tts_ready:
            logger.warning("TTS 모델 로드 실패. 음성 없이 계속합니다.")

        # OBS 연결 (실패해도 계속 진행)
        obs_connected = await self.obs.connect()
        if not obs_connected:
            logger.warning("OBS 연결 실패. OBS 없이 계속합니다.")

        logger.info("초기화 완료")

    async def start(self) -> None:
        """방송 루프를 시작합니다."""
        if self._broadcasting:
            logger.warning("이미 방송 중입니다.")
            return

        self._broadcasting = True
        self._broadcast_start_time = datetime.now(timezone.utc)
        self._ending_mode = ""
        await self.perception.start()

        # 방송 시작 이벤트 발생
        self.perception.event_detector.signal_stream_start()

        logger.info("🎙 AI 자율 방송 시작!")
        await self._broadcast_loop()

    async def stop(self) -> None:
        """방송 루프를 중단합니다."""
        self._broadcasting = False
        await self.perception.stop()
        await self.obs.disconnect()
        self._audio_stream.stop()
        logger.info("방송 중단 완료")

    async def _broadcast_loop(self) -> None:
        """
        메인 방송 루프.

        감지 → 판단 → 생성 → 발화 → 기억의 사이클을 반복합니다.
        게임 모드일 때는 게임 상태도 컨텍스트에 포함합니다.
        """
        while self._broadcasting:
            try:
                # 1. 감지: 지금 무슨 일이 벌어지고 있는가?
                context = await self.perception.get_current_context()

                # 게임 모드일 때 게임 컨텍스트 추가
                if self._mode == "game" and self._game_perception and self._game_manager:
                    game_ctx = await self._game_perception.get_game_context(
                        self._game_manager.current_game,
                        context.get("recent_chat", []),
                    )
                    context.update(game_ctx)

                # 2. 판단: AI가 스스로 다음 행동을 결정
                action = await self.brain.decide_action(context)
                logger.debug(f"행동 결정: {action.action_type}")

                # 3. 생성: 무슨 말을 할지 생성
                speech_text = await self.brain.generate_speech(action, context)

                if speech_text:
                    logger.info(f"🗣 발화: {speech_text[:80]}")
                    self._last_speech = speech_text

                    # 4. 발화: 내 목소리로 즉시 말함
                    await self.voice.speak_realtime(speech_text)

                    # 5. 기억: 방금 한 말을 기억에 저장
                    await self.brain.memory.save(speech_text, context)

                # 최근 채팅도 메모리에 저장
                for chat in context.get("recent_chat", []):
                    await self.brain.memory.save_chat(
                        chat.get("username", "익명"),
                        chat.get("message", ""),
                    )

                # 중요 이벤트 메모리에 저장
                for event in context.get("events", []):
                    await self.brain.memory.save_important_event(
                        event.get("type", "unknown"), event
                    )

                # 자연스러운 발화 간격
                pause = self._calculate_natural_pause(context)
                await asyncio.sleep(pause)

            except asyncio.CancelledError:
                logger.info("방송 루프 취소됨")
                break
            except Exception as e:
                logger.error(f"방송 루프 오류: {e}", exc_info=True)
                await asyncio.sleep(5)  # 오류 발생 시 잠깐 대기 후 재시도

    def _calculate_natural_pause(self, context: dict[str, Any]) -> float:
        """
        자연스러운 발화 간격을 계산합니다.

        채팅 활동이 활발하면 더 짧은 간격을, 조용하면 더 긴 간격을 사용합니다.
        게임 모드일 때는 게임 설정의 발화 간격을 사용합니다.
        """
        recent_chats = context.get("recent_chat", [])
        events = context.get("events", [])

        # 게임 모드에서는 게임별 발화 간격 사용
        if self._mode == "game":
            min_p = context.get("min_pause_seconds", self.min_pause)
            max_p = context.get("max_pause_seconds", self.max_pause)
            return random.uniform(min_p, max_p)

        if events:
            # 이벤트가 있으면 빠르게 반응
            return self.min_pause

        if len(recent_chats) >= 3:
            # 채팅이 활발하면 빠른 응답
            return random.uniform(self.min_pause, self.min_pause * 2)

        # 조용할 때는 자연스러운 간격
        return random.uniform(self.min_pause, self.max_pause)
