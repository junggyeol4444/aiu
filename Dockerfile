FROM python:3.10-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    pulseaudio \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 환경 변수 파일
ENV PYTHONPATH=/app

# 포트 (Gradio UI)
EXPOSE 7860

# 메인 실행
CMD ["python", "src/main.py"]
