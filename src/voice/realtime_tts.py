"""
realtime_tts.py - 실시간 텍스트→음성 변환 모듈
학습된 사용자 목소리로 텍스트를 저지연으로 변환합니다.
문장 분할 처리로 앞부분부터 즉시 재생합니다.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from loguru import logger

from src.voice.audio_stream import AudioStream
from src.voice.emotion_control import EmotionController


class RealtimeTTS:
    """
    학습된 개인화 TTS 모델로 텍스트를 실시간 음성으로 변환하는 클래스.
    저지연을 위해 문장 단위로 분할하여 처리합니다.
    """

    def __init__(
        self,
        settings: dict[str, Any],
        audio_stream: AudioStream,
    ) -> None:
        """
        Args:
            settings: settings.yaml의 voice 섹션
            audio_stream: 오디오 출력 스트림 객체
        """
        self.settings = settings
        self.audio_stream = audio_stream
        self.emotion_controller = EmotionController()
        self.model_path = Path(settings.get("model_path", "data/voice_models/"))
        self.sample_rate = settings.get("sample_rate", 22050)
        self.language = settings.get("language", "ko")

        self._tts_model: Any = None
        self._speaker_wav: Optional[str] = None

    def initialize(self) -> bool:
        """TTS 모델을 로드합니다. 방송 시작 전에 호출해야 합니다."""
        try:
            from TTS.api import TTS  # type: ignore

            logger.info("XTTS v2 모델 로딩 중...")
            self._tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

            # 레퍼런스 음성 파일 탐색
            wav_files = list(self.model_path.glob("*.wav"))
            if wav_files:
                self._speaker_wav = str(wav_files[0])
                logger.info(f"레퍼런스 음성: {self._speaker_wav}")
            else:
                logger.warning(
                    "레퍼런스 음성 파일이 없습니다. 기본 목소리를 사용합니다. "
                    "'음성 학습'을 먼저 실행해 주세요."
                )

            logger.info("TTS 모델 로드 완료")
            return True

        except ImportError:
            logger.error("TTS 패키지가 필요합니다: pip install TTS")
            return False
        except Exception as e:
            logger.error(f"TTS 모델 로드 실패: {e}")
            return False

    async def speak_realtime(self, text: str) -> None:
        """
        텍스트를 음성으로 변환하여 즉시 재생합니다.
        문장 단위로 분할하여 첫 문장부터 바로 재생합니다.

        Args:
            text: 발화할 텍스트
        """
        if not text.strip():
            return

        # 감정 파라미터 결정
        tone = self.emotion_controller.get_tone_parameters(text)

        # 문장 분할
        sentences = self._split_sentences(text)

        for sentence in sentences:
            if not sentence.strip():
                continue

            audio_data = await self._text_to_audio(sentence, tone.speed, tone.temperature)
            if audio_data is not None:
                self.audio_stream.play_audio(audio_data)

    async def speak_streaming(self, text_chunks: AsyncIterator[str]) -> None:
        """
        스트리밍 텍스트 청크를 실시간으로 음성으로 변환합니다.
        LLM 스트리밍 응답과 연동합니다.

        Args:
            text_chunks: 텍스트 청크를 생성하는 비동기 이터레이터
        """
        buffer = ""
        async for chunk in text_chunks:
            buffer += chunk
            # 문장 끝 감지 시 즉시 처리
            if re.search(r"[.!?。！？\n]", buffer):
                sentences = self._split_sentences(buffer)
                # 마지막 불완전 문장은 버퍼에 유지
                for sentence in sentences[:-1]:
                    if sentence.strip():
                        tone = self.emotion_controller.get_tone_parameters(sentence)
                        audio = await self._text_to_audio(
                            sentence, tone.speed, tone.temperature
                        )
                        if audio is not None:
                            self.audio_stream.play_audio(audio)
                buffer = sentences[-1] if sentences else ""

        # 남은 버퍼 처리
        if buffer.strip():
            tone = self.emotion_controller.get_tone_parameters(buffer)
            audio = await self._text_to_audio(buffer, tone.speed, tone.temperature)
            if audio is not None:
                self.audio_stream.play_audio(audio)

    async def _text_to_audio(
        self,
        text: str,
        speed: float = 1.0,
        temperature: float = 0.65,
    ) -> Optional[Any]:
        """
        텍스트를 오디오 NumPy 배열로 변환합니다.

        Args:
            text: 변환할 텍스트
            speed: 말하기 속도
            temperature: 감정 온도

        Returns:
            오디오 NumPy 배열 또는 None (실패 시)
        """
        if self._tts_model is None:
            logger.warning("TTS 모델이 초기화되지 않았습니다.")
            return None

        try:
            import numpy as np  # type: ignore

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            loop = asyncio.get_event_loop()

            def _synthesize() -> None:
                kwargs: dict[str, Any] = {
                    "text": text,
                    "language": self.language,
                    "file_path": tmp_path,
                    "speed": speed,
                    "temperature": temperature,
                }
                if self._speaker_wav:
                    kwargs["speaker_wav"] = self._speaker_wav

                self._tts_model.tts_to_file(**kwargs)

            # CPU 집약 작업을 별도 스레드에서 실행
            await loop.run_in_executor(None, _synthesize)

            import soundfile as sf  # type: ignore

            audio_data, _ = sf.read(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            return audio_data.astype(np.float32)

        except Exception as e:
            logger.error(f"TTS 변환 오류: {e}")
            return None

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        텍스트를 문장 단위로 분할합니다.
        한국어 문장 구분자를 지원합니다.
        """
        # 문장 끝 구분자: . ! ? 。！？
        sentences = re.split(r"(?<=[.!?。！？])\s*", text)
        return [s.strip() for s in sentences if s.strip()]
