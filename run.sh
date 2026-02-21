#!/bin/bash
# AI 자율 방송 시스템 실행 스크립트
# Ollama 실행 여부 확인 → 가상환경 활성화 → 시스템 실행

set -e

# Ollama 체크
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama가 설치되어 있지 않습니다."
    echo "설치: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# Ollama 서비스 실행 확인
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "🔄 Ollama 서비스 시작 중..."
    ollama serve &
    sleep 3
fi

# 모델 체크 및 자동 다운로드
MODEL=$(python3 -c "import yaml; print(yaml.safe_load(open('config/settings.yaml'))['llm']['model'])" 2>/dev/null || echo "llama3")
if ! ollama list | grep -q "$MODEL"; then
    echo "📥 모델 다운로드 중: $MODEL"
    ollama pull "$MODEL"
fi

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 실행
python src/main.py "$@"
