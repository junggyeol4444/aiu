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

            with gr.Row():
                # ── 방송 제어 패널 ───────────────────────────────────
                with gr.Column(scale=1):
                    gr.Markdown("## 📡 방송 제어")
                    status_label = gr.Label(value="대기 중", label="방송 상태")
                    start_btn = gr.Button("🔴 방송 시작", variant="primary")
                    stop_btn = gr.Button("⏹ 방송 중지", variant="stop")

                    gr.Markdown("---")
                    gr.Markdown("## 👁 실시간 현황")
                    viewer_count = gr.Number(label="시청자 수", value=0, interactive=False)
                    last_speech = gr.Textbox(label="마지막 발화", interactive=False, lines=2)

                # ── 페르소나 설정 패널 ───────────────────────────────
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

            # ── 대화 히스토리 ────────────────────────────────────────
            gr.Markdown("## 💬 대화 히스토리")
            history_display = gr.Dataframe(
                headers=["시간", "역할", "내용"],
                label="최근 대화",
                interactive=False,
            )
            refresh_btn = gr.Button("🔄 새로고침")

            # ── 이벤트 핸들러 ────────────────────────────────────────

            start_btn.click(
                fn=self._start_broadcast,
                outputs=[status_label],
            )
            stop_btn.click(
                fn=self._stop_broadcast,
                outputs=[status_label],
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
