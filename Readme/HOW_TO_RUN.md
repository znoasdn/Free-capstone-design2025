# 📋 다른 컴퓨터에서 실행하기 - 최종 체크리스트

## ✅ 필수 조건
- [ ] **Ollama 설치 및 모델 다운로드** ⭐ (가장 중요!)
- [ ] Python 3.8 이상 설치됨
- [ ] pip (Python 패키지 관리자) 설치됨
- [ ] 전체 `document_analyzer_refactored_v1` 폴더가 복사됨

---

## 🤖 1단계: Ollama 설치 (필수!) 비기너 가이드에서 한거일거임.

### 📥 Ollama 설치하기

**각 OS별 설치 방법:**

#### Windows:
1. [Ollama 공식 홈페이지](https://ollama.ai)에서 **"Download"** 클릭
2. **"Windows"** 버전 다운로드 (`OllamaSetup.exe`)
3. 설치 프로그램 실행 후 완료
4. **컴퓨터 재시작**

#### macOS:
1. [Ollama 공식 홈페이지](https://ollama.ai)에서 **"Download"** 클릭
2. **"macOS"** 버전 다운로드
3. 응용 프로그램 폴더로 드래그
4. Ollama 앱 실행

#### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 📦 모델 다운로드하기

Ollama 설치 후 터미널에서 다음 명령어 실행:

```bash
# 기본 모델 다운로드 (권장 - 2GB)
ollama pull llama3.2:3b

# 또는 더 빠른 모델 (1.3GB)
ollama pull llama3.2:1b
```

**다운로드 시간:** 인터넷 속도에 따라 1~5분

### ✅ Ollama 설치 확인

터미널에서 다음 명령어 실행:

```bash
ollama list
```

다음과 같이 모델이 표시되면 성공:
```
NAME              ID              SIZE      MODIFIED
llama3.2:3b       xxxxx           2.0GB     2 minutes ago
```

---

## 🐍 2단계: Python 패키지 설치 

### 가상 환경 생성 안해도 됨 무시하셈

#### Windows:
```bash
cd 프로젝트폴더경로
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux:
```bash
cd 프로젝트폴더경로
python3 -m venv venv
source venv/bin/activate
```

### 패키지 설치 이거가 제일 중요하다고 생각하셈

```bash
pip install -r requirements.txt
```

---

## 🚀 3단계: 프로젝트 실행

### 중요! Ollama 서버 먼저 실행

터미널에서:
```bash
ollama serve
```

또는 Ollama 앱을 실행 (백그라운드에서 자동으로 시작됨)

### 프로젝트 실행

#### 자동 실행 (권장):
- **Windows**: `run.bat` 더블클릭
- **macOS/Linux**: `chmod +x run.sh && ./run.sh`

#### 수동 실행:
```bash
python main.py
```

---

## 🎯 3가지 실행 방법

### 방법 1️⃣ : 자동 실행 배치/스크립트 (가장 쉬움)
**Windows:** `run.bat` 더블클릭
**macOS/Linux:** `./run.sh` 실행

### 방법 2️⃣ : 터미널 명령어
```bash
# 1. 프로젝트 폴더로 이동
cd 프로젝트경로

# 2. 가상 환경 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는 venv\Scripts\activate (Windows)

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 프로그램 실행
python main.py
```

### 방법 3️⃣ : IDE 사용 (VS Code, PyCharm 등)
1. 프로젝트 폴더를 IDE에서 엽니다
2. Python 인터프리터를 가상 환경으로 설정합니다
3. `main.py` 파일을 실행합니다

---

## 📚 도움이 되는 가이드 문서

| 파일 | 내용 |
|------|------|
| **OLLAMA_SETUP.md** | 🤖 Ollama 상세 설치 및 설정 가이드 |
| **QUICK_START.md** | ⚡ 빠른 시작 가이드 |
| **SETUP_GUIDE.md** | 📖 Python 및 전체 프로젝트 설정 상세 가이드 |

---

## 💡 핵심 정보

| 항목 | 내용 |
|------|------|
| **Ollama 필수** | 프로젝트 실행 필수 조건 |
| **Ollama 포트** | 11434 (로컬호스트만 허용) |
| **권장 모델** | `llama3.2:3b` (2GB) |
| **빠른 모델** | `llama3.2:1b` (1.3GB) |
| **Python** | 3.8 이상 필요 |
| **필요 패키지** | PyQt5, PyPDF2, python-docx, olefile, requests |

---

## ⚠️ 문제 해결

### "Ollama가 실행되지 않았습니다" 오류
```bash
# Ollama 서버 실행
ollama serve
```

### "모델을 찾을 수 없습니다" 오류
```bash
# 모델 다운로드
ollama pull llama3.2:3b
```

### "Python을 찾을 수 없습니다"
Python 설치 후 컴퓨터를 재시작하세요.

### 더 자세한 정보는 **OLLAMA_SETUP.md**와 **SETUP_GUIDE.md** 참고

---

## 📝 빠른 확인 목록

실행 전 다음을 확인하세요:

- [ ] Ollama 설치됨
- [ ] 모델 다운로드됨 (`ollama list` 확인)
- [ ] Python 3.8+ 설치됨
- [ ] 프로젝트 폴더 복사됨
- [ ] 가상 환경 생성됨
- [ ] Python 패키지 설치됨
- [ ] Ollama 서버 실행 중 (`ollama serve`)

---

## 🎯 한 번에 따라 하기

```
1️⃣ Ollama 설치 + 모델 다운로드
   ↓
2️⃣ Ollama 서버 실행 (ollama serve)
   ↓
3️⃣ Python 패키지 설치 (pip install -r requirements.txt)
   ↓
4️⃣ 프로젝트 실행 (python main.py)
   ↓
5️⃣ GUI 창 나타남 → 완료! 🎉
```

---

**모든 준비가 완료되었습니다! 이제 프로젝트를 실행할 준비가 되었습니다.** ✨
