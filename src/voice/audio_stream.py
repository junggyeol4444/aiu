"""
audio_stream.py - 오디오 스트리밍 출력 모듈
생성된 음성을 실제 오디오 장치로 출력합니다.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class AudioStream:
    """
    생성된 음성 데이터를 오디오 장치로 스트리밍 출력하는 클래스.
    백그라운드 스레드에서 재생하여 메인 루프를 블로킹하지 않습니다.
    """

    def __init__(self, sample_rate: int = 22050, device: Optional[str] = None) -> None:
        """
        Args:
            sample_rate: 오디오 샘플레이트 (Hz)
            device: 출력 오디오 장치 이름 (None이면 기본 장치)
        """
        self.sample_rate = sample_rate
        self.device = device
        self._playback_queue: queue.Queue[Optional[Any]] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """오디오 재생 워커 스레드를 시작합니다."""
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._playback_worker,
            daemon=True,
            name="AudioStreamWorker",
        )
        self._worker_thread.start()
        logger.info("오디오 스트림 워커 시작")

    def stop(self) -> None:
        """오디오 재생을 중단합니다."""
        self._running = False
        self._playback_queue.put(None)  # 종료 신호
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("오디오 스트림 중단")

    def play_audio(self, audio_data: Any) -> None:
        """
        오디오 데이터를 재생 큐에 추가합니다.

        Args:
            audio_data: 재생할 오디오 NumPy 배열
        """
        self._playback_queue.put(audio_data)

    async def play_file(self, file_path: str) -> None:
        """
        오디오 파일을 비동기적으로 재생합니다.

        Args:
            file_path: 재생할 오디오 파일 경로
        """
        try:
            import numpy as np  # type: ignore
            import soundfile as sf  # type: ignore

            data, sr = sf.read(file_path)
            if sr != self.sample_rate:
                import librosa  # type: ignore

                data = librosa.resample(data, orig_sr=sr, target_sr=self.sample_rate)

            self.play_audio(data.astype(np.float32))
        except Exception as e:
            logger.error(f"파일 재생 오류 ({file_path}): {e}")

    def _playback_worker(self) -> None:
        """백그라운드 스레드에서 오디오를 재생하는 워커."""
        try:
            import sounddevice as sd  # type: ignore
        except ImportError:
            logger.error("sounddevice 패키지가 필요합니다: pip install sounddevice")
            return

        while self._running:
            try:
                audio_data = self._playback_queue.get(timeout=1)
                if audio_data is None:
                    break

                sd.play(audio_data, samplerate=self.sample_rate, device=self.device)
                sd.wait()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"오디오 재생 오류: {e}")
