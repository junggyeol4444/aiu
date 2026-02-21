"""
main.py - 메인 실행 진입점
AI 자율 방송 시스템을 시작합니다.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from loguru import logger


def load_settings() -> tuple[dict, dict]:
    """
    설정 파일들을 로드합니다.

    Returns:
        (settings, platform_config) 튜플
    """
    settings_path = Path("config/settings.yaml")
    platform_path = Path("config/platform.yaml")

    if not settings_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {settings_path}")
        sys.exit(1)

    with open(settings_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    platform_config: dict = {}
    if platform_path.exists():
        with open(platform_path, "r", encoding="utf-8") as f:
            platform_config = yaml.safe_load(f)

    return settings, platform_config


def configure_logging() -> None:
    """로깅 설정을 구성합니다."""
    logger.remove()  # 기본 핸들러 제거
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO",
    )
    logger.add(
        "logs/broadcaster.log",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
        level="DEBUG",
    )


async def run_with_dashboard(settings: dict, platform_config: dict) -> None:
    """대시보드와 함께 방송 시스템을 실행합니다."""
    from src.broadcast_loop import BroadcastLoop
    from src.ui.dashboard import Dashboard

    broadcast_loop = BroadcastLoop(settings, platform_config)
    await broadcast_loop.initialize()

    dashboard = Dashboard(broadcast_loop, settings.get("ui", {}))

    # 대시보드를 별도 스레드에서 실행 (Gradio는 blocking)
    import threading

    dashboard_thread = threading.Thread(
        target=dashboard.launch,
        daemon=True,
        name="DashboardThread",
    )
    dashboard_thread.start()

    logger.info("대시보드 시작됨. 방송을 수동으로 시작하려면 대시보드를 사용하세요.")
    logger.info(f"대시보드 URL: http://localhost:{settings.get('ui', {}).get('port', 7860)}")

    # 메인 프로세스 유지
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await broadcast_loop.stop()


async def run_headless(settings: dict, platform_config: dict) -> None:
    """UI 없이 방송 시스템을 직접 실행합니다."""
    from src.broadcast_loop import BroadcastLoop

    broadcast_loop = BroadcastLoop(settings, platform_config)
    await broadcast_loop.initialize()

    try:
        await broadcast_loop.start()
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트 감지. 방송을 중단합니다...")
        await broadcast_loop.stop()


def main() -> None:
    """메인 실행 함수."""
    # .env 파일 로드
    load_dotenv()

    # 로깅 설정
    configure_logging()

    logger.info("=" * 60)
    logger.info("🤖 AI 자율 방송 시스템 시작")
    logger.info("=" * 60)

    # 설정 로드
    settings, platform_config = load_settings()

    # 실행 모드 결정 (환경 변수로 제어)
    headless = os.environ.get("HEADLESS", "false").lower() == "true"

    if headless:
        logger.info("헤드리스 모드로 실행합니다.")
        asyncio.run(run_headless(settings, platform_config))
    else:
        logger.info("대시보드 모드로 실행합니다.")
        asyncio.run(run_with_dashboard(settings, platform_config))


if __name__ == "__main__":
    main()
