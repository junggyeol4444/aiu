"""
test_voice.py - 음성 엔진 모듈 단위 테스트
"""

from __future__ import annotations

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── EmotionController 테스트 ───────────────────────────────────────

class TestEmotionController:
    """EmotionController 클래스 테스트."""

    def test_detect_excited_emotion(self) -> None:
        """흥분 감정 감지 테스트."""
        from src.voice.emotion_control import EmotionController, Emotion

        controller = EmotionController()
        emotion = controller.detect_emotion("와 이거 완전 대박이다 ㅋㅋㅋ!!!")
        assert emotion == Emotion.EXCITED

    def test_detect_happy_emotion(self) -> None:
        """기쁨 감정 감지 테스트."""
        from src.voice.emotion_control import EmotionController, Emotion

        controller = EmotionController()
        emotion = controller.detect_emotion("감사합니다! 정말 행복해요!")
        assert emotion == Emotion.HAPPY

    def test_detect_neutral_emotion(self) -> None:
        """중립 감정 감지 테스트."""
        from src.voice.emotion_control import EmotionController, Emotion

        controller = EmotionController()
        emotion = controller.detect_emotion("오늘 날씨가 맑습니다.")
        assert emotion == Emotion.NEUTRAL

    def test_get_tone_parameters(self) -> None:
        """톤 파라미터 반환 테스트."""
        from src.voice.emotion_control import EmotionController

        controller = EmotionController()
        tone = controller.get_tone_parameters("와 대박이다!!!")
        assert tone.speed > 1.0  # 흥분 상태에서 빠른 속도
        assert isinstance(tone.temperature, float)

    def test_tone_parameters_range(self) -> None:
        """톤 파라미터가 유효한 범위 내에 있는지 테스트."""
        from src.voice.emotion_control import EmotionController, Emotion

        controller = EmotionController()
        for emotion in Emotion:
            tone = controller._TONE_MAP.get(emotion)
            if tone:
                assert 0.5 <= tone.speed <= 2.0, f"{emotion}: speed={tone.speed} 범위 초과"
                assert 0.0 <= tone.temperature <= 1.0, f"{emotion}: temperature={tone.temperature} 범위 초과"

    def test_apply_emotion_without_tag(self) -> None:
        """감정 태그가 없을 때 원본 텍스트를 반환하는지 테스트."""
        from src.voice.emotion_control import EmotionController, Emotion

        controller = EmotionController()
        text = "안녕하세요!"
        result = controller.apply_emotion(text, Emotion.NEUTRAL)
        # 태그가 없으면 원본 반환
        assert text in result


# ── RealtimeTTS 문장 분할 테스트 ──────────────────────────────────

class TestRealtimeTTSSentenceSplit:
    """RealtimeTTS의 문장 분할 기능 테스트."""

    def test_split_sentences_basic(self) -> None:
        """기본 문장 분할 테스트."""
        from src.voice.realtime_tts import RealtimeTTS

        sentences = RealtimeTTS._split_sentences("안녕하세요. 반갑습니다. 잘 부탁드립니다.")
        assert len(sentences) == 3

    def test_split_sentences_exclamation(self) -> None:
        """느낌표로 끝나는 문장 분할 테스트."""
        from src.voice.realtime_tts import RealtimeTTS

        sentences = RealtimeTTS._split_sentences("와! 대박! 레전드!")
        assert len(sentences) == 3

    def test_split_sentences_single(self) -> None:
        """단일 문장 분할 테스트."""
        from src.voice.realtime_tts import RealtimeTTS

        sentences = RealtimeTTS._split_sentences("안녕하세요")
        assert len(sentences) == 1
        assert sentences[0] == "안녕하세요"

    def test_split_sentences_empty(self) -> None:
        """빈 텍스트 분할 테스트."""
        from src.voice.realtime_tts import RealtimeTTS

        sentences = RealtimeTTS._split_sentences("")
        assert sentences == []

    def test_split_sentences_mixed_punctuation(self) -> None:
        """여러 구두점이 섞인 문장 분할 테스트."""
        from src.voice.realtime_tts import RealtimeTTS

        text = "오늘 날씨가 좋네요! 나가볼까요? 같이 가요."
        sentences = RealtimeTTS._split_sentences(text)
        assert len(sentences) == 3


# ── VoiceCloneTrainer 테스트 ───────────────────────────────────────

class TestVoiceCloneTrainer:
    """VoiceCloneTrainer 클래스 테스트."""

    def test_is_model_ready_false_when_no_files(self, tmp_path) -> None:
        """모델 파일이 없을 때 False를 반환하는지 테스트."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        settings = {"model_path": str(tmp_path), "engine": "xtts_v2", "sample_rate": 22050}
        trainer = VoiceCloneTrainer(settings)
        assert not trainer.is_model_ready()

    def test_is_model_ready_true_when_wav_exists(self, tmp_path) -> None:
        """WAV 파일이 있을 때 True를 반환하는지 테스트."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        # 더미 WAV 파일 생성
        wav_file = tmp_path / "sample.wav"
        wav_file.touch()

        settings = {"model_path": str(tmp_path), "engine": "xtts_v2", "sample_rate": 22050}
        trainer = VoiceCloneTrainer(settings)
        assert trainer.is_model_ready()

    def test_preprocess_empty_dir(self, tmp_path) -> None:
        """빈 디렉토리에서 전처리 시 빈 목록 반환 테스트."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        model_dir = tmp_path / "models"
        model_dir.mkdir()
        empty_sample_dir = tmp_path / "samples"
        empty_sample_dir.mkdir()

        settings = {"model_path": str(model_dir), "engine": "xtts_v2", "sample_rate": 22050}
        trainer = VoiceCloneTrainer(settings)
        result = trainer.preprocess_samples(str(empty_sample_dir))
        assert result == []

    def test_progress_callback(self, tmp_path) -> None:
        """진행 콜백이 올바르게 호출되는지 테스트."""
        from src.voice.clone_trainer import VoiceCloneTrainer

        settings = {"model_path": str(tmp_path), "engine": "xtts_v2", "sample_rate": 22050}
        trainer = VoiceCloneTrainer(settings)

        callback_calls: list[tuple[float, str]] = []

        def callback(progress: float, message: str) -> None:
            callback_calls.append((progress, message))

        trainer.set_progress_callback(callback)
        trainer._report_progress(0.5, "테스트 메시지")

        assert len(callback_calls) == 1
        assert callback_calls[0] == (0.5, "테스트 메시지")
