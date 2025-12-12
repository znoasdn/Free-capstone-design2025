"""
GUI 대화상자 모듈
"""
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QPushButton,
    QListWidget, QLineEdit, QTextBrowser, QMessageBox
)
from PyQt5.QtCore import Qt
from core import Config, AnalysisHistory, LocalLLMAnalyzer

# Ollama 설치 가이드 다이얼로그 import
from .ollama_setup_dialog import OllamaSetupDialog

# CODEF API 다이얼로그 import
from .codef_dialogs import CodefSettingsDialog, DriverLicenseVerifyDialog

# 사용자 정의 패턴 다이얼로그 import
from .custom_pattern_dialog import CustomPatternDialog


class ExportDialog(QDialog):
    """결과 내보내기 대화상자"""
    
    def __init__(self, parent, analysis_result, detected_items, document_text, filename):
        super().__init__(parent)
        self.analysis_result = analysis_result
        self.detected_items = detected_items
        self.document_text = document_text
        self.filename = filename
        
        self.setWindowTitle("분석 결과 내보내기")
        self.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("내보내기 형식 선택:"))
        
        self.check_json = QCheckBox("JSON 파일")
        self.check_json.setChecked(True)
        layout.addWidget(self.check_json)
        
        self.check_csv = QCheckBox("CSV 파일 (탐지된 항목)")
        layout.addWidget(self.check_csv)
        
        self.check_txt = QCheckBox("텍스트 리포트")
        layout.addWidget(self.check_txt)
        
        self.check_masked = QCheckBox("마스킹된 문서")
        layout.addWidget(self.check_masked)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_selected_formats(self):
        """선택된 형식 반환"""
        formats = []
        if self.check_json.isChecked():
            formats.append('json')
        if self.check_csv.isChecked():
            formats.append('csv')
        if self.check_txt.isChecked():
            formats.append('txt')
        if self.check_masked.isChecked():
            formats.append('masked')
        return formats


class HistoryDialog(QDialog):
    """분석 이력 대화상자"""
    
    def __init__(self, parent, history: AnalysisHistory):
        super().__init__(parent)
        self.history = history
        
        self.setWindowTitle("분석 이력")
        self.setGeometry(150, 150, 800, 600)
        
        layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['시간', '파일명', '위험도', '점수', '탐지수'])
        self.table.horizontalHeader().setStretchLastSection(True)
        
        self.load_history()
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        
        btn_clear = QPushButton("전체 삭제")
        btn_clear.clicked.connect(self.clear_history)
        btn_layout.addWidget(btn_clear)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_history(self):
        """이력 로드"""
        records = self.history.get_recent(50)
        self.table.setRowCount(len(records))
        
        for i, record in enumerate(records):
            timestamp = datetime.fromisoformat(record['timestamp']).strftime('%Y-%m-%d %H:%M')
            self.table.setItem(i, 0, QTableWidgetItem(timestamp))
            self.table.setItem(i, 1, QTableWidgetItem(record['filename']))
            self.table.setItem(i, 2, QTableWidgetItem(record['risk_level']))
            self.table.setItem(i, 3, QTableWidgetItem(str(record['risk_score'])))
            self.table.setItem(i, 4, QTableWidgetItem(str(record['detected_count'])))
    
    def clear_history(self):
        """이력 삭제"""
        reply = QMessageBox.question(self, '확인', '모든 이력을 삭제하시겠습니까?')
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.table.setRowCount(0)
            QMessageBox.information(self, '완료', '이력이 삭제되었습니다.')


class SettingsDialog(QDialog):
    """설정 대화상자"""
    
    def __init__(self, parent, config: Config, analyzer: LocalLLMAnalyzer):
        super().__init__(parent)
        self.config = config
        self.analyzer = analyzer
        
        self.setWindowTitle("설정")
        self.setGeometry(200, 200, 500, 400)
        
        layout = QVBoxLayout()
        
        self.check_dark = QCheckBox("다크 모드")
        self.check_dark.setChecked(config.get_dark_mode())
        layout.addWidget(self.check_dark)
        
        self.check_auto_save = QCheckBox("분석 결과 자동 저장")
        self.check_auto_save.setChecked(config.get_auto_save())
        layout.addWidget(self.check_auto_save)
        
        layout.addWidget(QLabel("\n커스텀 민감정보 패턴:"))
        
        pattern_layout = QHBoxLayout()
        self.input_pattern_name = QLineEdit()
        self.input_pattern_name.setPlaceholderText("패턴 이름")
        pattern_layout.addWidget(self.input_pattern_name)
        
        self.input_pattern_regex = QLineEdit()
        self.input_pattern_regex.setPlaceholderText("정규식 패턴")
        pattern_layout.addWidget(self.input_pattern_regex)
        
        btn_add_pattern = QPushButton("추가")
        btn_add_pattern.clicked.connect(self.add_custom_pattern)
        pattern_layout.addWidget(btn_add_pattern)
        
        layout.addLayout(pattern_layout)
        
        self.pattern_list = QListWidget()
        self.load_custom_patterns()
        layout.addWidget(self.pattern_list)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # Ollama 설치 가이드 버튼
        btn_ollama_guide = QPushButton("🦙 Ollama 설치 가이드")
        btn_ollama_guide.clicked.connect(self.show_ollama_guide)
        btn_ollama_guide.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        button_layout.addWidget(btn_ollama_guide)
        
        # 적용 버튼 (다크모드 즉시 적용)
        btn_apply = QPushButton("적용")
        btn_apply.clicked.connect(self.apply_settings)
        button_layout.addWidget(btn_apply)
        
        # 확인/취소 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_custom_patterns(self):
        """커스텀 패턴 로드"""
        patterns = self.config.get_custom_patterns()
        for name, pattern in patterns.items():
            self.pattern_list.addItem(f"{name}: {pattern}")
    
    def add_custom_pattern(self):
        """커스텀 패턴 추가"""
        name = self.input_pattern_name.text().strip()
        pattern = self.input_pattern_regex.text().strip()
        
        if not name or not pattern:
            QMessageBox.warning(self, '경고', '이름과 패턴을 모두 입력하세요.')
            return
        
        if self.analyzer.add_custom_pattern(name, pattern):
            self.pattern_list.addItem(f"{name}: {pattern}")
            self.input_pattern_name.clear()
            self.input_pattern_regex.clear()
            QMessageBox.information(self, '성공', '패턴이 추가되었습니다.')
        else:
            QMessageBox.warning(self, '오류', '유효하지 않은 정규식 패턴입니다.')
    
    def apply_settings(self):
        """설정 즉시 적용 (저장하지 않고 미리보기)"""
        # 다크모드 설정 저장 및 즉시 적용
        dark_mode_changed = self.config.get_dark_mode() != self.check_dark.isChecked()
        
        self.config.set_dark_mode(self.check_dark.isChecked())
        self.config.set_auto_save(self.check_auto_save.isChecked())
        
        # 부모 윈도우의 테마 적용
        if dark_mode_changed and self.parent():
            self.parent().apply_theme()
            QMessageBox.information(self, '적용', '설정이 적용되었습니다.')
    
    def save_settings(self):
        """설정 저장 및 닫기"""
        self.config.set_dark_mode(self.check_dark.isChecked())
        self.config.set_auto_save(self.check_auto_save.isChecked())
        
        patterns = {}
        for i in range(self.pattern_list.count()):
            item_text = self.pattern_list.item(i).text()
            if ': ' in item_text:
                name, pattern = item_text.split(': ', 1)
                patterns[name] = pattern
        
        self.config.set_custom_patterns(patterns)
        
        # 부모 윈도우의 테마 적용
        if self.parent():
            self.parent().apply_theme()
        
        self.accept()
    
    def show_ollama_guide(self):
        """Ollama 설치 가이드 표시"""
        dialog = OllamaSetupDialog(self)
        dialog.exec()


class AboutDialog(QDialog):
    """정보 대화상자"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("정보")
        self.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout()
        
        browser = QTextBrowser()
        browser.setHtml("""
<h2>📄 문서 위험도 분석 시스템</h2>
<p><b>버전:</b> 2.0 (리팩토링 버전)</p>

<h3>주요 기능:</h3>
<ul>
<li>✅ 다양한 문서 형식 지원 (PDF, DOCX, TXT, HWP, HWPX)</li>
<li>✅ 드래그 앤 드롭으로 파일 추가</li>
<li>✅ Local LLM 기반 지능형 분석</li>
<li>✅ 정규식 + AI 하이브리드 탐지</li>
<li>✅ 개선된 보안 권고사항 생성 엔진</li>
<li>✅ 민감정보 자동 마스킹</li>
<li>✅ 일괄 분석 기능</li>
<li>✅ 분석 이력 관리</li>
<li>✅ 다양한 형식 내보내기 (JSON, CSV, TXT)</li>
<li>✅ 통계 대시보드</li>
<li>✅ 커스텀 패턴 추가</li>
<li>✅ 다크모드 지원</li>
</ul>

<h3>기술 스택:</h3>
<ul>
<li>Python 3.8+</li>
<li>PyQt5 (GUI)</li>
<li>Ollama (Local LLM)</li>
<li>모듈화된 아키텍처</li>
</ul>

<p><b>개발:</b> AI 기반 문서 보안 솔루션</p>
<p><b>라이선스:</b> MIT</p>
        """)
        layout.addWidget(browser)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
        self.setLayout(layout)
