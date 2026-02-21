# AI 자율 방송 시스템 (AI Autonomous Broadcaster)

> 사용자의 목소리를 학습한 AI가 **스스로 생각하고, 판단하고, 말하는** 완전 자율 라이브 방송 시스템

---

## 📌 프로젝트 개요

대본을 미리 만들어서 읽는 것이 아니라, AI가 매 순간 상황을 인식하고 스스로 판단하여 실시간으로 말하는 자율 방송 시스템입니다.

```
감지한다 → 생각한다 → 말한다 → 듣는다
(채팅/상황)  (AI 판단)  (내 목소리)  (반응 확인)
```

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    AI 자율 방송 시스템                    │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  👁 인지엔진  │───▶│  🧠 AI 두뇌  │───▶│ 🎤 음성엔진│ │
│  │              │    │              │    │           │ │
│  │ • 채팅 수신  │    │ • Ollama LLM │    │ • XTTS v2 │ │
│  │ • 시청자 추적│    │ • 행동 결정  │    │ • 실시간  │ │
│  │ • 이벤트 감지│    │ • 발화 생성  │    │   TTS     │ │
│  │ • 채팅/이벤트 │    │ • 메모리 관리│    │ • 감정 제어│ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│          │                  │                  │        │
│          └──────────────────┴──────────────────┘        │
│                             │                           │
│                    ┌────────▼────────┐                  │
│                    │  📡 방송 송출   │                  │
│                    │  • OBS 제어     │                  │
│                    │  • 가상 오디오  │                  │
│                    │  • 플랫폼 어댑터│                  │
│                    └─────────────────┘                  │
│                                                         │
│              🖥 Gradio 관리 대시보드                      │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 디렉토리 구조

```
ai-autonomous-broadcaster/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── config/
│   ├── persona.yaml          # AI 성격/말투 설정
│   ├── platform.yaml         # 방송 플랫폼 설정
│   └── settings.yaml         # 전체 설정
├── src/
│   ├── main.py               # 메인 실행
│   ├── broadcast_loop.py     # 메인 방송 루프
│   ├── brain/                # 🧠 AI 두뇌
│   │   ├── core.py
│   │   ├── persona.py
│   │   ├── memory.py
│   │   ├── action_decider.py
│   │   └── prompts/
│   ├── perception/           # 👁 인지 엔진
│   │   ├── chat_listener.py
│   │   ├── viewer_tracker.py
│   │   ├── event_detector.py
│   │   ├── external_info.py
│   │   └── context_builder.py
│   ├── voice/                # 🎤 음성 엔진
│   │   ├── clone_trainer.py
│   │   ├── realtime_tts.py
│   │   ├── emotion_control.py
│   │   └── audio_stream.py
│   ├── streaming/            # 📡 방송 송출
│   │   ├── obs_controller.py
│   │   ├── virtual_audio.py
│   │   └── platform_adapter.py
│   └── ui/                   # 🖥 관리 대시보드
│       ├── dashboard.py
│       └── voice_setup.py
├── data/
│   ├── voice_samples/        # 음성 샘플 저장
│   └── voice_models/         # 학습된 모델 저장
└── tests/
    ├── test_brain.py
    ├── test_perception.py
    └── test_voice.py
```

---

## 🚀 설치 방법

### Step 0: Ollama 설치 (필수)

```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# 모델 다운로드 (택 1)
ollama pull llama3          # 영어 위주, 범용
ollama pull gemma2          # 구글 모델, 한국어 양호
ollama pull qwen2.5         # 다국어 강함

# 한국어 특화 모델 (추천)
ollama pull eeve-korean-10.8b
```

사용할 모델을 `config/settings.yaml`의 `llm.model`에 설정하세요.

### 방법 1: Docker (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/ai-autonomous-broadcaster.git
cd ai-autonomous-broadcaster

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 등을 설정하세요

# 3. Docker Compose로 실행 (Ollama 포함)
docker-compose up --build
```

### 방법 2: 수동 설치

```bash
# Python 3.10 이상 필요
python --version

# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 4. 실행
python src/main.py
```

---

## 📖 사용법

### Step 1: 음성 학습

1. 대시보드 실행 후 `http://localhost:7860` 접속
2. **음성 학습** 탭으로 이동
3. WAV/MP3 음성 샘플 파일 업로드 (최소 3개, 각 5~30초)
4. **학습 시작** 버튼 클릭
5. 학습 완료 후 **미리듣기**로 결과 확인

### Step 2: 설정

`config/persona.yaml`을 편집하여 AI 성격을 설정합니다:

```yaml
persona:
  name: "나의 AI 분신"
  personality: "유머러스하고 친근함"
  speaking_style: "반말 위주"
  interests: ["게임", "음악"]
  catchphrase: "이거 레전드 아님?"
```

`config/settings.yaml`에서 플랫폼 및 LLM 설정을 합니다:

```yaml
llm:
  provider: "ollama"
  model: "llama3"
  ollama_url: "http://localhost:11434"

streaming:
  platform: "youtube"
```

### Step 3: 방송 시작

1. OBS Studio 실행 및 가상 오디오 장치 설정
2. 대시보드에서 **방송 시작** 버튼 클릭
3. AI가 자동으로 채팅을 읽고 반응하며 방송 진행

---

## ⚙️ 설정 파일 설명

### `config/settings.yaml`

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `llm.provider` | LLM 제공자 (`ollama`) | `ollama` |
| `llm.model` | 사용할 Ollama 모델 | `llama3` |
| `llm.temperature` | 창의성 수준 (0.0~1.0) | `0.8` |
| `voice.engine` | TTS 엔진 (`xtts_v2`) | `xtts_v2` |
| `broadcast.min_pause_seconds` | 최소 발화 간격 (초) | `1.0` |
| `broadcast.max_pause_seconds` | 최대 발화 간격 (초) | `5.0` |
| `broadcast.memory_window_size` | 유지할 대화 히스토리 수 | `50` |

### `config/persona.yaml`

| 항목 | 설명 |
|------|------|
| `name` | AI 방송인 이름 |
| `personality` | 성격 설명 |
| `speaking_style` | 말투 스타일 |
| `interests` | 관심 분야 목록 |
| `catchphrase` | 자주 쓰는 표현 |
| `mood_default` | 기본 기분 |
| `boundaries` | 하지 말아야 할 것들 |

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.10+ |
| LLM | Ollama 로컬 LLM (llama3, gemma2, qwen2.5 등) |
| 음성 합성 | Coqui XTTS v2 |
| 방송 제어 | OBS WebSocket |
| UI | Gradio |
| 비동기 처리 | asyncio |
| 메모리 | 인메모리 |
| 컨테이너 | Docker + Docker Compose |

---

## 🔑 필요한 API 키

| 키 | 용도 | 획득 방법 |
|----|------|----------|
| `YOUTUBE_API_KEY` | YouTube Live Chat | [Google Cloud Console](https://console.cloud.google.com) |
| `TWITCH_TOKEN` | Twitch IRC | [Twitch Developer](https://dev.twitch.tv) |

> **참고:** Ollama는 로컬에서 실행되므로 API 키가 필요하지 않습니다.

---

## 🧪 테스트 실행

```bash
pytest tests/ -v
```

---

## 📄 라이선스

MIT License

---

## 🤝 기여

이슈 제출, PR 환영합니다!