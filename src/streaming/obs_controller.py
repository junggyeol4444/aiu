"""
obs_controller.py - OBS WebSocket 원격 제어 모듈
OBS Studio를 WebSocket API를 통해 원격으로 제어합니다.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from loguru import logger


class OBSController:
    """OBS Studio WebSocket API를 통해 방송을 제어하는 클래스."""

    def __init__(self, settings: dict[str, Any]) -> None:
        """
        Args:
            settings: settings.yaml의 streaming 섹션
        """
        self.ws_url = settings.get("obs_websocket_url", "ws://localhost:4455")
        password_env = settings.get("obs_password_env", "OBS_PASSWORD")
        self.password = os.environ.get(password_env, "")
        self._client: Any = None

    async def connect(self) -> bool:
        """OBS WebSocket에 연결합니다."""
        try:
            import obsws_python as obs  # type: ignore

            self._client = obs.ReqClient(
                host=self._parse_host(),
                port=self._parse_port(),
                password=self.password,
            )
            logger.info(f"OBS WebSocket 연결 성공: {self.ws_url}")
            return True
        except ImportError:
            logger.error("obsws-python 패키지가 필요합니다: pip install obsws-python")
            return False
        except Exception as e:
            logger.error(f"OBS WebSocket 연결 실패: {e}")
            return False

    async def disconnect(self) -> None:
        """OBS WebSocket 연결을 종료합니다."""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        logger.info("OBS WebSocket 연결 종료")

    async def start_streaming(self) -> bool:
        """방송 송출을 시작합니다."""
        if not self._client:
            logger.warning("OBS에 연결되지 않았습니다.")
            return False
        try:
            self._client.start_stream()
            logger.info("OBS 방송 송출 시작")
            return True
        except Exception as e:
            logger.error(f"방송 시작 오류: {e}")
            return False

    async def stop_streaming(self) -> bool:
        """방송 송출을 중단합니다."""
        if not self._client:
            return False
        try:
            self._client.stop_stream()
            logger.info("OBS 방송 송출 중단")
            return True
        except Exception as e:
            logger.error(f"방송 중단 오류: {e}")
            return False

    async def switch_scene(self, scene_name: str) -> bool:
        """
        OBS 장면(Scene)을 전환합니다.

        Args:
            scene_name: 전환할 장면 이름

        Returns:
            성공 여부
        """
        if not self._client:
            return False
        try:
            self._client.set_current_program_scene(scene_name)
            logger.info(f"장면 전환: {scene_name}")
            return True
        except Exception as e:
            logger.error(f"장면 전환 오류: {e}")
            return False

    async def switch_to_ending_scene(self, scene_name: str = "엔딩") -> bool:
        """
        방종 엔딩 화면으로 장면을 전환합니다.

        Args:
            scene_name: 엔딩 장면 이름 (기본값: "엔딩")

        Returns:
            성공 여부
        """
        return await self.switch_scene(scene_name)

    async def get_streaming_status(self) -> dict[str, Any]:
        """방송 상태를 조회합니다."""
        if not self._client:
            return {"streaming": False, "connected": False}
        try:
            status = self._client.get_stream_status()
            return {
                "streaming": status.output_active,
                "connected": True,
                "duration": getattr(status, "output_duration", 0),
            }
        except Exception as e:
            logger.warning(f"방송 상태 조회 오류: {e}")
            return {"streaming": False, "connected": False}

    def _parse_host(self) -> str:
        """WebSocket URL에서 호스트를 파싱합니다."""
        url = self.ws_url.replace("ws://", "").replace("wss://", "")
        return url.split(":")[0]

    def _parse_port(self) -> int:
        """WebSocket URL에서 포트를 파싱합니다."""
        url = self.ws_url.replace("ws://", "").replace("wss://", "")
        parts = url.split(":")
        if len(parts) > 1:
            try:
                return int(parts[1].split("/")[0])
            except ValueError:
                pass
        return 4455
