# ⚡ 빠른 시작 가이드 (Quick Start)

## 🤖 Step 0: Ollama 설치 (필수!)

### Windows:
1. https://ollama.ai 에서 Windows 버전 다운로드
2. `OllamaSetup.exe` 실행
3. 컴퓨터 재시작

### macOS:
1. https://ollama.ai 에서 macOS 버전 다운로드
2. 응용 프로그램 폴더로 드래그
3. Ollama 앱 실행

### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 모델 다운로드:
```bash
ollama pull llama3.2:3b
```

---

## 📌 가장 간단한 방법 (추천)

### Windows 사용자
1. **Ollama 서버 실행**: Ollama 앱 클릭 (또는 `ollama serve` 명령어)
2. **프로젝트 실행**: 프로젝트 폴더에서 **`run.bat`** 파일 더블클릭
3. 자동으로 모든 설정이 진행됩니다!

### macOS/Linux 사용자
1. **Ollama 서버 실행**:
```bash
ollama serve
```

2. **프로젝트 실행** (새로운 터미널 창에서):
```bash
cd 프로젝트폴더
chmod +x run.sh
./run.sh
```

---

## 🎯 수동 설정 방법

### 1단계: Ollama 확인
```bash
ollama list
```
모델이 표시되면 OK!

### 2단계: Ollama 서버 실행
```bash
ollama serve
```

### 3단계: 새로운 터미널 창 열기 (중요!)
프로젝트 폴더로 이동:
```bash
cd 프로젝트_폴더_경로
```

### 4단계: 가상 환경 생성 및 활성화

#### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

**확인:** 터미널 앞에 `(venv)`가 나타나야 함

### 5단계: 패키지 설치
```bash
pip install -r requirements.txt
```

### 6단계: 프로그램 실행
```bash
python main.py
```

---

## ❌ 문제 발생 시

| 문제 | 해결책 |
|------|-------|
| `ollama: command not found` | Ollama를 설치하세요 |
| `모델을 찾을 수 없습니다` | `ollama pull llama3.2:3b` 실행 |
| `Ollama가 실행되지 않았습니다` | Ollama 서버 실행: `ollama serve` |
| `python: command not found` | Python이 설치되지 않았거나 PATH에 없음 |
| `ModuleNotFoundError` | `pip install -r requirements.txt` 재실행 |
| PyQt5 오류 | `pip install PyQt5 --upgrade` |

---

## 📦 포함된 패키지

- **Ollama** - 로컬 LLM 실행 프레임워크
PyQt5>=5.15.0
PyPDF2>=3.0.0
python-docx>=0.8.11
pyhwp>=0.1b12
six>=1.10.0
requests>=2.28.0
reportlab>=3.6.0
pyinstaller>=5.0.0
chardet>=5.0.0
pymupdf>=1.23.0

---

## 📚 필요한 가이드 문서

- **OLLAMA_SETUP.md** - Ollama 상세 설정
- **SETUP_GUIDE.md** - 전체 설정 가이드


## 🚀 실행 후 확인 사항

✅ GUI 창이 정상 표시됨  
✅ 파일을 드래그 앤 드롭할 수 있음  
✅ 분석 결과가 표시됨  
✅ Ollama와 연결됨 (상태 표시 확인)

---

## 💡 핵심 정보

**Ollama는 필수입니다!**
- 프로젝트는 Ollama와 LLM 모델을 반드시 필요로 합니다
- Ollama 없이는 실행할 수 없습니다
- 모델 다운로드 후 Ollama 서버를 항상 켜두어야 합니다

---

**준비되셨나요? 이제 시작할 준비가 되었습니다!** ✨
