# 🎯 완전 초보자 가이드 - 단 5분 안에 시작하기!

이 문서는 프로그래밍을 처음 하는 사람도 따라 할 수 있도록 작성되었습니다.

---

## ⚠️ 매우 중요: 순서대로 하기!

**이 순서를 반드시 지키세요:**

```
1️⃣ Ollama 설치
   ↓
2️⃣ 모델 다운로드
   ↓
3️⃣ Python 설치
   ↓
4️⃣ 프로젝트 실행
```

---

## 🤖 Step 1: Ollama 설치 (가장 중요!)

Ollama는 AI 모델을 실행하는 프로그램입니다. 이것 없이는 프로젝트가 작동하지 않습니다.

### Windows 사용자

**1) 브라우저에서 https://ollama.ai 접속**

**2) 화면에 보이는 "Download" 버튼 클릭**

**3) "Windows" 버전 클릭** (`OllamaSetup.exe`)

**4) 다운로드된 파일 실행**
- 파일 탐색기에서 `OllamaSetup.exe` 찾기
- 더블클릭해서 실행
- 화면에 나오는 대로 진행하기

**5) 컴퓨터 재시작**

---

### macOS 사용자

**1) https://ollama.ai 접속**

**2) "Download" → "macOS" 클릭**

**3) 다운로드된 파일 실행**
- 다운로드 폴더에서 `Ollama-darwin.zip` 찾기
- 더블클릭해서 압축 해제
- 나타난 Ollama 앱을 응용 프로그램 폴더로 드래그

**4) 응용 프로그램 폴더에서 Ollama 앱 실행**

---

### Linux 사용자

**터미널에서 이 명령어 복사 후 붙여넣기:**

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

엔터 누르고 완료될 때까지 기다리기

---

## 📦 Step 2: 모델 다운로드 (AI 두뇌)

모델은 AI의 "두뇌" 같은 것입니다. 반드시 설치해야 합니다.

### 모든 OS (동일)

**1) 터미널 또는 명령 프롬프트 열기**

- **Windows**: 시작 메뉴에서 "명령 프롬프트" 또는 "PowerShell" 검색 후 클릭
- **macOS/Linux**: Spotlight에서 "터미널" 검색 후 클릭

**2) 다음 명령어 복사해서 붙여넣기: 혹은 원하는 모델만 따로 불러오기** 

```bash
ollama pull llama3.2:3b
ollama pull gemma3:4b
```


**3) 엔터 누르기**

**4) 기다리기** (약 2~3분 소요)
- 진행 상황이 보일 것입니다
- "success" 메시지가 나타날 때까지 기다리기
- **인터넷이 끊기면 안됩니다!**

**완료 확인:**

```bash
ollama list
```

`llama3.2:3b`가 보이면 성공!

---

## 🐍 Step 3: Python 설치 (프로그래밍 언어)

Python은 이 프로젝트의 기반이 되는 프로그래밍 언어입니다.

## 나는 3.11.9씀

### Windows 사용자

**1) https://www.python.org/downloads 접속**


**2) 노란색 "Download Python" 버튼 클릭**

**3) 다운로드된 파일 실행**
- `python-3.x.x.exe` 찾기
- 더블클릭

**4) ⭐ 중요: 체크박스 선택**
```
☑️ Add Python to PATH
```
이 체크박스를 반드시 체크해야 합니다!

**5) "Install Now" 클릭**

**6) 설치 완료 후 컴퓨터 재시작**

**설치 확인:**

명령 프롬프트 열고:
```bash
python --version
```

버전이 보이면 성공! (예: Python 3.11.0)

---

### macOS 사용자

**1) 터미널에서 Homebrew 설치** (처음만)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2) Python 설치**

```bash
brew install python@3.11
```

**3) 설치 확인**

```bash
python3 --version
```

---

### Linux 사용자

**Ubuntu/Debian:**
```bash
sudo apt-get install python3 python3-pip
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip
```

---

## 📁 Step 4: 프로젝트 폴더 준비

**1) 프로젝트 폴더를 편한 위치에 복사**

- 예: `C:\Users\YourName\Desktop` (Windows)
- 예: `~/Desktop` (macOS/Linux)

**2) 폴더 경로 기억하기**

Windows 예시: `C:\Users\YourName\Desktop\document_analyzer_refactored_v2`

---

## 🚀 Step 5: 프로젝트 실행

### Windows 사용자 (가장 쉬운 방법)

**1) Ollama 앱 실행**
- 시작 메뉴에서 "Ollama" 검색
- Ollama 앱 실행
- 작업표시줄에서 Ollama 아이콘 확인

**2) 프로젝트 폴더 열기**
- 파일 탐색기에서 프로젝트 폴더 찾기
- 폴더 열기

**3) `run.bat` 파일 찾기**
- 폴더에 `run.bat`이라는 파일 보임
- 더블클릭으로 실행

**4) 기다리기**
- 터미널 창 나타남
- 자동으로 설정 진행
- 처음 실행 시 1~2분 소요

**5) GUI 창 나타남** → 완료! 🎉

---

### macOS/Linux 사용자

**1) 터미널 2개 열기** (중요!)

**터미널 1: Ollama 서버 실행**

```bash
ollama serve
```

**터미널 2: 프로젝트 실행**

**2) 프로젝트 폴더로 이동**

```bash
cd ~/Desktop/document_analyzer_refactored_v2
```

(경로는 자신의 폴더 경로로 변경)

**3) 다음 명령어 실행**

```bash
chmod +x run.sh
./run.sh
```

**4) 자동 설정** (1~2분)

**5) GUI 창 나타남** → 완료! 🎉

---

## ⚠️ 문제가 생겼다면?

### "Ollama를 찾을 수 없습니다"
→ Ollama를 설치하지 않았습니다. Step 1을 다시 진행하세요.

### "모델 없음" 에러
→ 모델을 다운로드하지 않았습니다. Step 2를 다시 진행하세요.

### "Python을 찾을 수 없습니다"
→ Python을 설치하지 않았습니다. Step 3을 다시 진행하세요.

### 프로그램이 시작되지 않음
→ Ollama 서버가 실행 중인지 확인하세요. (Step 5의 첫 번째 단계)

---

## 📚 더 알고 싶다면?

- **OLLAMA_SETUP.md** - Ollama 상세 정보
- **SETUP_GUIDE.md** - 전체 설정 상세 가이드
- **QUICK_START.md** - 빠른 시작
- **HOW_TO_RUN.md** - 최종 체크리스트

---

## 💡 꼭 기억하기!

1. **Ollama는 필수** - 없으면 작동 불가
2. **순서 중요** - 1 → 2 → 3 → 4 → 5 순서로!
3. **Ollama 서버는 항상 켜두기** - 프로그램 실행 중에는 Ollama가 실행되어야 함
4. **인터넷 연결 필수** - 모델 다운로드와 Ollama 실행 시 필요

---

## ✅ 최종 확인 목록

실행 전 모두 확인했는지 체크하세요:

- [ ] Ollama 설치됨 (`ollama list` 명령어로 확인)
- [ ] 모델 다운로드됨 (`llama3.2:3b` 보임)
- [ ] Python 설치됨 (`python --version` 또는 `python3 --version` 실행)
- [ ] 프로젝트 폴더 준비됨
- [ ] Ollama 서버 실행 중

모두 확인되면 **프로젝트 실행**으로 진행하세요!

---

**축하합니다! 이제 준비가 완료되었습니다!** 🎉

문제가 생기면 다른 가이드 문서를 참고하세요.
