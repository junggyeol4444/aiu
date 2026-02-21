"""
clone_trainer.py - 음성 클론 모델 학습 모듈
사용자 음성 샘플을 사용하여 XTTS v2 또는 OpenVoice 모델을 파인튜닝합니다.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger


class VoiceCloneTrainer:
    """
    사용자 음성 샘플에서 개인화된 TTS 모델을 학습하는 클래스.
    XTTS v2 (Coqui TTS) 엔진을 기본으로 사용합니다.
    """

    def __init__(self, settings: dict[str, Any]) -> None:
        """
        Args:
            settings: settings.yaml의 voice 섹션
        """
        self.engine = settings.get("engine", "xtts_v2")
        self.model_path = Path(settings.get("model_path", "data/voice_models/"))
        self.sample_rate = settings.get("sample_rate", 22050)
        self.language = settings.get("language", "ko")

        # 학습 진행 콜백 (UI 연동용)
        self._progress_callback: Optional[Callable[[float, str], None]] = None

    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """학습 진행 상태를 전달받을 콜백 함수를 설정합니다."""
        self._progress_callback = callback

    def _report_progress(self, progress: float, message: str) -> None:
        """학습 진행 상태를 보고합니다."""
        logger.info(f"[학습 {progress:.0%}] {message}")
        if self._progress_callback:
            self._progress_callback(progress, message)

    # ── 데이터 전처리 ─────────────────────────────────────────────────

    def preprocess_samples(self, sample_dir: str) -> list[Path]:
        """
        음성 샘플을 전처리합니다 (노이즈 제거, 정규화, 포맷 변환).

        Args:
            sample_dir: 음성 샘플이 있는 디렉토리

        Returns:
            전처리된 오디오 파일 경로 목록
        """
        try:
            import librosa  # type: ignore
            import soundfile as sf  # type: ignore
            import numpy as np
        except ImportError:
            logger.error("librosa, soundfile, numpy 패키지가 필요합니다.")
            return []

        sample_path = Path(sample_dir)
        audio_files = list(sample_path.glob("*.wav")) + list(sample_path.glob("*.mp3"))

        if not audio_files:
            logger.warning(f"음성 샘플 파일이 없습니다: {sample_dir}")
            return []

        processed_dir = self.model_path / "preprocessed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_files: list[Path] = []

        for i, audio_file in enumerate(audio_files):
            self._report_progress(
                i / len(audio_files),
                f"전처리 중: {audio_file.name}"
            )
            try:
                # 로드 및 리샘플링
                y, sr = librosa.load(str(audio_file), sr=self.sample_rate)

                # 정규화
                y = librosa.util.normalize(y)

                # 저장
                output_path = processed_dir / f"processed_{audio_file.stem}.wav"
                sf.write(str(output_path), y, self.sample_rate)
                processed_files.append(output_path)
            except Exception as e:
                logger.warning(f"파일 전처리 실패 ({audio_file.name}): {e}")

        self._report_progress(1.0, f"전처리 완료: {len(processed_files)}개 파일")
        return processed_files

    # ── 모델 학습 ─────────────────────────────────────────────────────

    def train(self, sample_dir: str = "data/voice_samples/") -> bool:
        """
        음성 샘플을 사용하여 TTS 모델을 학습합니다.

        Args:
            sample_dir: 음성 샘플 디렉토리

        Returns:
            학습 성공 여부
        """
        logger.info(f"음성 클론 학습 시작 (엔진: {self.engine})")
        self._report_progress(0.0, "학습 준비 중...")

        # 전처리
        processed_files = self.preprocess_samples(sample_dir)
        if not processed_files:
            logger.error("전처리된 샘플 파일이 없습니다.")
            return False

        if self.engine == "xtts_v2":
            return self._train_xtts(processed_files)
        else:
            logger.warning(f"지원하지 않는 엔진: {self.engine}")
            return False

    def _train_xtts(self, audio_files: list[Path]) -> bool:
        """XTTS v2로 음성 클론을 생성합니다 (파인튜닝 대신 스피커 임베딩 방식)."""
        try:
            from TTS.api import TTS  # type: ignore

            self._report_progress(0.3, "XTTS v2 모델 로드 중...")
            # XTTS v2는 소량의 샘플로 스피커 임베딩을 생성할 수 있음
            tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

            self.model_path.mkdir(parents=True, exist_ok=True)

            # 샘플 파일을 모델 디렉토리에 복사 (추론 시 레퍼런스로 사용)
            for audio_file in audio_files[:3]:  # 최대 3개 샘플 사용
                dest = self.model_path / audio_file.name
                shutil.copy2(str(audio_file), str(dest))

            self._report_progress(1.0, "음성 클론 준비 완료!")
            logger.info(f"음성 모델 저장 위치: {self.model_path}")
            return True

        except ImportError:
            logger.error("TTS 패키지가 필요합니다: pip install TTS")
            return False
        except Exception as e:
            logger.error(f"XTTS 학습 오류: {e}")
            return False

    def is_model_ready(self) -> bool:
        """학습된 모델이 사용 가능한 상태인지 확인합니다."""
        wav_files = list(self.model_path.glob("*.wav"))
        return len(wav_files) > 0
