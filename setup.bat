@echo off
chcp 65001 > nul
echo 🔧 AI 자율 방송 시스템 설치

python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo 📝 .env 파일 생성됨. API 키를 설정해주세요.
)

mkdir data\voice_samples 2>nul
mkdir data\voice_models 2>nul
mkdir logs 2>nul

echo ✅ 설치 완료! run.bat 으로 실행하세요.
pause
