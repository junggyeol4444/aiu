#!/bin/bash
echo "🔧 AI 자율 방송 시스템 설치"

# Python 버전 체크
python3 --version || { echo "Python 3.10+ 필요"; exit 1; }

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# .env 파일 생성
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 .env 파일이 생성되었습니다. API 키를 설정해주세요."
fi

# 디렉토리 생성
mkdir -p data/voice_samples data/voice_models logs

# Ollama 설치 안내
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "📌 Ollama 설치가 필요합니다:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo "  ollama pull llama3"
fi

echo "✅ 설치 완료! ./run.sh 로 실행하세요."
