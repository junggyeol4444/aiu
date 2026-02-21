"""
voice_setup.py - 음성 학습 UI 모듈
음성 샘플 업로드, 학습 실행, 학습된 음성 미리듣기 Gradio UI를 제공합니다.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class VoiceSetupUI:
    """
    음성 클론 학습을 위한 Gradio 기반 UI 클래스.
    사용자가 음성 샘플을 업로드하고 학습을 시작할 수 있습니다.
    """

    def __init__(self, voice_settings: dict[str, Any]) -> None:
        """
        Args:
            voice_settings: settings.yaml의 voice 섹션
        """
        self.settings = voice_settings
        self.sample_dir = Path("data/voice_samples/")
        self.model_dir = Path(voice_settings.get("model_path", "data/voice_models/"))
        self._demo: Any = None

    def build(self) -> Any:
        """음성 설정 UI를 구성하고 반환합니다."""
        try:
            import gradio as gr  # type: ignore
        except ImportError:
            logger.error("gradio 패키지가 필요합니다: pip install gradio")
            return None

        with gr.Blocks(title="음성 학습 설정") as demo:
            gr.Markdown("# 🎤 음성 학습 설정")
            gr.Markdown(
                "AI가 당신의 목소리로 말할 수 있도록 음성 샘플을 업로드하고 학습을 시작하세요."
            )

            with gr.Row():
                with gr.Column():
                    gr.Markdown("## 1️⃣ 음성 샘플 업로드")
                    gr.Markdown(
                        "- WAV 또는 MP3 형식 권장\n"
                        "- 최소 3개, 최대 10개 파일\n"
                        "- 각 파일은 5~30초 분량\n"
                        "- 조용한 환경에서 녹음된 깨끗한 음성"
                    )
                    audio_input = gr.File(
                        label="음성 샘플 파일",
                        file_count="multiple",
                        file_types=[".wav", ".mp3", ".flac"],
                    )
                    upload_btn = gr.Button("📤 샘플 업로드")
                    upload_status = gr.Label(label="업로드 상태")

                with gr.Column():
                    gr.Markdown("## 2️⃣ 학습 실행")
                    train_btn = gr.Button("🚀 학습 시작", variant="primary")
                    train_progress = gr.Label(label="학습 진행 상태")

                    gr.Markdown("## 3️⃣ 음성 미리듣기")
                    preview_text = gr.Textbox(
                        label="미리듣기 텍스트",
                        value="안녕하세요! AI 방송 시스템 테스트입니다.",
                        lines=2,
                    )
                    preview_btn = gr.Button("🔊 미리듣기")
                    audio_preview = gr.Audio(label="생성된 음성", interactive=False)

            # ── 이벤트 핸들러 연결 ────────────────────────────────────

            upload_btn.click(
                fn=self._upload_samples,
                inputs=[audio_input],
                outputs=[upload_status],
            )
            train_btn.click(
                fn=self._start_training,
                outputs=[train_progress],
            )
            preview_btn.click(
                fn=self._generate_preview,
                inputs=[preview_text],
                outputs=[audio_preview],
            )

        self._demo = demo
        return demo

    def launch(self, host: str = "0.0.0.0", port: int = 7861) -> None:
        """음성 설정 UI를 독립적으로 실행합니다."""
        if self._demo is None:
            self.build()
        if self._demo:
            self._demo.launch(server_name=host, server_port=port)

    # ── 이벤트 핸들러 구현 ───────────────────────────────────────────

    def _upload_samples(self, files: Optional[list[Any]]) -> str:
        """음성 샘플 파일을 업로드합니다."""
        if not files:
            return "❌ 업로드할 파일을 선택해 주세요."

        self.sample_dir.mkdir(parents=True, exist_ok=True)
        count = 0

        for file_obj in files:
            try:
                src = Path(file_obj.name)
                dst = self.sample_dir / src.name
                shutil.copy2(str(src), str(dst))
                count += 1
            except Exception as e:
                logger.warning(f"파일 업로드 실패: {e}")

        return f"✅ {count}개 파일 업로드 완료: {self.sample_dir}"

    def _start_training(self) -> str:
        """음성 클론 학습을 시작합니다."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        trainer = VoiceCloneTrainer(self.settings)

        progress_messages: list[str] = []

        def progress_callback(progress: float, message: str) -> None:
            progress_messages.append(f"[{progress:.0%}] {message}")

        trainer.set_progress_callback(progress_callback)

        try:
            success = trainer.train(str(self.sample_dir))
            if success:
                return "✅ 학습 완료! 이제 방송을 시작할 수 있습니다."
            else:
                return "❌ 학습 실패. 로그를 확인해 주세요."
        except Exception as e:
            logger.error(f"학습 오류: {e}")
            return f"❌ 오류: {e}"

    def _generate_preview(self, text: str) -> Optional[str]:
        """학습된 목소리로 텍스트를 음성으로 변환하여 미리듣기를 제공합니다."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        trainer = VoiceCloneTrainer(self.settings)
        if not trainer.is_model_ready():
            return None

        try:
            from TTS.api import TTS  # type: ignore
            import tempfile

            tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            wav_files = list(self.model_dir.glob("*.wav"))
            speaker_wav = str(wav_files[0]) if wav_files else None

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                kwargs: dict[str, Any] = {
                    "text": text,
                    "language": self.settings.get("language", "ko"),
                    "file_path": tmp.name,
                }
                if speaker_wav:
                    kwargs["speaker_wav"] = speaker_wav

                tts.tts_to_file(**kwargs)
                return tmp.name

        except ImportError:
            logger.error("TTS 패키지가 필요합니다.")
            return None
        except Exception as e:
            logger.error(f"미리듣기 생성 오류: {e}")
            return None
