"""
Ollama 설치 가이드 다이얼로그
"""

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QGroupBox, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
import requests


class OllamaSetupDialog(QDialog):
    """Ollama 설치 가이드 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ollama 설치 가이드")
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        # 창 닫기 시 경고 표시 여부
        self.show_warning_on_close = True
        
        self.init_ui()
        self.check_ollama_status()
        
        # 주기적으로 Ollama 상태 확인
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_ollama_status)
        self.status_timer.start(3000)  # 3초마다 확인
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel("🦙 Ollama 설치 가이드")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2196F3; margin: 10px;")
        layout.addWidget(title_label)
        
        # 상태 표시
        self.status_label = QLabel("🔍 Ollama 상태 확인 중...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 설치 가이드
        guide_group = QGroupBox("📋 설치 단계")
        guide_layout = QVBoxLayout()
        
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setMaximumHeight(200)
        guide_content = """
1. 🌐 Ollama 공식 웹사이트 방문
   • https://ollama.ai 에서 다운로드

2. 💾 설치 파일 다운로드 및 실행
   • Windows용 설치 파일 다운로드
   • 관리자 권한으로 설치 실행

3. 🔧 설치 완료 후 모델 다운로드
   • 터미널에서 다음 명령어 실행:
   • ollama pull llama3.2:3b
   • ollama pull qwen2.5:7b
   • ollama pull phi3.5:3.8b

4. ✅ 설치 확인
   • 이 창에서 자동으로 상태를 확인합니다
        """
        guide_text.setPlainText(guide_content)
        guide_layout.addWidget(guide_text)
        guide_group.setLayout(guide_layout)
        layout.addWidget(guide_group)
        
        # 빠른 액션 버튼들
        action_group = QGroupBox("🚀 빠른 액션")
        action_layout = QVBoxLayout()
        
        # 웹사이트 열기 버튼
        btn_website = QPushButton("🌐 Ollama 웹사이트 열기")
        btn_website.clicked.connect(self.open_website)
        btn_website.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        action_layout.addWidget(btn_website)
        
        # 설치 확인 버튼
        btn_check = QPushButton("🔍 Ollama 설치 상태 확인")
        btn_check.clicked.connect(self.check_ollama_status)
        btn_check.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        action_layout.addWidget(btn_check)
        
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        # 경고 메시지
        warning_group = QGroupBox("⚠️ 중요 안내")
        warning_layout = QVBoxLayout()
        
        warning_label = QLabel("""
• Ollama가 설치되지 않으면 LLM 분석 기능을 사용할 수 없습니다.
• 규칙 기반 분석만 가능하며, 분석 정확도가 제한됩니다.
• 설치 후 이 프로그램을 다시 시작하는 것을 권장합니다.
        """)
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #f44336; font-size: 11px;")
        warning_layout.addWidget(warning_label)
        warning_group.setLayout(warning_layout)
        layout.addWidget(warning_group)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        # 경고 없이 닫기 체크박스
        self.no_warning_checkbox = QCheckBox("다시 묻지 않기")
        button_layout.addWidget(self.no_warning_checkbox)
        
        button_layout.addStretch()
        
        # 나중에 하기 버튼
        btn_later = QPushButton("나중에 설치")
        btn_later.clicked.connect(self.close_with_warning)
        btn_later.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 16px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        button_layout.addWidget(btn_later)
        
        # 완료 버튼
        self.btn_done = QPushButton("설치 완료")
        self.btn_done.clicked.connect(self.accept)
        self.btn_done.setEnabled(False)
        self.btn_done.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.btn_done)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def open_website(self):
        """Ollama 웹사이트 열기"""
        try:
            webbrowser.open("https://ollama.ai")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"웹사이트를 열 수 없습니다:\n{str(e)}")
    
    def check_ollama_status(self):
        """Ollama 설치 상태 확인"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.status_label.setText("✅ Ollama가 정상적으로 설치되어 있습니다!")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #e8f5e8;
                        border: 2px solid #4CAF50;
                        border-radius: 5px;
                        padding: 10px;
                        margin: 5px;
                        color: #2e7d32;
                        font-weight: bold;
                    }
                """)
                self.btn_done.setEnabled(True)
                self.show_warning_on_close = False
            else:
                self.set_not_installed_status()
        except Exception:
            self.set_not_installed_status()
    
    def set_not_installed_status(self):
        """미설치 상태 설정"""
        self.status_label.setText("❌ Ollama가 설치되지 않았거나 실행되지 않고 있습니다.")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ffeaea;
                border: 2px solid #f44336;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
                color: #c62828;
                font-weight: bold;
            }
        """)
        self.btn_done.setEnabled(False)
        self.show_warning_on_close = True
    
    def close_with_warning(self):
        """경고와 함께 닫기"""
        if self.no_warning_checkbox.isChecked():
            self.show_warning_on_close = False
        
        if self.show_warning_on_close:
            reply = QMessageBox.warning(
                self,
                "LLM 분석 불가",
                "Ollama가 설치되지 않아 LLM 분석 기능을 사용할 수 없습니다.\n\n"
                "• 규칙 기반 분석만 가능합니다\n"
                "• 분석 정확도가 제한됩니다\n"
                "• 나중에 '도구 > 설정'에서 다시 설치할 수 있습니다\n\n"
                "정말 계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.reject()
        else:
            self.reject()
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        if self.show_warning_on_close and not self.no_warning_checkbox.isChecked():
            reply = QMessageBox.warning(
                self,
                "LLM 분석 불가",
                "Ollama가 설치되지 않아 LLM 분석 기능을 사용할 수 없습니다.\n\n"
                "정말 닫으시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
