@echo off
chcp 65001 > nul
echo ========================================
echo  AI 자율 방송 시스템 실행
echo ========================================

:: Ollama 체크
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Ollama가 설치되어 있지 않습니다.
    echo https://ollama.com/download 에서 설치해주세요.
    pause
    exit /b 1
)

:: 가상환경 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: 실행
python src\main.py %*
pause
