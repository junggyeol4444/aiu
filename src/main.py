"""
main.py - 메인 실행 진입점
AI 자율 방송 시스템을 시작합니다.
"""

from __future__ import annotations

import argparse
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


def parse_args() -> argparse.Namespace:
    """명령행 인수를 파싱합니다."""
    parser = argparse.ArgumentParser(description="AI 자율 방송 시스템")
    parser.add_argument(
        "--mode",
        choices=["schedule", "now", "dashboard"],
        default=None,
        help=(
            "실행 모드: "
            "schedule=스케줄에 따라 자동 시작/종료, "
            "now=즉시 방송 시작 (헤드리스), "
            "dashboard=대시보드 UI 모드 (기본값)"
        ),
    )
    return parser.parse_args()


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


async def run_schedule_mode(settings: dict, platform_config: dict) -> None:
    """스케줄 모드로 방송 시스템을 실행합니다."""
    from src.broadcast_loop import BroadcastLoop
    from src.scheduler import BroadcastScheduler

    broadcast_loop = BroadcastLoop(settings, platform_config)
    await broadcast_loop.initialize()

    scheduler = BroadcastScheduler(broadcast_loop)
    if not scheduler.enabled:
        logger.warning("스케줄이 비활성화되어 있습니다. config/schedule.yaml을 확인하세요.")
        return

    try:
        await scheduler.run()
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트 감지. 스케줄러를 중단합니다...")
        scheduler.stop()
        await broadcast_loop.stop()


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

    # Ollama 상태 자동 체크
    llm_cfg = settings.get("llm", {})
    ollama_url = llm_cfg.get("ollama_url", "http://localhost:11434")
    model = llm_cfg.get("model", "llama3")

    async def _check_and_run() -> None:
        from src.utils.ollama_checker import ensure_ollama_ready
        ready = await ensure_ollama_ready(model, ollama_url)
        if not ready:
            logger.error("Ollama 준비 실패. 시스템을 종료합니다.")
            sys.exit(1)

    # 명령행 인수 파싱
    args = parse_args()

    # 실행 모드 결정 (명령행 인수 → 환경 변수 순)
    run_mode = args.mode
    if run_mode is None:
        if os.environ.get("HEADLESS", "false").lower() == "true":
            run_mode = "now"
        else:
            run_mode = "dashboard"

    if run_mode == "schedule":
        logger.info("스케줄 모드로 실행합니다.")
        asyncio.run(_schedule_main(settings, platform_config, ollama_url, model))
    elif run_mode == "now":
        logger.info("즉시 방송 모드로 실행합니다.")
        asyncio.run(_headless_main(settings, platform_config, ollama_url, model))
    else:
        logger.info("대시보드 모드로 실행합니다.")
        asyncio.run(_dashboard_main(settings, platform_config, ollama_url, model))


async def _check_ollama(ollama_url: str, model: str) -> None:
    """Ollama 준비 상태를 확인합니다."""
    from src.utils.ollama_checker import ensure_ollama_ready
    ready = await ensure_ollama_ready(model, ollama_url)
    if not ready:
        logger.error("Ollama 준비 실패. 시스템을 종료합니다.")
        sys.exit(1)


async def _schedule_main(
    settings: dict, platform_config: dict, ollama_url: str, model: str
) -> None:
    """스케줄 모드 진입점."""
    await _check_ollama(ollama_url, model)
    await run_schedule_mode(settings, platform_config)


async def _headless_main(
    settings: dict, platform_config: dict, ollama_url: str, model: str
) -> None:
    """헤드리스 모드 진입점."""
    await _check_ollama(ollama_url, model)
    await run_headless(settings, platform_config)


async def _dashboard_main(
    settings: dict, platform_config: dict, ollama_url: str, model: str
) -> None:
    """대시보드 모드 진입점."""
    await _check_ollama(ollama_url, model)
    await run_with_dashboard(settings, platform_config)


if __name__ == "__main__":
    main()
