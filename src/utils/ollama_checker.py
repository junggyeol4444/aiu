"""
ollama_checker.py - Ollama 서비스 및 모델 자동 체크 모듈
시스템 시작 시 Ollama 연결 가능 여부와 필요 모델 존재 여부를 확인합니다.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Optional

import aiohttp
from loguru import logger


async def check_ollama_connection(ollama_url: str = "http://localhost:11434") -> bool:
    """
    Ollama 서비스가 실행 중이고 연결 가능한지 확인합니다.

    Args:
        ollama_url: Ollama 서비스 URL

    Returns:
        연결 가능하면 True, 아니면 False
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ollama_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
    except Exception as e:
        logger.warning(f"Ollama 연결 실패: {e}")
        return False


async def check_model_available(
    model: str,
    ollama_url: str = "http://localhost:11434",
) -> bool:
    """
    지정된 모델이 Ollama에 다운로드되어 있는지 확인합니다.

    Args:
        model: 확인할 모델 이름 (예: "llama3")
        ollama_url: Ollama 서비스 URL

    Returns:
        모델이 사용 가능하면 True, 아니면 False
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ollama_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
                return model.split(":")[0] in models
    except Exception as e:
        logger.warning(f"모델 목록 조회 실패: {e}")
        return False


def pull_model(model: str) -> bool:
    """
    Ollama 모델을 자동으로 다운로드합니다.

    Args:
        model: 다운로드할 모델 이름

    Returns:
        성공하면 True, 실패하면 False
    """
    logger.info(f"📥 모델 다운로드 중: {model}")
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=False,
            check=True,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"모델 다운로드 실패: {e}")
        return False
    except FileNotFoundError:
        logger.error("ollama 명령어를 찾을 수 없습니다. Ollama가 설치되어 있는지 확인하세요.")
        return False


async def ensure_ollama_ready(
    model: str,
    ollama_url: str = "http://localhost:11434",
    auto_pull: bool = True,
) -> bool:
    """
    Ollama 서비스가 준비되었는지 확인하고, 모델이 없으면 자동으로 다운로드합니다.

    시스템 시작 시 main.py 초기화 과정에서 호출됩니다.

    Args:
        model: 사용할 모델 이름
        ollama_url: Ollama 서비스 URL
        auto_pull: 모델이 없을 때 자동 다운로드 여부

    Returns:
        준비 완료되면 True, 아니면 False
    """
    logger.info("Ollama 상태 확인 중...")

    # 1. Ollama 서비스 연결 확인
    connected = await check_ollama_connection(ollama_url)
    if not connected:
        logger.error(
            "❌ Ollama 서비스에 연결할 수 없습니다.\n"
            "  Ollama가 실행 중인지 확인하세요: ollama serve"
        )
        return False

    logger.info("✅ Ollama 서비스 연결 확인")

    # 2. 모델 존재 여부 확인
    model_ready = await check_model_available(model, ollama_url)
    if not model_ready:
        if auto_pull:
            logger.info(f"모델 '{model}'이 없습니다. 자동 다운로드를 시작합니다...")
            # pull은 블로킹 작업이므로 executor에서 실행
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, pull_model, model)
            if not success:
                logger.error(f"❌ 모델 '{model}' 다운로드 실패")
                return False
            logger.info(f"✅ 모델 '{model}' 다운로드 완료")
        else:
            logger.error(
                f"❌ 모델 '{model}'이 없습니다.\n"
                f"  ollama pull {model} 으로 다운로드하세요."
            )
            return False
    else:
        logger.info(f"✅ 모델 '{model}' 사용 가능")

    return True
