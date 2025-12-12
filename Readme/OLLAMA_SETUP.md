# 🤖 Ollama 설치 및 설정 가이드

이 프로젝트는 **Ollama**라는 로컬 LLM(대형언어모델) 실행 프레임워크를 사용합니다.  
다른 컴퓨터에서 이 프로젝트를 실행하려면 Ollama를 먼저 설치하고 모델을 다운로드해야 합니다.

---

## 📋 필요한 것

- **메모리**: 최소 8GB RAM (권장 16GB 이상)
- **디스크 공간**: 모델에 따라 3GB ~ 10GB
- **인터넷**: 모델 다운로드 시 필요
- **OS**: Windows, macOS, Linux 모두 지원

---

## 🚀 Ollama 설치 방법

### 1️⃣ Windows 설치

#### 방법 A: 공식 설치 프로그램 (권장)

1. [Ollama 공식 홈페이지](https://ollama.ai)에서 **"Download"** 클릭
2. **"Windows"** 버전 다운로드 (`OllamaSetup.exe`)
3. 설치 파일 실행 후 화면에 따라 진행
4. 설치 완료 후 **컴퓨터 재시작**

#### 설치 확인

```bash
ollama --version
```

---

### 2️⃣ macOS 설치

#### 공식 설치 프로그램

1. [Ollama 공식 홈페이지](https://ollama.ai)에서 **"Download"** 클릭
2. **"macOS"** 버전 다운로드 (`Ollama-darwin.zip`)
3. 다운로드한 파일을 **응용 프로그램** 폴더로 드래그
4. **응용 프로그램** 폴더에서 **Ollama** 앱 실행

#### 터미널에서 설치 (Homebrew 사용)

```bash
brew install ollama
```

#### 설치 확인

```bash
ollama --version
```

---

### 3️⃣ Linux 설치

#### Ubuntu/Debian

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Fedora/RedHat

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### 설치 확인

```bash
ollama --version
```

---

## 🎯 Ollama 시작하기

### 1단계: Ollama 서버 실행

Ollama는 백그라운드에서 서버로 실행되어야 합니다.

#### Windows:
- 시작 메뉴에서 **Ollama** 검색 후 실행
- 또는 설치 시 자동으로 시작되도록 설정됨
- 작업표시줄의 Ollama 아이콘 확인

#### macOS:
- Finder에서 **응용 프로그램 > Ollama** 실행
- 또는 터미널: `ollama serve`

#### Linux:
```bash
ollama serve
```

**실행 확인:**
```bash
curl http://localhost:11434/api/tags
```

또는 브라우저에서 접속:
```
http://localhost:11434/api/tags
```

---

## 📦 모델 다운로드

Ollama는 다양한 모델을 지원합니다. 프로젝트에서 사용 가능한 모델들을 소개합니다.

### 추천 모델 (용도별)

| 모델명 | 크기 | 성능 | 추천 상황 | 다운로드 시간 |
|-------|------|------|---------|------------|
| **llama3.2:1b** | 1.3GB | 빠름 | 빠른 응답 필요 | 1분 |
| **llama3.2:3b** | 2.0GB | 중간 | 평균 성능 (기본값) | 2분 |
| **gemma2:2b** | 1.6GB | 빠름 | 경량 모델 선호 | 2분 |
| **phi3:mini** | 1.3GB | 빠름 | 매우 빠른 응답 | 1분 |
| **mistral:7b** | 4.1GB | 우수 | 고성능 필요 | 5분 |

### 모델 다운로드 명령어

#### 기본 모델 다운로드 (llama3.2:3b - 권장)

```bash
ollama pull llama3.2:3b
```

#### 다른 모델 다운로드

```bash
# 빠른 모델
ollama pull llama3.2:1b

# 경량 모델
ollama pull gemma2:2b

# 성능 좋은 모델
ollama pull mistral:7b
```

#### 모델 다운로드 상태 확인

```bash
ollama list
```

---

## ✅ 설치 완료 확인

### 1단계: Ollama 서버 확인

```bash
curl http://localhost:11434/api/tags
```

**성공 응답 예시:**
```json
{
  "models": [
    {
      "name": "llama3.2:3b",
      "modified_at": "2024-01-15T10:30:00Z",
      "size": 2000000000
    }
  ]
}
```

### 2단계: 모델 테스트 실행

```bash
ollama run llama3.2:3b "안녕하세요"
```

**성공 응답:** AI 모델이 한국어로 응답함

### 3단계: 프로젝트에서 테스트

프로젝트를 실행하고, GUI에서 **"Ollama 연결 확인"** 또는 **"설정"** 메뉴 확인

---

## 🛠️ 트러블슈팅

### 문제 1: "Ollama를 찾을 수 없습니다"

**해결책:**
```bash
# Ollama 서버가 실행 중인지 확인
# Windows: 작업표시줄의 Ollama 아이콘 확인
# macOS/Linux: ollama serve 실행 중인지 확인

# 수동으로 시작
ollama serve
```

### 문제 2: "모델을 다운로드할 수 없습니다" (네트워크 오류)

**해결책:**
1. 인터넷 연결 확인
2. 방화벽 설정 확인 (Ollama 포트 11434 허용)
3. 다시 시도:
```bash
ollama pull llama3.2:3b
```

### 문제 3: "메모리 부족" 오류

**해결책:**
- 더 작은 모델 사용: `ollama pull llama3.2:1b`
- 다른 프로그램 종료
- 다운로드한 모델 확인 후 불필요한 모델 삭제:
```bash
ollama rm 모델이름
```

### 문제 4: 프로젝트에서 "Ollama가 실행되지 않았습니다" 오류

**해결책:**
1. Ollama 서버 실행 확인: `ollama serve` 명령어 실행
2. 포트 11434가 사용 중인지 확인
3. 방화벽에서 로컬호스트(localhost) 접근 허용 확인

### 문제 5: 응답이 매우 느립니다

**해결책:**
1. 더 작은 모델로 변경 (1b 또는 2b 모델)
2. GPU 활성화 확인 (NVIDIA/AMD GPU 있는 경우)
3. 컴퓨터의 다른 프로그램 종료 (메모리 확보)

---

## ⚙️ 고급 설정

### GPU 가속 활성화 (선택사항)

NVIDIA GPU가 있는 경우 CUDA를 통해 가속할 수 있습니다.

#### Windows (NVIDIA GPU)

1. [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) 설치
2. Ollama 재설치
3. GPU가 자동으로 사용됨

#### macOS (Apple Silicon)

M1/M2/M3 맥은 자동으로 GPU 가속 사용

---

## 📝 프로젝트 설정 파일

프로젝트의 `utils/constants.py` 파일에서 다음을 확인할 수 있습니다:

```python
# Ollama 설정
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_TIMEOUT = 120

# 사용 가능한 모델 목록
AVAILABLE_MODELS = [
    "llama3.2:3b",      # 기본값 (권장)
    "llama3.2:1b",      # 빠름
    "gemma2:2b",        # 경량
    "phi3:mini",        # 매우 빠름
    "mistral:7b"        # 고성능
]
```

### 모델 변경 방법

프로젝트 실행 시 GUI에서 모델을 선택할 수 있습니다.

---

## 📊 모델 크기 및 시간 안내

### 다운로드 시간 (일반적인 인터넷 속도 기준)

| 모델 | 크기 | 100Mbps | 50Mbps | 10Mbps |
|------|------|---------|--------|--------|
| llama3.2:1b | 1.3GB | 1-2분 | 2-3분 | 10분 |
| llama3.2:3b | 2.0GB | 2-3분 | 3-5분 | 15분 |
| gemma2:2b | 1.6GB | 2분 | 3분 | 12분 |
| mistral:7b | 4.1GB | 4-5분 | 6-8분 | 30분 |

### 실행 시간 (응답 생성 시간)

| 모델 | CPU | GPU (NVIDIA) |
|------|-----|-------------|
| llama3.2:1b | 2-5초 | 1-2초 |
| llama3.2:3b | 5-10초 | 2-4초 |
| gemma2:2b | 3-8초 | 1-3초 |
| mistral:7b | 15-30초 | 4-10초 |

---

## 🌐 로컬호스트 포트 정보

Ollama는 다음 포트를 사용합니다:

- **포트 11434**: Ollama API 서버
- 방화벽 설정: 로컬호스트 접근만 허용 (원격 접근 불허)

---

## 📞 추가 정보

- **Ollama 공식 문서**: https://github.com/jmorganca/ollama
- **모델 라이브러리**: https://ollama.ai/library
- **커뮤니티 포럼**: https://github.com/jmorganca/ollama/discussions

---

## ✨ 빠른 확인 목록

- [ ] Ollama 설치됨
- [ ] Ollama 서버 실행 중 (`ollama serve`)
- [ ] 모델 다운로드됨 (`ollama pull llama3.2:3b`)
- [ ] `ollama list` 명령어로 모델 확인
- [ ] 프로젝트 Python 패키지 설치됨
- [ ] 프로젝트 시작 (`python main.py`)

---

**모든 준비가 완료되었습니다! 이제 프로젝트를 실행할 준비가 되었습니다.** 🚀
