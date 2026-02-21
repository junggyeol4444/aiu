"""
dashboard.py - 모니터링 및 설정 대시보드 모듈
Gradio 기반 실시간 방송 모니터링 및 설정 UI를 제공합니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from loguru import logger

if TYPE_CHECKING:
    from src.broadcast_loop import BroadcastLoop


class Dashboard:
    """
    Gradio 기반 방송 관리 대시보드.
    방송 시작/중지, 실시간 상태 모니터링, 페르소나 설정 기능을 제공합니다.
    """

    def __init__(
        self,
        broadcast_loop: "BroadcastLoop",
        ui_settings: dict[str, Any],
    ) -> None:
        """
        Args:
            broadcast_loop: 방송 루프 인스턴스
            ui_settings: settings.yaml의 ui 섹션
        """
        self.broadcast_loop = broadcast_loop
        self.host = ui_settings.get("host", "0.0.0.0")
        self.port = ui_settings.get("port", 7860)
        self.share = ui_settings.get("share", False)
        self._demo: Any = None

    def build(self) -> Any:
        """Gradio 대시보드 UI를 구성하고 반환합니다."""
        try:
            import gradio as gr  # type: ignore
        except ImportError:
            logger.error("gradio 패키지가 필요합니다: pip install gradio")
            return None

        with gr.Blocks(title="AI 자율 방송 시스템", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🤖 AI 자율 방송 시스템 대시보드")

            with gr.Tabs():
                # ── 탭 1: 방송 제어 ──────────────────────────────────
                with gr.TabItem("📡 방송 제어"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("## 📡 방송 제어")
                            status_label = gr.Label(value="대기 중", label="방송 상태")
                            mode_label = gr.Label(
                                value=self.broadcast_loop.current_mode,
                                label="현재 모드",
                            )
                            start_btn = gr.Button("🔴 방송 시작", variant="primary")
                            stop_btn = gr.Button("⏹ 방송 중지", variant="stop")

                            gr.Markdown("---")
                            # 모드 전환 버튼
                            with gr.Row():
                                talk_mode_btn = gr.Button("💬 토크 모드")
                                game_mode_btn = gr.Button("🎮 게임 모드")
                            mode_status = gr.Label(label="모드 전환")

                            gr.Markdown("---")
                            gr.Markdown("## 👁 실시간 현황")
                            viewer_count = gr.Number(
                                label="시청자 수", value=0, interactive=False
                            )
                            last_speech = gr.Textbox(
                                label="마지막 발화", interactive=False, lines=2
                            )

                        # ── 페르소나 설정 패널 ───────────────────────
                        with gr.Column(scale=2):
                            gr.Markdown("## 🎭 페르소나 설정")
                            persona_name = gr.Textbox(
                                label="이름",
                                value=self.broadcast_loop.brain.persona.name,
                            )
                            persona_personality = gr.Textbox(
                                label="성격",
                                value=self.broadcast_loop.brain.persona.personality,
                                lines=2,
                            )
                            persona_mood = gr.Textbox(
                                label="현재 기분",
                                value=self.broadcast_loop.brain.persona.mood,
                            )
                            persona_update_btn = gr.Button("💾 페르소나 저장")
                            persona_status = gr.Label(label="저장 상태")

                    # ── 대화 히스토리 ─────────────────────────────────
                    gr.Markdown("## 💬 대화 히스토리")
                    history_display = gr.Dataframe(
                        headers=["시간", "역할", "내용"],
                        label="최근 대화",
                        interactive=False,
                    )
                    refresh_btn = gr.Button("🔄 새로고침")

                    # 이벤트 핸들러
                    start_btn.click(fn=self._start_broadcast, outputs=[status_label])
                    stop_btn.click(fn=self._stop_broadcast, outputs=[status_label])
                    talk_mode_btn.click(
                        fn=lambda: self._switch_mode("talk"),
                        outputs=[mode_label, mode_status],
                    )
                    game_mode_btn.click(
                        fn=lambda: self._switch_mode("game"),
                        outputs=[mode_label, mode_status],
                    )
                    persona_update_btn.click(
                        fn=self._update_persona,
                        inputs=[persona_name, persona_personality, persona_mood],
                        outputs=[persona_status],
                    )
                    refresh_btn.click(
                        fn=self._get_history,
                        outputs=[history_display, viewer_count, last_speech],
                    )

                # ── 탭 2: 스케줄 ─────────────────────────────────────
                with gr.TabItem("⏰ 스케줄"):
                    gr.Markdown("## 📅 방송 스케줄")
                    schedule_display = gr.Dataframe(
                        headers=["요일", "시작 시간"],
                        label="주간 방송 스케줄",
                        interactive=False,
                        value=self._get_schedule_rows(),
                    )
                    next_broadcast_label = gr.Label(
                        label="다음 방송 시간",
                        value=self._get_next_broadcast_str(),
                    )
                    schedule_refresh_btn = gr.Button("🔄 스케줄 새로고침")
                    schedule_refresh_btn.click(
                        fn=self._refresh_schedule,
                        outputs=[schedule_display, next_broadcast_label],
                    )

                # ── 탭 3: 게임 설정 ──────────────────────────────────
                with gr.TabItem("🎮 게임 설정"):
                    gr.Markdown("## 🎮 게임 방송 설정")
                    game_status = gr.Label(label="게임 상태", value=self._get_game_status())
                    game_list_display = gr.Dataframe(
                        headers=["게임 이름", "프로세스"],
                        label="게임 목록",
                        interactive=False,
                        value=self._get_game_list_rows(),
                    )
                    game_name_input = gr.Textbox(label="게임 이름 (시작/종료)", placeholder="Minecraft")
                    with gr.Row():
                        start_game_btn = gr.Button("▶ 게임 시작")
                        stop_game_btn = gr.Button("⏹ 게임 종료")
                    game_action_status = gr.Label(label="게임 액션 결과")

                    start_game_btn.click(
                        fn=self._start_game,
                        inputs=[game_name_input],
                        outputs=[game_status, game_action_status],
                    )
                    stop_game_btn.click(
                        fn=self._stop_game,
                        outputs=[game_status, game_action_status],
                    )

        self._demo = demo
        return demo

    def launch(self) -> None:
        """대시보드를 실행합니다."""
        if self._demo is None:
            self.build()
        if self._demo:
            logger.info(f"대시보드 시작: http://{self.host}:{self.port}")
            self._demo.launch(
                server_name=self.host,
                server_port=self.port,
                share=self.share,
            )

    # ── 이벤트 핸들러 구현 ───────────────────────────────────────────

    def _start_broadcast(self) -> str:
        """방송 시작 버튼 핸들러."""
        import asyncio

        try:
            asyncio.create_task(self.broadcast_loop.start())
            logger.info("대시보드에서 방송 시작 요청")
            return "🔴 방송 중"
        except Exception as e:
            logger.error(f"방송 시작 오류: {e}")
            return f"오류: {e}"

    def _stop_broadcast(self) -> str:
        """방송 중지 버튼 핸들러."""
        import asyncio

        try:
            asyncio.create_task(self.broadcast_loop.stop())
            logger.info("대시보드에서 방송 중지 요청")
            return "⏹ 대기 중"
        except Exception as e:
            logger.error(f"방송 중지 오류: {e}")
            return f"오류: {e}"

    def _update_persona(
        self, name: str, personality: str, mood: str
    ) -> str:
        """페르소나 설정 업데이트 핸들러."""
        try:
            self.broadcast_loop.brain.persona.update(
                name=name,
                personality=personality,
                mood_default=mood,
            )
            return "✅ 페르소나 저장 완료"
        except Exception as e:
            logger.error(f"페르소나 업데이트 오류: {e}")
            return f"❌ 오류: {e}"

    def _get_history(self) -> tuple[list[list[str]], int, str]:
        """대화 히스토리와 현재 상태를 반환합니다."""
        history = self.broadcast_loop.brain.memory.get_recent_history(20)
        rows = [
            [
                entry.get("timestamp", "")[:19],
                "AI" if entry.get("role") == "assistant" else entry.get("username", "시청자"),
                entry.get("content", ""),
            ]
            for entry in history
        ]
        viewer_count = self.broadcast_loop.perception.viewer_tracker.current_count
        last_speech = ""
        if history:
            for entry in reversed(history):
                if entry.get("role") == "assistant":
                    last_speech = entry.get("content", "")
                    break

        return rows, viewer_count, last_speech

    def _switch_mode(self, mode: str) -> tuple[str, str]:
        """방송 모드를 전환합니다."""
        try:
            self.broadcast_loop.set_broadcast_mode(mode)
            mode_label = "💬 토크 방송" if mode == "talk" else "🎮 게임 방송"
            return mode_label, f"✅ {mode_label} 모드로 전환됨"
        except Exception as e:
            logger.error(f"모드 전환 오류: {e}")
            return mode, f"❌ 오류: {e}"

    def _get_schedule_rows(self) -> list[list[str]]:
        """스케줄 정보를 Dataframe 형식으로 반환합니다."""
        try:
            from src.scheduler import BroadcastScheduler
            scheduler = BroadcastScheduler(self.broadcast_loop)
            return [
                [entry.get("day", ""), entry.get("time", "")]
                for entry in scheduler.get_schedule_summary()
            ]
        except Exception as e:
            logger.warning(f"스케줄 조회 오류: {e}")
            return []

    def _get_next_broadcast_str(self) -> str:
        """다음 방송 시간 문자열을 반환합니다."""
        try:
            from src.scheduler import BroadcastScheduler
            scheduler = BroadcastScheduler(self.broadcast_loop)
            next_time = scheduler.get_next_broadcast_time()
            if next_time:
                return next_time.strftime("%Y-%m-%d %H:%M")
            return "스케줄 없음"
        except Exception as e:
            logger.warning(f"다음 방송 시간 조회 오류: {e}")
            return "조회 실패"

    def _refresh_schedule(self) -> tuple[list[list[str]], str]:
        """스케줄 정보를 새로고침합니다."""
        return self._get_schedule_rows(), self._get_next_broadcast_str()

    def _get_game_status(self) -> str:
        """현재 게임 상태를 반환합니다."""
        gm = self.broadcast_loop._game_manager
        if gm is None:
            return "게임 모드 비활성화"
        game = gm.current_game
        if game:
            return f"🎮 실행 중: {game.get('name', '')}"
        return "대기 중"

    def _get_game_list_rows(self) -> list[list[str]]:
        """게임 목록을 Dataframe 형식으로 반환합니다."""
        gm = self.broadcast_loop._game_manager
        if gm is None:
            return []
        return [
            [g.get("name", ""), g.get("process_name", "")]
            for g in gm.games
        ]

    def _start_game(self, game_name: str) -> tuple[str, str]:
        """게임을 시작합니다."""
        gm = self.broadcast_loop._game_manager
        if gm is None:
            return "게임 모드 비활성화", "❌ 게임 모드가 활성화되어 있지 않습니다."
        if not game_name.strip():
            return self._get_game_status(), "❌ 게임 이름을 입력하세요."
        success = gm.start_game(game_name.strip())
        if success:
            self.broadcast_loop.set_broadcast_mode("game", game_name.strip())
            return self._get_game_status(), f"✅ {game_name} 시작됨"
        return self._get_game_status(), f"❌ {game_name} 시작 실패"

    def _stop_game(self) -> tuple[str, str]:
        """게임을 종료합니다."""
        gm = self.broadcast_loop._game_manager
        if gm is None:
            return "게임 모드 비활성화", "❌ 게임 모드가 활성화되어 있지 않습니다."
        gm.stop_game()
        self.broadcast_loop.set_broadcast_mode("talk")
        return self._get_game_status(), "✅ 게임 종료됨. 토크 모드로 전환"
