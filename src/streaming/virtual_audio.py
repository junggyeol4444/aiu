"""
virtual_audio.py - 가상 오디오 디바이스 관리 모듈
생성된 음성을 OBS로 라우팅하기 위한 가상 오디오 디바이스를 관리합니다.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Optional

from loguru import logger


class VirtualAudioManager:
    """
    가상 오디오 디바이스를 설정하고 음성 라우팅을 관리하는 클래스.

    Linux: PulseAudio 가상 싱크 사용
    Windows: VB-Cable 또는 Voicemeeter 가이드 제공
    macOS: BlackHole 가이드 제공
    """

    def __init__(self) -> None:
        self.platform = sys.platform
        self._virtual_sink_name = "ai_broadcaster_sink"
        self._null_sink_index: Optional[int] = None

    def setup(self) -> bool:
        """
        플랫폼에 맞는 가상 오디오 디바이스를 설정합니다.

        Returns:
            설정 성공 여부
        """
        if self.platform.startswith("linux"):
            return self._setup_pulseaudio()
        elif self.platform == "win32":
            logger.info(
                "Windows에서는 VB-Cable 또는 Voicemeeter를 설치하고 "
                "OBS에서 오디오 입력으로 설정해 주세요."
            )
            return True
        elif self.platform == "darwin":
            logger.info(
                "macOS에서는 BlackHole 또는 Loopback을 설치하고 "
                "OBS에서 오디오 입력으로 설정해 주세요."
            )
            return True
        else:
            logger.warning(f"지원하지 않는 플랫폼: {self.platform}")
            return False

    def teardown(self) -> None:
        """가상 오디오 디바이스를 정리합니다."""
        if self.platform.startswith("linux") and self._null_sink_index is not None:
            self._remove_pulseaudio_sink()

    def get_virtual_device_name(self) -> str:
        """OBS에 입력해야 할 가상 오디오 디바이스 이름을 반환합니다."""
        if self.platform.startswith("linux"):
            return f"{self._virtual_sink_name}.monitor"
        return "VB-Cable Input (Windows) / BlackHole (macOS)"

    # ── Linux PulseAudio ──────────────────────────────────────────────

    def _setup_pulseaudio(self) -> bool:
        """PulseAudio 가상 Null Sink를 생성합니다."""
        try:
            result = subprocess.run(
                [
                    "pactl",
                    "load-module",
                    "module-null-sink",
                    f"sink_name={self._virtual_sink_name}",
                    f"sink_properties=device.description=AI_Broadcaster",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self._null_sink_index = int(result.stdout.strip())
            logger.info(f"PulseAudio 가상 싱크 생성: {self._virtual_sink_name} (index={self._null_sink_index})")
            return True
        except FileNotFoundError:
            logger.warning("pactl 명령어를 찾을 수 없습니다. PulseAudio가 설치되어 있나요?")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"PulseAudio 가상 싱크 생성 실패: {e.stderr}")
            return False

    def _remove_pulseaudio_sink(self) -> None:
        """생성한 PulseAudio 가상 싱크를 제거합니다."""
        try:
            subprocess.run(
                ["pactl", "unload-module", str(self._null_sink_index)],
                check=True,
                capture_output=True,
            )
            logger.info(f"PulseAudio 가상 싱크 제거: index={self._null_sink_index}")
        except Exception as e:
            logger.warning(f"PulseAudio 가상 싱크 제거 실패: {e}")
