"""
단일 파일 분석 스레드
"""
import time
from PyQt5.QtCore import QThread, pyqtSignal
from core import DocumentProcessor, LocalLLMAnalyzer


class AnalysisThread(QThread):
    """분석 스레드 (취소 가능)"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict, list, str)
    error = pyqtSignal(str)
    status_message = pyqtSignal(str)  # 상태 메시지 시그널 추가
    
    def __init__(self, file_path: str, model_name: str):
        super().__init__()
        self.file_path = file_path
        self.model_name = model_name
        self._is_cancelled = False
    
    def cancel(self):
        """분석 취소"""
        self._is_cancelled = True
    
    def run(self):
        """스레드 실행"""
        try:
            if self._is_cancelled:
                return
            
            # 시작
            self.status_message.emit("🚀 분석 준비 중...")
            self.progress.emit(5)
            time.sleep(0.8)  # 사용자가 볼 수 있도록 딜레이
            
            if self._is_cancelled:
                return
            
            # 텍스트 추출
            self.status_message.emit("📄 문서에서 텍스트 추출 중...")
            self.progress.emit(15)
            time.sleep(0.5)
            processor = DocumentProcessor()
            text = processor.extract_text(self.file_path)
            self.progress.emit(25)
            time.sleep(0.5)
            
            if self._is_cancelled:
                return
            
            # 분석기 초기화
            self.status_message.emit("🔧 분석기 초기화 중...")
            self.progress.emit(35)
            time.sleep(0.5)
            analyzer = LocalLLMAnalyzer(self.model_name, status_callback=self._status_callback)
            self.progress.emit(45)
            time.sleep(0.3)
            
            # Ollama 연결 확인
            self.status_message.emit("🔗 Ollama 서버 연결 확인 중...")
            self.progress.emit(50)
            time.sleep(0.5)
            connected, msg = analyzer.check_ollama_connection()
            if not connected:
                self.status_message.emit("❌ Ollama 연결 실패")
                self.error.emit(f"Ollama 연결 실패: {msg}")
                return
            
            if self._is_cancelled:
                return
            
            # 분석 실행
            self.status_message.emit("🔍 규칙 기반 분석 시작...")
            self.progress.emit(60)
            time.sleep(0.5)
            analysis_result, detected_items = analyzer.comprehensive_analysis(text)
            
            if self._is_cancelled:
                return
            
            # 분석 완료 후 진행률을 서서히 100%까지 증가
            self.status_message.emit("📊 분석 결과 정리 중...")
            for i in range(85, 96, 2):
                if self._is_cancelled:
                    return
                self.progress.emit(i)
                time.sleep(0.2)
            
            self.status_message.emit("✅ 분석 완료")
            for i in range(96, 101):
                if self._is_cancelled:
                    return
                self.progress.emit(i)
                time.sleep(0.1)
            
            time.sleep(0.5)  # 완료 메시지를 볼 수 있도록
            self.finished.emit(analysis_result, detected_items, text)
            
        except Exception as e:
            if not self._is_cancelled:
                self.status_message.emit("❌ 분석 중 오류 발생")
                self.error.emit(f"분석 오류: {str(e)}")
    
    def _status_callback(self, message: str):
        """분석기에서 오는 상태 메시지 처리"""
        self.status_message.emit(message)
        time.sleep(0.3)  # 각 상태 메시지마다 딜레이
