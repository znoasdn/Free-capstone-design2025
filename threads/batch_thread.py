"""
일괄 파일 분석 스레드
"""
import time
from pathlib import Path
from typing import List
from PyQt5.QtCore import QThread, pyqtSignal
from core import DocumentProcessor, LocalLLMAnalyzer
from utils.logger import logger


class BatchAnalysisThread(QThread):
    """일괄 분석 스레드"""
    
    file_progress = pyqtSignal(int, int, str)
    detailed_progress = pyqtSignal(float)  # 세밀한 진행률 (0.0 ~ 100.0)
    file_finished = pyqtSignal(str, dict, list, str, str)  # filename, result, detected, text, file_path
    all_finished = pyqtSignal()
    status_message = pyqtSignal(str)  # 상태 메시지 시그널 추가
    
    def __init__(self, file_paths: List[str], model_name: str):
        super().__init__()
        self.file_paths = file_paths
        self.model_name = model_name
        self._is_cancelled = False
    
    def cancel(self):
        """일괄 분석 취소"""
        self._is_cancelled = True
    
    def run(self):
        """스레드 실행"""
        self.status_message.emit("🚀 일괄 분석 준비 중...")
        time.sleep(0.8)
        
        self.status_message.emit("🔧 일괄 분석 초기화 중...")
        time.sleep(0.5)
        processor = DocumentProcessor()
        analyzer = LocalLLMAnalyzer(self.model_name, status_callback=self._status_callback)
        
        for i, file_path in enumerate(self.file_paths, 1):
            # 취소 확인
            if self._is_cancelled:
                logger.info("일괄 분석이 취소되었습니다.")
                return
            
            try:
                filename = Path(file_path).name
                self.file_progress.emit(i, len(self.file_paths), filename)
                
                # 파일별 세밀한 진행률 계산 (각 파일당 4단계)
                base_progress = ((i - 1) / len(self.file_paths)) * 100
                step_size = (1 / len(self.file_paths)) * 100 / 4  # 4단계로 나누기
                
                # 1단계: 처리 시작
                self.detailed_progress.emit(base_progress + step_size * 0.5)
                self.status_message.emit(f"📄 [{i}/{len(self.file_paths)}] {filename} 처리 시작...")
                time.sleep(0.3)
                
                # 취소 확인
                if self._is_cancelled:
                    return
                
                # 2단계: 텍스트 추출
                self.detailed_progress.emit(base_progress + step_size * 1.5)
                self.status_message.emit(f"📄 [{i}/{len(self.file_paths)}] {filename} - 텍스트 추출 중...")
                time.sleep(0.2)
                text = processor.extract_text(file_path)
                
                # 취소 확인
                if self._is_cancelled:
                    return
                
                # 3단계: 분석 시작
                self.detailed_progress.emit(base_progress + step_size * 2.5)
                self.status_message.emit(f"🔍 [{i}/{len(self.file_paths)}] {filename} - 분석 중...")
                time.sleep(0.2)
                result, detected = analyzer.comprehensive_analysis(text)
                
                # 4단계: 분석 완료
                self.detailed_progress.emit(base_progress + step_size * 4)
                
                # 취소 확인
                if self._is_cancelled:
                    return
                
                # 결과 전송 (텍스트와 파일 경로 포함)
                self.status_message.emit(f"✅ [{i}/{len(self.file_paths)}] {filename} - 분석 완료")
                time.sleep(0.4)
                self.file_finished.emit(filename, result, detected, text, file_path)
                
            except Exception as e:
                logger.error(f"파일 처리 실패 {file_path}: {str(e)}")
                self.status_message.emit(f"❌ [{i}/{len(self.file_paths)}] {filename} - 분석 실패: {str(e)}")
                time.sleep(0.5)
                # 실패한 경우에도 빈 결과 전송 (취소되지 않은 경우만)
                if not self._is_cancelled:
                    self.file_finished.emit(
                        Path(file_path).name, 
                        {"risk_level": "오류", "risk_score": 0, "reasoning": str(e), "recommendations": []},
                        [],
                        "",
                        file_path
                    )
                continue
        
        # 전체 완료 (취소되지 않은 경우만)
        if not self._is_cancelled:
            self.status_message.emit("📊 일괄 분석 결과 정리 중...")
            time.sleep(0.8)
            self.status_message.emit(f"🎉 일괄 분석 완료 - 총 {len(self.file_paths)}개 파일 처리")
            time.sleep(0.5)
            self.all_finished.emit()
    
    def _status_callback(self, message: str):
        """분석기에서 오는 상태 메시지 처리"""
        self.status_message.emit(message)
        time.sleep(0.2)  # 각 상태 메시지마다 딜레이
