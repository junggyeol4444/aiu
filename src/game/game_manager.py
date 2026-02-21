"""
game_manager.py - 게임 프로세스 관리 모듈
게임 실행/종료/상태 체크 및 OBS 장면 전환을 담당합니다.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Optional

from loguru import logger


class GameManager:
    """
    게임 방송 모드에서 게임 프로세스와 OBS 장면을 관리하는 클래스.

    설정된 게임 목록에서 게임을 선택하고,
    프로세스 실행/종료와 OBS 장면 전환을 수행합니다.
    """

    def __init__(self, game_config: dict[str, Any]) -> None:
        """
        Args:
            game_config: settings.yaml의 game 섹션 설정
        """
        self.enabled: bool = game_config.get("enabled", False)
        self.launch_method: str = game_config.get("launch_method", "process")
        self.games: list[dict[str, Any]] = game_config.get("games", [])
        self._current_game: Optional[dict[str, Any]] = None
        self._process: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

    @property
    def current_game(self) -> Optional[dict[str, Any]]:
        """현재 실행 중인 게임 정보를 반환합니다."""
        return self._current_game

    @property
    def is_game_running(self) -> bool:
        """게임 프로세스가 실행 중인지 확인합니다."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def get_game_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """
        이름으로 게임 설정을 찾습니다.

        Args:
            name: 게임 이름

        Returns:
            게임 설정 딕셔너리 또는 None
        """
        for game in self.games:
            if game.get("name", "").lower() == name.lower():
                return game
        return None

    def start_game(self, game_name: str) -> bool:
        """
        게임을 시작합니다.

        Args:
            game_name: 시작할 게임 이름

        Returns:
            성공하면 True, 실패하면 False
        """
        game = self.get_game_by_name(game_name)
        if game is None:
            logger.error(f"게임을 찾을 수 없습니다: {game_name}")
            return False

        launch_cmd = game.get("launch_command", "")
        if not launch_cmd:
            logger.info(f"'{game_name}' 수동 실행 모드 (launch_command 없음)")
            self._current_game = game
            return True

        try:
            self._process = subprocess.Popen(
                launch_cmd.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._current_game = game
            logger.info(f"게임 시작: {game_name} (PID: {self._process.pid})")
            return True
        except Exception as e:
            logger.error(f"게임 실행 오류: {e}")
            return False

    def stop_game(self) -> None:
        """현재 실행 중인 게임을 종료합니다."""
        if self._process and self.is_game_running:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            logger.info(f"게임 종료: {self._current_game.get('name', '') if self._current_game else ''}")

        self._process = None
        self._current_game = None

    def check_process_running(self, process_name: str) -> bool:
        """
        지정된 이름의 프로세스가 실행 중인지 확인합니다.
        이미 실행된 게임 창을 캡처하는 모드(window)에서 사용합니다.

        Args:
            process_name: 확인할 프로세스 이름

        Returns:
            실행 중이면 True, 아니면 False
        """
        try:
            if sys.platform == "win32":
                output = subprocess.check_output(
                    ["tasklist", "/fi", f"imagename eq {process_name}"],
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="replace")
                return process_name.lower() in output.lower()
            else:
                output = subprocess.check_output(
                    ["pgrep", "-f", process_name],
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="replace")
                return bool(output.strip())
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            logger.warning(f"프로세스 확인 오류: {e}")
            return False

    def detect_running_game(self) -> Optional[dict[str, Any]]:
        """
        현재 실행 중인 게임을 자동으로 감지합니다.
        window 모드에서 이미 실행된 게임 창을 찾을 때 사용합니다.

        Returns:
            감지된 게임 설정 또는 None
        """
        for game in self.games:
            process_name = game.get("process_name", "")
            if process_name and self.check_process_running(process_name):
                logger.info(f"실행 중인 게임 감지: {game.get('name', '')}")
                self._current_game = game
                return game
        return None
