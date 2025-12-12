"""
메인 GUI 윈도우 (완전한 버전)
"""
import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QFileDialog, QProgressBar, QComboBox,
    QGroupBox, QAction, QMessageBox, QApplication, QTabWidget,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QListWidget, QCheckBox, QListWidgetItem, QMenu, QInputDialog
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QTextCursor, QDragEnterEvent, QDropEvent
import requests

from core import Config, AnalysisHistory, LocalLLMAnalyzer
from threads import AnalysisThread, BatchAnalysisThread
from gui.widgets import DropLabel
from gui.dialogs import ExportDialog, HistoryDialog, SettingsDialog, AboutDialog, OllamaSetupDialog, CodefSettingsDialog, DriverLicenseVerifyDialog
# CustomPatternDialog는 함수 내부에서 지연 로딩
from utils.constants import AVAILABLE_MODELS, SUPPORTED_EXTENSIONS, RISK_COLORS, HIGHLIGHT_COLORS
from utils.logger import logger


class DocumentAnalyzerGUI(QMainWindow):
    """메인 GUI (완전한 버전)"""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.history = AnalysisHistory()
        self.current_file = None
        self.analysis_result = None
        self.detected_items = []
        self.document_text = ""
        self.analysis_thread = None
        self.batch_files = []
        self.batch_results = {}  # {filename: {result, detected, text, file_path}}
        self.batch_thread = None
        
        self.setAcceptDrops(True)
        
        self.init_ui()
        self.apply_theme()
        self.check_ollama_status()
        
        # Ollama 상태 체크 타이머
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_ollama_status)
        self.check_timer.start(10000)
        
        # 애플리케이션 시작 시 Ollama 설치 확인
        QTimer.singleShot(1000, self.check_initial_ollama_setup)
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("📄 문서 위험도 분석 시스템 v2.0 (리팩토링)")
        self.setGeometry(50, 50, 1600, 900)
        
        self.create_menu_bar()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 드래그 앤 드롭 영역
        self.drop_area = DropLabel(
            "📁 여기에 파일을 드래그 앤 드롭하세요\n(PDF, DOCX, TXT, HWP, HWPX)"
        )
        self.drop_area.setMinimumHeight(80)
        self.drop_area.files_dropped.connect(self.on_files_dropped)
        main_layout.addWidget(self.drop_area)
        
        # 제어 패널
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 상태 메시지 표시
        self.status_message_label = QLabel("준비")
        self.status_message_label.setVisible(False)
        self.status_message_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
        """)
        main_layout.addWidget(self.status_message_label)
        
        # 탭 위젯
        self.tabs = QTabWidget()
        
        # 단일 분석 탭
        tab_single = self.create_single_analysis_tab()
        self.tabs.addTab(tab_single, "📄 단일 분석")
        
        # 일괄 분석 탭
        tab_batch = self.create_batch_analysis_tab()
        self.tabs.addTab(tab_batch, "📚 일괄 분석")
        
        # 통계 탭
        tab_stats = self.create_statistics_tab()
        self.tabs.addTab(tab_stats, "📊 통계")
        
        # 최근 분석 기록 탭
        tab_history = self.create_recent_history_tab()
        self.tabs.addTab(tab_history, "📜 최근 분석 기록")
        
        main_layout.addWidget(self.tabs)
        
        # 상태바
        self.status_label = QLabel("준비")
        self.ollama_status = QLabel("Ollama: 확인 중...")
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.ollama_status)
    
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일')
        
        action_open = QAction('📁 문서 열기', self)
        action_open.setShortcut('Ctrl+O')
        action_open.triggered.connect(self.select_file)
        file_menu.addAction(action_open)
        
        action_batch = QAction('📚 일괄 분석', self)
        action_batch.setShortcut('Ctrl+B')
        action_batch.triggered.connect(self.select_multiple_files)
        file_menu.addAction(action_batch)
        
        file_menu.addSeparator()
        
        action_exit = QAction('❌ 종료', self)
        action_exit.setShortcut('Ctrl+Q')
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu('도구')
        
        action_patterns = QAction('📝 사용자 정의 패턴', self)
        action_patterns.triggered.connect(self.show_custom_patterns)
        tools_menu.addAction(action_patterns)
        
        tools_menu.addSeparator()
        
        action_codef = QAction('🔐 CODEF API 설정', self)
        action_codef.triggered.connect(self.show_codef_settings)
        tools_menu.addAction(action_codef)
        
        tools_menu.addSeparator()
        
        action_settings = QAction('⚙️ 설정', self)
        action_settings.triggered.connect(self.show_settings)
        tools_menu.addAction(action_settings)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu('도움말')
        
        action_about = QAction('ℹ️ 정보', self)
        action_about.triggered.connect(self.show_about)
        help_menu.addAction(action_about)
    
    def create_control_panel(self) -> QGroupBox:
        """제어 패널"""
        group = QGroupBox("제어 패널")
        layout = QHBoxLayout()
        
        self.btn_select_file = QPushButton("📁 문서 선택")
        self.btn_select_file.clicked.connect(self.select_file)
        layout.addWidget(self.btn_select_file)
        
        self.label_filename = QLabel("선택된 파일 없음")
        self.label_filename.setStyleSheet("color: gray;")
        layout.addWidget(self.label_filename, 1)
        
        layout.addWidget(QLabel("모델:"))
        self.combo_model = QComboBox()
        
        # 모델명과 설명을 함께 표시
        for model_name, description in AVAILABLE_MODELS.items():
            display_text = f"{model_name} - {description}"
            self.combo_model.addItem(display_text, model_name)  # 실제 모델명은 데이터로 저장
        
        # 마지막 사용 모델 설정
        last_model = self.config.get_last_model()
        for i in range(self.combo_model.count()):
            if self.combo_model.itemData(i) == last_model:
                self.combo_model.setCurrentIndex(i)
                break
        else:
            # 마지막 모델이 없으면 첫 번째 모델 선택
            self.combo_model.setCurrentIndex(0)
        
        layout.addWidget(self.combo_model)
        
        self.btn_analyze = QPushButton("🔍 분석 시작")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self.start_analysis)
        if self.config.get_dark_mode():
            self.btn_analyze.setStyleSheet("""
                QPushButton {
                    background-color: #2e7d32;
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border: 1px solid #1b5e20;
                }
                QPushButton:disabled {
                    background-color: #2a2a2a;
                    color: #666;
                    border: 1px solid #444;
                }
                QPushButton:hover:enabled {
                    background-color: #388e3c;
                    border: 1px solid #2e7d32;
                }
            """)
        else:
            self.btn_analyze.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: #000000;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666;
                }
                QPushButton:hover:enabled {
                    background-color: #45a049;
                    color: #000000;
                }
            """)
        layout.addWidget(self.btn_analyze)
        
        self.btn_cancel = QPushButton("⛔ 취소")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_analysis)
        if self.config.get_dark_mode():
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: #c62828;
                    color: white;
                    padding: 8px 16px;
                    border: 1px solid #8e0000;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                    border: 1px solid #c62828;
                }
            """)
        else:
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        layout.addWidget(self.btn_cancel)
        
        self.btn_reset = QPushButton("🔄 초기화")
        self.btn_reset.clicked.connect(self.reset_analysis)
        layout.addWidget(self.btn_reset)
        
        group.setLayout(layout)
        return group
    
    def create_single_analysis_tab(self) -> QWidget:
        """단일 분석 탭"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # 왼쪽: 문서 내용
        left_group = QGroupBox("문서 내용")
        left_layout = QVBoxLayout()
        
        self.text_document = QTextEdit()
        self.text_document.setReadOnly(True)
        self.text_document.setFont(QFont("Consolas", 10))
        # 커스텀 컨텍스트 메뉴 활성화
        self.text_document.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_document.customContextMenuRequested.connect(self.show_document_context_menu)
        left_layout.addWidget(self.text_document)
        
        left_group.setLayout(left_layout)
        layout.addWidget(left_group, 3)
        
        # 오른쪽: 분석 결과
        right_group = QGroupBox("분석 결과")
        right_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.result_layout = QVBoxLayout(scroll_widget)
        
        # 위험도 프레임
        self.risk_frame = QFrame()
        self.risk_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        risk_layout = QVBoxLayout(self.risk_frame)
        
        self.label_risk_level = QLabel("위험도: -")
        self.label_risk_level.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        risk_layout.addWidget(self.label_risk_level)
        
        self.label_risk_score = QLabel("점수: -")
        self.label_risk_score.setFont(QFont("Arial", 12))
        risk_layout.addWidget(self.label_risk_score)
        
        self.result_layout.addWidget(self.risk_frame)
        
        # 탐지된 민감정보
        self.label_detected_title = QLabel("🔍 탐지된 민감정보")
        self.label_detected_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.result_layout.addWidget(self.label_detected_title)
        
        self.text_detected = QTextEdit()
        self.text_detected.setReadOnly(True)
        self.text_detected.setMaximumHeight(200)
        self.result_layout.addWidget(self.text_detected)
        
        # 판단 근거
        self.label_reasoning_title = QLabel("📊 판단 근거")
        self.label_reasoning_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.result_layout.addWidget(self.label_reasoning_title)
        
        self.text_reasoning = QTextEdit()
        self.text_reasoning.setReadOnly(True)
        self.text_reasoning.setMaximumHeight(150)
        self.result_layout.addWidget(self.text_reasoning)
        
        # 보안 권고사항
        self.label_recommendations_title = QLabel("💡 보안 권고사항")
        self.label_recommendations_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.result_layout.addWidget(self.label_recommendations_title)
        
        self.text_recommendations = QTextEdit()
        self.text_recommendations.setReadOnly(True)
        self.text_recommendations.setMaximumHeight(250)
        self.result_layout.addWidget(self.text_recommendations)
        
        # 민감정보 마스킹 버튼
        self.btn_mask_pdf = QPushButton("🔒 민감정보 마스킹 PDF 저장")
        self.btn_mask_pdf.setVisible(False)  # 분석 완료 시 표시
        self.btn_mask_pdf.clicked.connect(self.export_masked_pdf)
        if self.config.get_dark_mode():
            self.btn_mask_pdf.setStyleSheet("""
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border: 1px solid #0d47a1;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #2196f3;
                }
            """)
        else:
            self.btn_mask_pdf.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        self.result_layout.addWidget(self.btn_mask_pdf)
        
        self.result_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        right_layout.addWidget(scroll)
        
        right_group.setLayout(right_layout)
        layout.addWidget(right_group, 2)
        
        widget.setLayout(layout)
        return widget
    
    def create_batch_analysis_tab(self) -> QWidget:
        """일괄 분석 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 드래그 앤 드롭 영역
        drop_area_batch = DropLabel("📁 여기에 여러 파일을 드래그 앤 드롭하세요")
        drop_area_batch.setMinimumHeight(60)
        drop_area_batch.files_dropped.connect(self.handle_multiple_files_drop)
        layout.addWidget(drop_area_batch)
        
        # 제어 버튼
        control_layout = QHBoxLayout()
        
        btn_select_files = QPushButton("📚 여러 파일 선택")
        btn_select_files.clicked.connect(self.select_multiple_files)
        control_layout.addWidget(btn_select_files)
        
        self.label_file_count = QLabel("선택된 파일: 0개")
        control_layout.addWidget(self.label_file_count, 1)
        
        self.btn_start_batch = QPushButton("🚀 일괄 분석 시작")
        self.btn_start_batch.setEnabled(False)
        self.btn_start_batch.clicked.connect(self.start_batch_analysis)
        control_layout.addWidget(self.btn_start_batch)
        
        self.btn_cancel_batch = QPushButton("⛔ 취소")
        self.btn_cancel_batch.setVisible(False)
        self.btn_cancel_batch.clicked.connect(self.cancel_batch_analysis)
        if self.config.get_dark_mode():
            self.btn_cancel_batch.setStyleSheet("""
                QPushButton {
                    background-color: #c62828;
                    color: white;
                    padding: 8px 16px;
                    border: 1px solid #8e0000;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
        else:
            self.btn_cancel_batch.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        control_layout.addWidget(self.btn_cancel_batch)
        
        self.btn_clear_batch = QPushButton("🗑️ 목록 초기화")
        self.btn_clear_batch.clicked.connect(self.clear_batch_list)
        control_layout.addWidget(self.btn_clear_batch)
        
        self.btn_batch_mask = QPushButton("🔒 민감정보 마스킹")
        self.btn_batch_mask.clicked.connect(self.show_batch_mask_dialog)
        control_layout.addWidget(self.btn_batch_mask)
        
        layout.addLayout(control_layout)
        
        # 진행률
        self.batch_progress_bar = QProgressBar()
        layout.addWidget(self.batch_progress_bar)
        
        self.label_batch_status = QLabel("대기 중...")
        layout.addWidget(self.label_batch_status)
        
        # 결과 테이블
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(6)
        self.batch_table.setHorizontalHeaderLabels(['파일명', '위험도', '점수', '탐지수', '상태', '단일 분석'])
        self.batch_table.horizontalHeader().setStretchLastSection(False)
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.batch_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_statistics_tab(self) -> QWidget:
        """통계 탭 (일괄분석 통계만)"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 일괄분석 통계 제목
        title_label = QLabel("📊 일괄분석 통계")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        from PyQt5.QtWidgets import QGridLayout
        batch_stats_layout = QGridLayout()
        
        batch_stats_layout.addWidget(QLabel("분석된 파일 수:"), 0, 0)
        self.label_batch_count = QLabel("0")
        self.label_batch_count.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        batch_stats_layout.addWidget(self.label_batch_count, 0, 1)
        
        batch_stats_layout.addWidget(QLabel("평균 위험도:"), 1, 0)
        self.label_batch_avg_risk = QLabel("-")
        self.label_batch_avg_risk.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        batch_stats_layout.addWidget(self.label_batch_avg_risk, 1, 1)
        
        batch_stats_layout.addWidget(QLabel("고위험 파일:"), 2, 0)
        self.label_batch_high_risk = QLabel("0")
        self.label_batch_high_risk.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.label_batch_high_risk.setStyleSheet("color: red;")
        batch_stats_layout.addWidget(self.label_batch_high_risk, 2, 1)
        
        layout.addLayout(batch_stats_layout)
        
        # 일괄분석 결과 테이블
        self.batch_stats_table = QTableWidget()
        self.batch_stats_table.setColumnCount(3)
        self.batch_stats_table.setHorizontalHeaderLabels(['파일명', '위험도', '점수'])
        self.batch_stats_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.batch_stats_table)
        
        # 새로고침 버튼
        btn_refresh = QPushButton("🔄 통계 새로고침")
        btn_refresh.clicked.connect(self.refresh_statistics)
        layout.addWidget(btn_refresh)
        
        widget.setLayout(layout)
        return widget
    
    def create_recent_history_tab(self) -> QWidget:
        """최근 분석 기록 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 제목 및 안내
        title_layout = QHBoxLayout()
        title_label = QLabel("📜 최근 분석 기록")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        # 선택 안내 레이블
        hint_label = QLabel("💡 Ctrl+클릭으로 여러 항목 선택 가능")
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        title_layout.addStretch()
        title_layout.addWidget(hint_label)
        layout.addLayout(title_layout)
        
        # 최근 분석 기록 테이블
        self.recent_history_table = QTableWidget()
        self.recent_history_table.setColumnCount(6)
        self.recent_history_table.setHorizontalHeaderLabels(['시간', '파일명', 'LLM', '위험도', '점수', '보기'])
        self.recent_history_table.horizontalHeader().setStretchLastSection(False)
        self.recent_history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # 다중 선택 활성화
        self.recent_history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_history_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # 우클릭 메뉴 활성화
        self.recent_history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_history_table.customContextMenuRequested.connect(self.show_history_context_menu)
        
        layout.addWidget(self.recent_history_table)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 새로고침 버튼
        btn_refresh = QPushButton("🔄 기록 새로고침")
        btn_refresh.clicked.connect(self.refresh_recent_history)
        button_layout.addWidget(btn_refresh)
        
        # 선택 삭제 버튼
        self.btn_delete_selected = QPushButton("🗑️ 선택 삭제")
        self.btn_delete_selected.clicked.connect(self.delete_selected_history)
        button_layout.addWidget(self.btn_delete_selected)
        
        # 전체 삭제 버튼
        self.btn_clear_all = QPushButton("🗑️ 전체 삭제")
        self.btn_clear_all.clicked.connect(self.clear_all_history)
        button_layout.addWidget(self.btn_clear_all)
        
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def show_history_context_menu(self, position):
        """분석 기록 테이블 우클릭 메뉴"""
        selected_rows = self.recent_history_table.selectionModel().selectedRows()
        
        menu = QMenu(self)
        
        if selected_rows:
            delete_action = menu.addAction(f"🗑️ 선택한 {len(selected_rows)}개 항목 삭제")
            delete_action.triggered.connect(self.delete_selected_history)
        else:
            no_selection = menu.addAction("(항목을 선택하세요)")
            no_selection.setEnabled(False)
        
        menu.exec_(self.recent_history_table.mapToGlobal(position))
    
    def delete_selected_history(self):
        """선택된 분석 기록 삭제"""
        selected_rows = self.recent_history_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, '경고', '삭제할 항목을 선택하세요.\n\n💡 Ctrl+클릭으로 여러 항목을 선택할 수 있습니다.')
            return
        
        # 확인 메시지
        reply = QMessageBox.question(
            self,
            '선택 삭제 확인',
            f'선택한 {len(selected_rows)}개 항목을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 선택된 행에서 timestamp 추출 (UserRole에 저장됨)
            timestamps_to_delete = []
            for index in selected_rows:
                row = index.row()
                item = self.recent_history_table.item(row, 0)  # 시간 열
                if item:
                    timestamp = item.data(Qt.ItemDataRole.UserRole)
                    if timestamp:
                        timestamps_to_delete.append(timestamp)
            
            if timestamps_to_delete:
                # history에서 삭제
                deleted_count = self.history.delete_by_timestamps(timestamps_to_delete)
                
                # UI 새로고침
                self.refresh_recent_history()
                
                QMessageBox.information(
                    self,
                    '삭제 완료',
                    f'{deleted_count}개 항목이 삭제되었습니다.'
                )
                logger.info(f"선택 삭제 완료: {deleted_count}개 항목")
            else:
                QMessageBox.warning(self, '오류', '삭제할 항목을 찾을 수 없습니다.')
                
        except Exception as e:
            logger.error(f"선택 삭제 중 오류: {str(e)}")
            QMessageBox.critical(
                self,
                '삭제 오류',
                f'삭제 중 오류가 발생했습니다:\n{str(e)}'
            )
    
    
    def check_ollama_status(self):
        """Ollama 상태 확인"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.ollama_status.setText("✅ Ollama: 연결됨")
                self.ollama_status.setStyleSheet("color: green;")
            else:
                self.ollama_status.setText("⚠️ Ollama: 오류")
                self.ollama_status.setStyleSheet("color: orange;")
        except:
            self.ollama_status.setText("❌ Ollama: 연결 안됨")
            self.ollama_status.setStyleSheet("color: red;")
    
    def check_initial_ollama_setup(self):
        """애플리케이션 시작 시 Ollama 설치 확인"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            if response.status_code == 200:
                # Ollama가 설치되어 있고 실행 중
                return
        except:
            pass
        
        # Ollama가 설치되지 않았거나 실행되지 않는 경우
        # 설정에서 "다시 묻지 않기"가 설정되어 있는지 확인
        if not self.config.settings.value('ollama_setup_skip', False, type=bool):
            dialog = OllamaSetupDialog(self)
            result = dialog.exec()
            
            # "다시 묻지 않기"가 체크된 경우 설정 저장
            if hasattr(dialog, 'no_warning_checkbox') and dialog.no_warning_checkbox.isChecked():
                self.config.settings.setValue('ollama_setup_skip', True)
    
    def select_file(self):
        """파일 선택"""
        last_dir = self.config.get_last_directory()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "문서 선택", last_dir,
            "지원 문서 (*.pdf *.docx *.txt *.hwp *.hwpx);;모든 파일 (*.*)"
        )
        
        if file_path:
            self.handle_file_selection(file_path)
    
    def handle_file_selection(self, file_path: str):
        """파일 선택 처리"""
        self.current_file = file_path
        self.config.set_last_directory(str(Path(file_path).parent))
        filename = Path(file_path).name
        self.label_filename.setText(f"📄 {filename}")
        self.btn_analyze.setEnabled(True)
        self.status_label.setText(f"파일 선택됨: {filename}")
    
    def on_files_dropped(self, files):
        """드롭된 파일 처리"""
        if len(files) == 1:
            # 단일 파일 - 단일 분석 탭
            self.handle_file_selection(files[0])
            self.tabs.setCurrentIndex(0)
        else:
            # 여러 파일 - 일괄 분석 탭
            self.handle_multiple_files_drop(files)
    
    def start_analysis(self):
        """분석 시작"""
        try:
            if not self.current_file:
                return
            
            self.btn_analyze.setVisible(False)
            self.btn_cancel.setVisible(True)
            self.btn_select_file.setEnabled(False)
            self.combo_model.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_message_label.setVisible(True)
            self.status_message_label.setText("🚀 분석 시작...")
            self.status_label.setText("분석 중...")
            
            # 실제 모델명 가져오기 (itemData에 저장된 값)
            model = self.combo_model.currentData()
            self.config.set_last_model(model)
            self.analysis_thread = AnalysisThread(self.current_file, model)
            self.analysis_thread.progress.connect(self.update_progress)
            self.analysis_thread.finished.connect(self.analysis_finished)
            self.analysis_thread.error.connect(self.analysis_error)
            self.analysis_thread.status_message.connect(self.update_status_message)  # 상태 메시지 시그널 연결
            self.analysis_thread.start()
        except Exception as e:
            logger.error(f"분석 시작 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            self.restore_ui_state()
            QMessageBox.critical(self, '오류', f'분석 시작 중 오류가 발생했습니다:\n{str(e)}')
    
    def update_progress(self, value: int):
        """진행률 업데이트"""
        self.progress_bar.setValue(value)
    
    def update_status_message(self, message: str):
        """상태 메시지 업데이트"""
        self.status_message_label.setText(message)
    
    def analysis_finished(self, analysis_result: dict, detected_items: list, text: str):
        """분석 완료"""
        self.analysis_result = analysis_result
        self.detected_items = detected_items
        self.document_text = text
        
        # 결과 표시
        self.display_results()
        
        # 이력 저장 (분석 결과, 탐지 항목, 문서 텍스트, LLM 모델 포함)
        filename = Path(self.current_file).name
        current_model = self.combo_model.currentData()
        self.history.add_record(filename, analysis_result, len(detected_items), detected_items, text, current_model)
        
        # 자동 저장
        if self.config.get_auto_save():
            self.auto_save_results()
        
        # UI 복원
        self.restore_ui_state()
        self.status_label.setText("분석 완료")
        
        # 통계 및 최근 분석 기록 새로고침
        self.refresh_statistics()
        self.refresh_recent_history()
    
    def analysis_error(self, error_msg: str):
        """분석 오류"""
        QMessageBox.critical(self, "오류", error_msg)
        self.restore_ui_state()
        self.status_label.setText("분석 실패")
    
    def reset_analysis(self):
        """초기화"""
        try:
            # 진행 중인 단일 분석 스레드 취소
            if self.analysis_thread and self.analysis_thread.isRunning():
                self.analysis_thread.cancel()
                self.analysis_thread.wait(1000)  # 최대 1초 대기
            
            # 진행 중인 일괄 분석 스레드 취소
            if self.batch_thread and self.batch_thread.isRunning():
                self.batch_thread.cancel()
                self.batch_thread.wait(1000)
            
            # 데이터 초기화
            self.current_file = None
            self.analysis_result = None
            self.detected_items = []
            self.document_text = ""
            
            # UI 초기화
            self.label_filename.setText("선택된 파일 없음")
            if self.config.get_dark_mode():
                self.label_filename.setStyleSheet("color: #888;")
            else:
                self.label_filename.setStyleSheet("color: gray;")
            self.btn_analyze.setEnabled(False)
            
            # 텍스트 위젯 초기화
            if hasattr(self, 'text_document'):
                self.text_document.clear()
            if hasattr(self, 'text_detected'):
                self.text_detected.clear()
            if hasattr(self, 'text_reasoning'):
                self.text_reasoning.clear()
            if hasattr(self, 'text_recommendations'):
                self.text_recommendations.clear()
            
            # 위험도 표시 초기화
            if hasattr(self, 'label_risk_level'):
                self.label_risk_level.setText("위험도: -")
            if hasattr(self, 'label_risk_score'):
                self.label_risk_score.setText("점수: -")
            if hasattr(self, 'risk_frame'):
                self.risk_frame.setStyleSheet("background-color: #9E9E9E; border-radius: 5px; padding: 10px;")
            
            # 민감정보 마스킹 버튼 숨김
            if hasattr(self, 'btn_mask_pdf'):
                self.btn_mask_pdf.setVisible(False)
            
            # UI 상태 복원
            self.restore_ui_state()
            
            self.status_label.setText("초기화됨")
            logger.info("분석 초기화 완료")
            
        except Exception as e:
            logger.error(f"초기화 중 오류: {str(e)}")
            self.status_label.setText("초기화 중 오류 발생")
            QMessageBox.warning(self, '경고', f'초기화 중 오류가 발생했습니다:\n{str(e)}')
    
    def show_history(self):
        """이력 표시"""
        dialog = HistoryDialog(self, self.history)
        dialog.exec()
    
    def clear_all_history(self):
        """전체 분석 기록 및 캐시 삭제"""
        reply = QMessageBox.question(
            self, 
            '전체 삭제 확인', 
            '모든 분석 기록과 캐시를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 분석 기록 삭제
                self.history.clear()
                
                # 캐시 파일들 삭제
                import os
                import glob
                
                # __pycache__ 폴더들 삭제
                for root, dirs, files in os.walk('.'):
                    for dir_name in dirs:
                        if dir_name == '__pycache__':
                            pycache_path = os.path.join(root, dir_name)
                            try:
                                import shutil
                                shutil.rmtree(pycache_path)
                                logger.info(f"캐시 폴더 삭제: {pycache_path}")
                            except Exception as e:
                                logger.warning(f"캐시 폴더 삭제 실패: {pycache_path} - {e}")
                
                # .pyc 파일들 삭제
                for pyc_file in glob.glob('**/*.pyc', recursive=True):
                    try:
                        os.remove(pyc_file)
                        logger.info(f"캐시 파일 삭제: {pyc_file}")
                    except Exception as e:
                        logger.warning(f"캐시 파일 삭제 실패: {pyc_file} - {e}")
                
                # 로그 파일 삭제 (선택적) - 사용 중인 파일은 건너뛰기
                log_files = ['document_analyzer.log']
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            # 파일이 사용 중인지 확인
                            with open(log_file, 'a') as f:
                                pass  # 파일 접근 테스트
                            os.remove(log_file)
                            logger.info(f"로그 파일 삭제: {log_file}")
                        except PermissionError:
                            # 파일이 사용 중인 경우 건너뛰기
                            logger.info(f"로그 파일이 사용 중이므로 삭제를 건너뜁니다: {log_file}")
                        except Exception as e:
                            logger.warning(f"로그 파일 삭제 실패: {log_file} - {e}")
                
                # UI 새로고침
                self.refresh_recent_history()
                self.refresh_statistics()
                
                QMessageBox.information(
                    self, 
                    '삭제 완료', 
                    '모든 분석 기록과 캐시가 성공적으로 삭제되었습니다.'
                )
                
            except Exception as e:
                logger.error(f"전체 삭제 중 오류: {str(e)}")
                QMessageBox.critical(
                    self, 
                    '삭제 오류', 
                    f'삭제 중 오류가 발생했습니다:\n{str(e)}'
                )
    
    def show_settings(self):
        """설정 표시"""
        analyzer = LocalLLMAnalyzer(self.combo_model.currentText())
        dialog = SettingsDialog(self, self.config, analyzer)
        dialog.exec()
    
    def show_custom_patterns(self):
        """사용자 정의 패턴 관리 창 표시"""
        try:
            # 지연 로딩으로 순환 참조 방지
            from gui.dialogs.custom_pattern_dialog import CustomPatternDialog
            dialog = CustomPatternDialog(self)
            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self, 
                "오류", 
                f"사용자 정의 패턴 창을 열 수 없습니다.\n\n오류: {str(e)}"
            )
    
    def show_about(self):
        """정보 표시"""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def show_codef_settings(self):
        """CODEF API 설정 표시"""
        dialog = CodefSettingsDialog(self, self.config)
        dialog.exec()
    
    def show_driver_license_verify(self, license_number: str):
        """운전면허 진위확인 다이얼로그 표시"""
        # API 설정 확인
        if not self.config.is_codef_configured():
            reply = QMessageBox.question(
                self,
                'API 설정 필요',
                'CODEF API가 설정되지 않았습니다.\n'
                'API 설정 화면으로 이동하시겠습니까?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.show_codef_settings()
            return
        
        dialog = DriverLicenseVerifyDialog(self, license_number)
        dialog.exec()
    
    
    def apply_theme(self):
        """테마 적용"""
        if self.config.get_dark_mode():
            self.setStyleSheet("""
                /* 기본 위젯 */
                QMainWindow, QWidget, QDialog {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
                
                /* 그룹박스 */
                QGroupBox {
                    background-color: #2b2b2b;
                    border: 1px solid #444;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                    color: #e0e0e0;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                
                /* 입력 필드 */
                QTextEdit, QLineEdit, QComboBox, QListWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 5px;
                    color: #e0e0e0;
                    selection-background-color: #0d47a1;
                }
                
                /* 콤보박스 드롭다운 */
                QComboBox::drop-down {
                    border: none;
                    background-color: #3c3c3c;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #e0e0e0;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    selection-background-color: #0d47a1;
                    color: #e0e0e0;
                }
                
                /* 버튼 */
                QPushButton {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border: 1px solid #666;
                }
                QPushButton:pressed {
                    background-color: #2a2a2a;
                }
                QPushButton:disabled {
                    background-color: #2a2a2a;
                    color: #666;
                }
                
                /* 테이블 */
                QTableWidget {
                    background-color: #2d2d2d;
                    alternate-background-color: #333;
                    border: 1px solid #444;
                    gridline-color: #444;
                    color: #e0e0e0;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #0d47a1;
                }
                QHeaderView::section {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    padding: 5px;
                    border: 1px solid #444;
                    font-weight: bold;
                }
                
                /* 탭 위젯 */
                QTabWidget::pane {
                    border: 1px solid #444;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    padding: 8px 16px;
                    border: 1px solid #444;
                    border-bottom: none;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #2b2b2b;
                    border-bottom: 2px solid #0d47a1;
                }
                QTabBar::tab:hover {
                    background-color: #4a4a4a;
                }
                
                /* 프로그레스바 */
                QProgressBar {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 3px;
                    text-align: center;
                    color: #e0e0e0;
                }
                QProgressBar::chunk {
                    background-color: #0d47a1;
                    border-radius: 2px;
                }
                
                /* 스크롤바 */
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: #555;
                    min-height: 20px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #666;
                }
                QScrollBar:horizontal {
                    background-color: #2d2d2d;
                    height: 12px;
                    border: none;
                }
                QScrollBar::handle:horizontal {
                    background-color: #555;
                    min-width: 20px;
                    border-radius: 6px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #666;
                }
                
                /* 메뉴바 */
                QMenuBar {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border-bottom: 1px solid #444;
                }
                QMenuBar::item {
                    padding: 5px 10px;
                    background-color: transparent;
                }
                QMenuBar::item:selected {
                    background-color: #3c3c3c;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border: 1px solid #444;
                }
                QMenu::item {
                    padding: 5px 25px;
                }
                QMenu::item:selected {
                    background-color: #0d47a1;
                }
                
                /* 상태바 */
                QStatusBar {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                    border-top: 1px solid #444;
                }
                
                /* 라벨 */
                QLabel {
                    color: #e0e0e0;
                }
                
                /* 프레임 */
                QFrame {
                    border: 1px solid #444;
                }
            """)
        else:
            self.setStyleSheet("")
        
        # 상태 메시지 레이블 스타일 적용
        self._apply_status_message_style()
        
        # 전체 삭제 버튼 스타일 적용
        self._apply_clear_all_button_style()
    
    def _apply_status_message_style(self):
        """상태 메시지 레이블 스타일 적용"""
        if hasattr(self, 'status_message_label'):
            if self.config.get_dark_mode():
                self.status_message_label.setStyleSheet("""
                    QLabel {
                        background-color: #2d2d2d;
                        border: 1px solid #444;
                        border-radius: 3px;
                        padding: 5px;
                        font-size: 11px;
                        color: #e0e0e0;
                    }
                """)
            else:
                self.status_message_label.setStyleSheet("""
                    QLabel {
                        background-color: #f0f0f0;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        padding: 5px;
                        font-size: 11px;
                        color: #333;
                    }
                """)
    
    def _apply_clear_all_button_style(self):
        """전체 삭제 버튼 스타일 적용"""
        if hasattr(self, 'btn_clear_all'):
            if self.config.get_dark_mode():
                self.btn_clear_all.setStyleSheet("""
                    QPushButton {
                        background-color: #c62828;
                        color: white;
                        font-weight: bold;
                        padding: 8px 16px;
                        border: 1px solid #8e0000;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                        border: 1px solid #c62828;
                    }
                """)
            else:
                self.btn_clear_all.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-weight: bold;
                        padding: 8px 16px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                """)
    
    def cancel_analysis(self):
        """분석 취소"""
        try:
            if self.analysis_thread and self.analysis_thread.isRunning():
                # 취소 요청
                self.analysis_thread.cancel()
                
                # 스레드 종료 대기 (최대 3초)
                if not self.analysis_thread.wait(3000):
                    logger.warning("분석 스레드가 3초 내에 종료되지 않았습니다.")
                    # 강제 종료는 하지 않음 - 자연스럽게 종료되도록 함
                
                # UI 상태 복원
                self.restore_ui_state()
                self.status_label.setText("분석 취소됨")
                logger.info("분석 취소 완료")
                
                QMessageBox.information(self, '취소', '분석이 취소되었습니다.')
            else:
                self.status_label.setText("취소할 분석 작업이 없습니다.")
                logger.warning("취소할 분석 스레드가 없거나 이미 종료됨")
                
        except Exception as e:
            logger.error(f"분석 취소 중 오류: {str(e)}")
            self.restore_ui_state()
            self.status_label.setText("취소 중 오류 발생")
            QMessageBox.warning(self, '경고', f'취소 중 오류가 발생했습니다:\n{str(e)}')
    
    def restore_ui_state(self):
        """UI 상태 복원"""
        self.btn_analyze.setVisible(True)
        self.btn_analyze.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.btn_select_file.setEnabled(True)
        self.combo_model.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_message_label.setVisible(False)
    
    def display_results(self):
        """결과 표시 (각 섹션별로)"""
        risk_level = self.analysis_result.get('risk_level', '알 수 없음')
        risk_score = self.analysis_result.get('risk_score', 0)
        
        # 위험도 프레임
        self.label_risk_level.setText(f"위험도: {risk_level}")
        self.label_risk_score.setText(f"점수: {risk_score}/100")
        
        color = RISK_COLORS.get(risk_level, "#9E9E9E")
        self.risk_frame.setStyleSheet(
            f"background-color: {color}; border-radius: 5px; padding: 10px;"
        )
        
        # 탐지된 민감정보
        type_counts = {}
        for item in self.detected_items:
            type_counts[item['type']] = type_counts.get(item['type'], 0) + 1
        
        detected_text = f"총 {len(self.detected_items)}개 탐지\n\n"
        for t, c in type_counts.items():
            detected_text += f"• {t}: {c}개\n"
        self.text_detected.setText(detected_text)
        
        # 판단 근거
        self.text_reasoning.setText(self.analysis_result.get('reasoning', ''))
        
        # 보안 권고사항
        recs = self.analysis_result.get('recommendations', [])
        rec_text = ""
        for i, rec in enumerate(recs, 1):
            rec_text += f"{i}. {rec}\n\n"
        self.text_recommendations.setText(rec_text)
        
        # 문서 하이라이팅
        self.highlight_document()
        
        # 민감정보 마스킹 버튼 표시
        self.btn_mask_pdf.setVisible(True)
    
    def highlight_document(self):
        """문서 하이라이팅"""
        # 완전히 초기화 (이전 포맷 캐시 제거)
        self.text_document.clear()
        
        # 기본 문자 포맷 설정 (하이라이트 없음)
        default_format = QTextCharFormat()
        default_format.setBackground(QColor("transparent"))
        if self.config.get_dark_mode():
            default_format.setForeground(QColor("#e0e0e0"))
        else:
            default_format.setForeground(QColor("#000000"))
        
        # 기본 포맷으로 리셋 후 텍스트 삽입
        self.text_document.setCurrentCharFormat(default_format)
        self.text_document.setPlainText(self.document_text)
        
        # 탐지된 항목이 없으면 하이라이팅 스킵
        if not self.detected_items:
            return
        
        cursor = self.text_document.textCursor()
        
        for item in sorted(self.detected_items, key=lambda x: x.get('start', 0)):
            if item.get('start', -1) >= 0:
                fmt = QTextCharFormat()
                color_tuple = HIGHLIGHT_COLORS.get(item['type'], HIGHLIGHT_COLORS['default'])
                color = QColor(*color_tuple)
                fmt.setBackground(color)
                
                # 라이트 모드/다크 모드에 따라 텍스트 색상 지정
                if self.config.get_dark_mode():
                    # 다크 모드: 밝은 텍스트
                    fmt.setForeground(QColor("#ffffff"))
                else:
                    # 라이트 모드: 어두운 텍스트
                    fmt.setForeground(QColor("#000000"))
                
                cursor.setPosition(item['start'])
                cursor.setPosition(item['end'], QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(fmt)
    
    def handle_multiple_files_drop(self, files):
        """여러 파일 드롭 처리"""
        self.batch_files = files
        self.config.set_last_directory(str(Path(files[0]).parent))
        self.label_file_count.setText(f"선택된 파일: {len(files)}개")
        self.btn_start_batch.setEnabled(True)
        self.tabs.setCurrentIndex(1)  # 일괄 분석 탭으로 전환
        self.status_label.setText(f"{len(files)}개 파일 드롭됨")
    
    def select_multiple_files(self):
        """여러 파일 선택"""
        last_dir = self.config.get_last_directory()
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "여러 파일 선택", last_dir,
            "지원 문서 (*.pdf *.docx *.txt *.hwp *.hwpx)"
        )
        
        if file_paths:
            self.handle_multiple_files_drop(file_paths)
    
    def start_batch_analysis(self):
        """일괄 분석 시작"""
        if not self.batch_files:
            return
        
        self.btn_start_batch.setVisible(False)
        self.btn_cancel_batch.setVisible(True)
        self.batch_progress_bar.setValue(0)
        self.batch_table.setRowCount(0)
        self.batch_results.clear()  # 이전 결과 초기화
        self.status_message_label.setVisible(True)
        self.status_message_label.setText("🚀 일괄 분석 시작...")
        
        model = self.combo_model.currentData()
        self.batch_thread = BatchAnalysisThread(self.batch_files, model)
        self.batch_thread.file_progress.connect(self.update_batch_progress)
        self.batch_thread.detailed_progress.connect(self.update_detailed_batch_progress)  # 세밀한 진행률 연결
        self.batch_thread.file_finished.connect(self.batch_file_finished)
        self.batch_thread.all_finished.connect(self.batch_all_finished)
        self.batch_thread.status_message.connect(self.update_status_message)  # 상태 메시지 시그널 연결
        self.batch_thread.start()
    
    def update_batch_progress(self, current: int, total: int, filename: str):
        """일괄 분석 진행"""
        progress = int((current / total) * 100)
        self.batch_progress_bar.setValue(progress)
        self.label_batch_status.setText(f"분석 중: {filename} ({current}/{total})")
    
    def update_detailed_batch_progress(self, progress: float):
        """세밀한 일괄 분석 진행률 업데이트"""
        self.batch_progress_bar.setValue(int(progress))
    
    def batch_file_finished(self, filename: str, result: dict, detected: list, text: str, file_path: str):
        """파일 분석 완료"""
        row = self.batch_table.rowCount()
        self.batch_table.insertRow(row)
        
        # 결과 저장
        self.batch_results[filename] = {
            'result': result,
            'detected': detected,
            'text': text,
            'file_path': file_path
        }
        
        # 테이블 항목 추가 (체크박스 제거됨)
        self.batch_table.setItem(row, 0, QTableWidgetItem(filename))
        self.batch_table.setItem(row, 1, QTableWidgetItem(result.get('risk_level', '-')))
        self.batch_table.setItem(row, 2, QTableWidgetItem(str(result.get('risk_score', 0))))
        self.batch_table.setItem(row, 3, QTableWidgetItem(str(len(detected))))
        self.batch_table.setItem(row, 4, QTableWidgetItem("✅ 완료"))
        
        # "보기" 버튼 추가
        btn_view = QPushButton("보기")
        btn_view.clicked.connect(lambda checked, fn=filename: self.view_batch_result(fn))
        if self.config.get_dark_mode():
            btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #0d47a1;
                    color: white;
                    padding: 4px 8px;
                    border: 1px solid #0a3d91;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
            """)
        else:
            btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        self.batch_table.setCellWidget(row, 5, btn_view)
        
        # 이력 저장 (분석 결과, 탐지 항목, 문서 텍스트, LLM 모델 포함)
        current_model = self.combo_model.currentData()
        self.history.add_record(filename, result, len(detected), detected, text, current_model)
    
    def batch_all_finished(self):
        """일괄 분석 완료"""
        # 진행률을 100%까지 서서히 증가
        current_progress = self.batch_progress_bar.value()
        if current_progress < 100:
            from PyQt5.QtCore import QTimer
            self.batch_completion_timer = QTimer()
            self.batch_completion_progress = current_progress
            self.batch_completion_timer.timeout.connect(self._update_batch_completion_progress)
            self.batch_completion_timer.start(50)  # 50ms마다 업데이트
        else:
            self._finalize_batch_analysis()
    
    def _update_batch_completion_progress(self):
        """일괄 분석 완료 진행률 업데이트"""
        self.batch_completion_progress += 2
        self.batch_progress_bar.setValue(self.batch_completion_progress)
        
        if self.batch_completion_progress >= 100:
            self.batch_completion_timer.stop()
            self._finalize_batch_analysis()
    
    def _finalize_batch_analysis(self):
        """일괄 분석 최종 완료 처리"""
        self.batch_progress_bar.setValue(100)
        self.label_batch_status.setText("✅ 모든 파일 분석 완료")
        self.btn_start_batch.setVisible(True)
        self.btn_start_batch.setEnabled(True)
        self.btn_cancel_batch.setVisible(False)
        self.status_message_label.setVisible(False)  # 상태 메시지 레이블 숨김
        self.refresh_statistics()
        self.refresh_recent_history()
        QMessageBox.information(self, '완료', f'{len(self.batch_files)}개 파일 분석이 완료되었습니다.')
    
    def cancel_batch_analysis(self):
        """일괄 분석 취소"""
        try:
            if self.batch_thread and self.batch_thread.isRunning():
                # 취소 요청
                self.batch_thread.cancel()
                
                # 스레드 종료 대기 (최대 3초)
                if not self.batch_thread.wait(3000):
                    logger.warning("일괄 분석 스레드가 3초 내에 종료되지 않았습니다.")
                
                # UI 상태 복원
                self.btn_start_batch.setVisible(True)
                self.btn_start_batch.setEnabled(True)
                self.btn_cancel_batch.setVisible(False)
                self.status_message_label.setVisible(False)  # 상태 메시지 레이블 숨김
                self.label_batch_status.setText("⛔ 일괄 분석 취소됨")
                logger.info("일괄 분석 취소 완료")
                
                QMessageBox.information(self, '취소', '일괄 분석이 취소되었습니다.')
            else:
                self.label_batch_status.setText("취소할 분석 작업이 없습니다.")
                logger.warning("취소할 일괄 분석 스레드가 없거나 이미 종료됨")
                
        except Exception as e:
            logger.error(f"일괄 분석 취소 중 오류: {str(e)}")
            self.btn_start_batch.setVisible(True)
            self.btn_start_batch.setEnabled(True)
            self.btn_cancel_batch.setVisible(False)
            self.status_message_label.setVisible(False)  # 상태 메시지 레이블 숨김
            self.label_batch_status.setText("취소 중 오류 발생")
            QMessageBox.warning(self, '경고', f'취소 중 오류가 발생했습니다:\n{str(e)}')
    
    def clear_batch_list(self):
        """일괄 분석 목록 초기화 (이력은 유지)"""
        # 분석 중이면 초기화 불가
        if self.batch_thread and self.batch_thread.isRunning():
            QMessageBox.warning(self, '경고', '분석이 진행 중입니다. 먼저 취소하거나 완료될 때까지 기다려주세요.')
            return
        
        # 목록이 비어있으면 초기화 불필요
        if self.batch_table.rowCount() == 0:
            QMessageBox.information(self, '알림', '초기화할 목록이 없습니다.')
            return
        
        # 경고 팝업
        reply = QMessageBox.question(
            self, 
            '목록 초기화 확인', 
            f'일괄 분석 목록({self.batch_table.rowCount()}개 항목)을 초기화하시겠습니까?\n\n'
            '※ 분석 이력은 유지되며, 화면의 목록만 깔끔하게 정리됩니다.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 테이블 초기화
            self.batch_table.setRowCount(0)
            
            # 배치 파일 목록 초기화
            self.batch_files.clear()
            
            # 배치 결과 캐시 초기화
            self.batch_results.clear()
            
            # 상태 업데이트
            self.label_file_count.setText("선택된 파일: 0개")
            self.label_batch_status.setText("목록이 초기화되었습니다")
            self.btn_start_batch.setEnabled(False)
            self.batch_progress_bar.setValue(0)
            
            logger.info("일괄 분석 목록 초기화 완료")
            QMessageBox.information(self, '완료', '일괄 분석 목록이 초기화되었습니다.')
    
    def show_batch_mask_dialog(self):
        """일괄 마스킹 대화상자 표시"""
        if self.batch_table.rowCount() == 0:
            QMessageBox.warning(self, '경고', '마스킹할 파일이 없습니다.')
            return
        
        # 대화상자 생성
        dialog = QDialog(self)
        dialog.setWindowTitle("일괄 민감정보 마스킹")
        dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        
        # 설명 레이블
        label = QLabel("마스킹할 파일을 선택하세요:")
        layout.addWidget(label)
        
        # 전체 선택/해제 버튼
        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("전체 선택")
        btn_select_all.clicked.connect(lambda: self.toggle_all_checkboxes(True))
        btn_deselect_all = QPushButton("전체 해제")
        btn_deselect_all.clicked.connect(lambda: self.toggle_all_checkboxes(False))
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_deselect_all)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 파일 목록 (체크박스 포함)
        self.mask_list_widget = QListWidget()
        for row in range(self.batch_table.rowCount()):
            filename_item = self.batch_table.item(row, 0)
            
            if filename_item:
                item = QListWidgetItem(filename_item.text())
                item.setData(1, row)  # 행 번호 저장
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)  # 기본적으로 모두 체크
                self.mask_list_widget.addItem(item)
        
        layout.addWidget(self.mask_list_widget)
        
        # 실행 버튼
        btn_execute = QPushButton("선택된 파일 마스킹")
        btn_execute.clicked.connect(lambda: self.execute_batch_masking(dialog))
        layout.addWidget(btn_execute)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def toggle_all_checkboxes(self, checked: bool):
        """모든 체크박스 선택/해제"""
        for i in range(self.mask_list_widget.count()):
            item = self.mask_list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    
    def execute_batch_masking(self, dialog: QDialog):
        """선택된 파일들의 일괄 마스킹 실행 (개별 파일로 저장)"""
        selected_files = []
        
        for i in range(self.mask_list_widget.count()):
            item = self.mask_list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                row = item.data(1)
                filename_item = self.batch_table.item(row, 0)
                
                if filename_item:
                    filename = filename_item.text()
                    if filename in self.batch_results:
                        selected_files.append((filename, self.batch_results[filename]))
        
        if not selected_files:
            QMessageBox.warning(self, '경고', '선택된 파일이 없습니다.')
            return
        
        # 저장 디렉토리 선택
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "마스킹된 파일 저장 위치 선택"
        )
        
        if not save_dir:
            return
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.utils import simpleSplit
            
            # 한글 폰트 등록 시도
            try:
                pdfmetrics.registerFont(TTFont('Malgun', 'malgun.ttf'))
                font_name = 'Malgun'
            except:
                try:
                    pdfmetrics.registerFont(TTFont('Gulim', 'gulim.ttf'))
                    font_name = 'Gulim'
                except:
                    font_name = 'Helvetica'
            
            # 각 파일을 개별 PDF로 저장
            saved_files = []
            for filename, batch_data in selected_files:
                # 파일명 생성 (확장자 제거 후 _masked 추가)
                base_name = Path(filename).stem
                output_filename = f"{base_name}_masked.pdf"
                output_path = Path(save_dir) / output_filename
                
                # PDF 생성
                c = canvas.Canvas(str(output_path), pagesize=A4)
                width, height = A4
                
                # 마스킹 처리
                analyzer = LocalLLMAnalyzer()
                masked_text = analyzer.mask_sensitive_info(
                    batch_data['text'], 
                    batch_data['detected']
                )
                
                # 마스킹된 내용 출력
                c.setFont(font_name, 9)
                y_position = height - 50
                
                max_width = width - 100
                lines = masked_text.split('\n')
                
                for line in lines:
                    wrapped_lines = simpleSplit(line if line else ' ', font_name, 9, max_width)
                    
                    for wrapped_line in wrapped_lines:
                        if y_position < 50:
                            c.showPage()
                            c.setFont(font_name, 9)
                            y_position = height - 50
                        
                        c.drawString(50, y_position, wrapped_line)
                        y_position -= 15
                
                c.save()
                saved_files.append(output_filename)
                logger.info(f"마스킹 PDF 저장: {output_path}")
            
            QMessageBox.information(
                self, 
                '완료', 
                f'{len(saved_files)}개 파일의 민감정보가 마스킹되어 개별 PDF로 저장되었습니다.\n\n저장 위치: {save_dir}\n\n' + 
                '\n'.join(f'• {f}' for f in saved_files[:5]) + 
                (f'\n... 외 {len(saved_files)-5}개' if len(saved_files) > 5 else '')
            )
            logger.info(f"일괄 마스킹 완료: {len(saved_files)}개 파일")
            
            dialog.accept()
            
        except Exception as e:
            logger.error(f"일괄 마스킹 PDF 생성 오류: {str(e)}")
            QMessageBox.critical(
                self, 
                '오류', 
                f'PDF 생성 중 오류가 발생했습니다:\n{str(e)}'
            )
    
    def view_batch_result(self, filename: str):
        """일괄 분석 결과를 단일 분석 탭에서 보기"""
        if filename not in self.batch_results:
            QMessageBox.warning(self, '오류', '해당 파일의 분석 결과를 찾을 수 없습니다.')
            return
        
        # 결과 가져오기
        batch_data = self.batch_results[filename]
        self.current_file = batch_data['file_path']
        self.analysis_result = batch_data['result']
        self.detected_items = batch_data['detected']
        self.document_text = batch_data['text']
        
        # UI 업데이트
        self.label_filename.setText(f"📄 {filename}")
        self.btn_analyze.setEnabled(True)
        
        # 결과 표시
        self.display_results()
        
        # 단일 분석 탭으로 전환
        self.tabs.setCurrentIndex(0)
        self.status_label.setText(f"일괄 분석 결과 표시: {filename}")
    
    def refresh_statistics(self):
        """통계 새로고침 (일괄분석 통계만)"""
        # 일괄분석 통계 업데이트 (batch_results 기반)
        if self.batch_results:
            batch_count = len(self.batch_results)
            batch_scores = [data['result'].get('risk_score', 0) for data in self.batch_results.values()]
            batch_avg = sum(batch_scores) / batch_count if batch_count > 0 else 0
            batch_high_risk = sum(1 for score in batch_scores if score >= 75)
            
            self.label_batch_count.setText(str(batch_count))
            self.label_batch_avg_risk.setText(f"{batch_avg:.1f}")
            self.label_batch_high_risk.setText(str(batch_high_risk))
            
            # 일괄분석 결과 테이블
            self.batch_stats_table.setRowCount(batch_count)
            for i, (filename, data) in enumerate(self.batch_results.items()):
                self.batch_stats_table.setItem(i, 0, QTableWidgetItem(filename))
                self.batch_stats_table.setItem(i, 1, QTableWidgetItem(data['result'].get('risk_level', '-')))
                self.batch_stats_table.setItem(i, 2, QTableWidgetItem(str(data['result'].get('risk_score', 0))))
        else:
            self.label_batch_count.setText("0")
            self.label_batch_avg_risk.setText("-")
            self.label_batch_high_risk.setText("0")
            self.batch_stats_table.setRowCount(0)
    
    def refresh_recent_history(self):
        """최근 분석 기록 새로고침"""
        # 최근 분석 기록 업데이트 (history 기반)
        records = self.history.get_recent(20)
        self.recent_history_table.setRowCount(len(records))
        
        for i, record in enumerate(records):
            # 시간 표시 항목 (timestamp를 UserRole에 저장)
            timestamp_display = datetime.fromisoformat(record['timestamp']).strftime('%Y-%m-%d %H:%M')
            time_item = QTableWidgetItem(timestamp_display)
            time_item.setData(Qt.ItemDataRole.UserRole, record['timestamp'])  # 원본 timestamp 저장
            self.recent_history_table.setItem(i, 0, time_item)
            
            self.recent_history_table.setItem(i, 1, QTableWidgetItem(record['filename']))
            # LLM 모델 정보 (기존 기록에는 없을 수 있으므로 기본값 설정)
            llm_model = record.get('llm_model', '규칙 기반')
            self.recent_history_table.setItem(i, 2, QTableWidgetItem(llm_model))
            self.recent_history_table.setItem(i, 3, QTableWidgetItem(record['risk_level']))
            self.recent_history_table.setItem(i, 4, QTableWidgetItem(str(record['risk_score'])))
            
            # "보기" 버튼 추가
            btn_view = QPushButton("보기")
            # 분석 결과 데이터가 있는 경우에만 활성화
            has_data = 'detected_items' in record and 'document_text' in record
            btn_view.setEnabled(has_data)
            btn_view.clicked.connect(lambda checked, rec=record: self.view_history_result(rec))
            if self.config.get_dark_mode():
                btn_view.setStyleSheet("""
                    QPushButton {
                        background-color: #0d47a1;
                        color: white;
                        padding: 2px 6px;
                        border: 1px solid #0a3d91;
                    }
                    QPushButton:hover:enabled {
                        background-color: #1565c0;
                    }
                    QPushButton:disabled {
                        background-color: #2a2a2a;
                        color: #666;
                    }
                """)
            else:
                btn_view.setStyleSheet("""
                    QPushButton {
                        background-color: #2196F3;
                        color: white;
                        padding: 2px 6px;
                    }
                    QPushButton:hover:enabled {
                        background-color: #1976D2;
                    }
                    QPushButton:disabled {
                        background-color: #ccc;
                        color: #888;
                    }
                """)
            self.recent_history_table.setCellWidget(i, 5, btn_view)
    
    def view_history_result(self, record: dict):
        """최근 분석 기록에서 결과 보기"""
        if 'result' not in record or 'detected_items' not in record or 'document_text' not in record:
            QMessageBox.warning(self, '오류', '해당 기록의 분석 결과를 찾을 수 없습니다.')
            return
        
        # 결과 데이터 설정
        self.current_file = record.get('filename', '기록에서 조회')
        self.analysis_result = record['result']
        self.detected_items = record['detected_items']
        self.document_text = record['document_text']
        
        # UI 업데이트
        self.label_filename.setText(f"📄 {record['filename']} (기록)")
        self.btn_analyze.setEnabled(False)
        
        # 결과 표시
        self.display_results()
        
        # 단일 분석 탭으로 전환
        self.tabs.setCurrentIndex(0)
        self.status_label.setText(f"분석 기록 표시: {record['filename']}")
    
    def export_masked_pdf(self):
        """민감정보 마스킹 PDF 저장"""
        if not self.document_text or not self.detected_items:
            QMessageBox.warning(self, '경고', '마스킹할 문서가 없습니다.')
            return
        
        try:
            # 마스킹 처리
            analyzer = LocalLLMAnalyzer()
            masked_text = analyzer.mask_sensitive_info(self.document_text, self.detected_items)
            
            # 저장 경로 선택
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "민감정보 마스킹 PDF 저장",
                f"masked_{Path(self.current_file).stem}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # PDF 생성
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.utils import simpleSplit
            
            # 한글 폰트 등록 시도
            try:
                # Windows 기본 한글 폰트
                pdfmetrics.registerFont(TTFont('Malgun', 'malgun.ttf'))
                font_name = 'Malgun'
            except:
                try:
                    pdfmetrics.registerFont(TTFont('Gulim', 'gulim.ttf'))
                    font_name = 'Gulim'
                except:
                    # 폰트를 찾을 수 없으면 기본 폰트 사용 (한글 깨질 수 있음)
                    font_name = 'Helvetica'
            
            # PDF 생성
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            
            # 마스킹된 내용 (헤더 없이 바로 시작)
            c.setFont(font_name, 9)
            y_position = height - 50
            
            # 텍스트를 줄바꿈 처리하여 출력
            max_width = width - 100  # 좌우 여백 50씩
            lines = masked_text.split('\n')
            
            for line in lines:
                # 긴 줄은 자동으로 줄바꿈
                wrapped_lines = simpleSplit(line if line else ' ', font_name, 9, max_width)
                
                for wrapped_line in wrapped_lines:
                    if y_position < 50:  # 페이지 하단에 도달하면 새 페이지
                        c.showPage()
                        c.setFont(font_name, 9)
                        y_position = height - 50  # 헤더 없이 바로 시작
                    
                    c.drawString(50, y_position, wrapped_line)
                    y_position -= 15
            
            # 페이지 번호 추가
            page_num = c.getPageNumber()
            c.setFont(font_name, 8)
            c.drawString(width - 100, 30, f"Page {page_num}")
            
            c.save()
            
            QMessageBox.information(
                self, 
                '완료', 
                f'민감정보가 마스킹된 PDF 파일이 저장되었습니다.\n\n{file_path}'
            )
            logger.info(f"민감정보 마스킹 PDF 저장 완료: {file_path}")
            
        except Exception as e:
            logger.error(f"PDF 생성 오류: {str(e)}")
            QMessageBox.critical(
                self, 
                '오류', 
                f'PDF 생성 중 오류가 발생했습니다:\n{str(e)}'
            )
    
    def auto_save_results(self):
        """자동 저장"""
        try:
            save_dir = Path('analysis_results')
            save_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = Path(self.current_file).stem
            
            json_path = save_dir / f"{base_name}_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                export_data = {
                    'filename': Path(self.current_file).name,
                    'timestamp': datetime.now().isoformat(),
                    'analysis_result': self.analysis_result,
                    'detected_items': self.detected_items
                }
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"결과 자동 저장: {json_path}")
        except Exception as e:
            logger.error(f"자동 저장 실패: {str(e)}")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """드롭 이벤트"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                ext = Path(file_path).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(file_path)
        
        if files:
            self.on_files_dropped(files)
    
    def show_document_context_menu(self, position):
        """문서 내용 영역 커스텀 컨텍스트 메뉴"""
        # 선택된 텍스트 가져오기
        cursor = self.text_document.textCursor()
        selected_text = cursor.selectedText().strip()
        
        # 기본 컨텍스트 메뉴 생성
        menu = self.text_document.createStandardContextMenu()
        
        # 구분선 추가
        menu.addSeparator()
        
        # 사용자 정의 패턴 추가 메뉴
        add_pattern_action = menu.addAction("📝 사용자 정의 패턴에 추가")
        add_pattern_action.setEnabled(bool(selected_text))
        
        if not selected_text:
            add_pattern_action.setToolTip("텍스트를 먼저 선택하세요")
        
        # 메뉴 실행
        action = menu.exec_(self.text_document.mapToGlobal(position))
        
        # 사용자 정의 패턴 추가 선택 시
        if action == add_pattern_action and selected_text:
            self.show_add_pattern_dialog(selected_text)
    
    def show_add_pattern_dialog(self, selected_text: str):
        """선택한 텍스트를 사용자 정의 패턴으로 추가하는 다이얼로그"""
        try:
            from gui.dialogs.custom_pattern_dialog import CustomPatternDialog
            dialog = CustomPatternDialog(self, initial_pattern=selected_text)
            dialog.exec_()
        except Exception as e:
            logger.error(f"사용자 정의 패턴 추가 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "오류",
                f"패턴 추가 중 오류가 발생했습니다:\n{str(e)}"
            )