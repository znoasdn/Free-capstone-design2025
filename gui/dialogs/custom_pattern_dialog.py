"""
사용자 정의 패턴 관리 다이얼로그

키워드/정규식 패턴 추가, 수정, 삭제 UI
"""
import re
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QMessageBox, QHeaderView,
    QGroupBox, QFormLayout, QTextEdit, QCheckBox, QSpinBox, QTabWidget,
    QWidget, QFileDialog, QPlainTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from core.user_pattern_manager import get_pattern_manager
from utils.logger import logger


class CustomPatternDialog(QDialog):
    """사용자 정의 패턴 관리 다이얼로그"""
    
    def __init__(self, parent=None, initial_pattern: str = None):
        super().__init__(parent)
        self.pattern_manager = get_pattern_manager()
        self.initial_pattern = initial_pattern
        self.editing_pattern = None  # 수정 중인 패턴
        self.init_ui()
        self.load_patterns()
        
        # 초기 패턴이 있으면 추가/수정 탭으로 이동하고 입력란에 채워넣기
        if self.initial_pattern:
            self.tab_widget.setCurrentIndex(1)
            self.pattern_input.setText(self.initial_pattern)
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("사용자 정의 패턴 관리")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 탭 1: 패턴 목록
        self.list_tab = QWidget()
        self.init_list_tab()
        self.tab_widget.addTab(self.list_tab, "패턴 목록")
        
        # 탭 2: 패턴 추가/수정
        self.edit_tab = QWidget()
        self.init_edit_tab()
        self.tab_widget.addTab(self.edit_tab, "패턴 추가/수정")
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def init_list_tab(self):
        """패턴 목록 탭 초기화"""
        layout = QVBoxLayout(self.list_tab)
        
        # 패턴 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "활성", "이름", "패턴", "유형", "카테고리", "위험도"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # 버튼들
        btn_layout = QHBoxLayout()
        
        # 좌측 버튼들
        add_btn = QPushButton("➕ 추가")
        add_btn.clicked.connect(self.go_to_add_mode)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ 수정")
        edit_btn.clicked.connect(self.go_to_edit_mode)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ 삭제")
        delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(delete_btn)
        
        toggle_btn = QPushButton("🔄 활성화 토글")
        toggle_btn.clicked.connect(self.toggle_selected)
        btn_layout.addWidget(toggle_btn)
        
        btn_layout.addStretch()
        
        # 우측 버튼들
        import_btn = QPushButton("📥 가져오기")
        import_btn.clicked.connect(self.import_patterns)
        btn_layout.addWidget(import_btn)
        
        export_btn = QPushButton("📤 내보내기")
        export_btn.clicked.connect(self.export_patterns)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
    
    def init_edit_tab(self):
        """패턴 추가/수정 탭 초기화"""
        layout = QVBoxLayout(self.edit_tab)
        
        # 패턴 정보 그룹
        info_group = QGroupBox("패턴 정보")
        info_layout = QFormLayout(info_group)
        
        # 이름
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("예: 프로젝트 코드명, 사내 용어")
        info_layout.addRow("이름:", self.name_input)
        
        # 패턴
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("키워드 또는 정규식 입력")
        info_layout.addRow("패턴:", self.pattern_input)
        
        # 유형
        self.type_combo = QComboBox()
        self.type_combo.addItems(["keyword", "regex"])
        info_layout.addRow("유형:", self.type_combo)
        
        # 카테고리
        self.category_combo = QComboBox()
        self.category_combo.addItems(["사용자정의", "개인정보", "금융정보", "의료정보", "기업정보"])
        self.category_combo.setEditable(True)
        info_layout.addRow("카테고리:", self.category_combo)
        
        # 위험도
        score_layout = QHBoxLayout()
        self.score_input = QSpinBox()
        self.score_input.setRange(1, 15)
        self.score_input.setValue(8)
        score_layout.addWidget(self.score_input)
        score_layout.addWidget(QLabel("(1=낮음, 15=높음)"))
        score_layout.addStretch()
        info_layout.addRow("위험도:", score_layout)
        
        # 설명
        self.desc_input = QPlainTextEdit()
        self.desc_input.setPlaceholderText("이 패턴에 대한 설명을 입력하세요")
        self.desc_input.setMaximumHeight(80)
        info_layout.addRow("설명 (선택):", self.desc_input)
        
        layout.addWidget(info_group)
        
        # 패턴 테스트 그룹
        test_group = QGroupBox("패턴 테스트")
        test_layout = QVBoxLayout(test_group)
        
        self.test_input = QPlainTextEdit()
        self.test_input.setPlaceholderText("테스트할 텍스트를 입력하세요")
        self.test_input.setMaximumHeight(80)
        test_layout.addWidget(self.test_input)
        
        test_btn_layout = QHBoxLayout()
        test_btn = QPushButton("🔍 테스트")
        test_btn.clicked.connect(self.test_pattern)
        test_btn_layout.addWidget(test_btn)
        test_btn_layout.addStretch()
        test_layout.addLayout(test_btn_layout)
        
        self.test_result_label = QLabel("")
        self.test_result_label.setStyleSheet("padding: 5px;")
        test_layout.addWidget(self.test_result_label)
        
        layout.addWidget(test_group)
        
        layout.addStretch()
        
        # 버튼들
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.cancel_edit)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 저장")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        save_btn.clicked.connect(self.save_pattern)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def load_patterns(self):
        """패턴 목록 로드"""
        patterns = self.pattern_manager.get_patterns(enabled_only=False)
        self.table.setRowCount(len(patterns))
        
        for i, p in enumerate(patterns):
            # 활성화 체크박스
            enabled_item = QTableWidgetItem()
            enabled_item.setCheckState(Qt.Checked if p.get('enabled', True) else Qt.Unchecked)
            enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, enabled_item)
            
            # 이름
            name_item = QTableWidgetItem(p.get('name', ''))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, name_item)
            
            # 패턴
            pattern_item = QTableWidgetItem(p.get('pattern', ''))
            pattern_item.setData(Qt.UserRole, p)  # 전체 데이터 저장
            pattern_item.setFlags(pattern_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 2, pattern_item)
            
            # 유형
            type_item = QTableWidgetItem(p.get('type', 'keyword'))
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, type_item)
            
            # 카테고리
            category_item = QTableWidgetItem(p.get('category', '사용자정의'))
            category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 4, category_item)
            
            # 위험도
            score = p.get('score', 8)
            # 기존 1-100 점수를 1-15로 변환 (호환성)
            if score > 15:
                score = max(1, min(15, score // 7))
            score_item = QTableWidgetItem(str(score))
            score_item.setFlags(score_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 5, score_item)
    
    def go_to_add_mode(self):
        """추가 모드로 전환"""
        self.editing_pattern = None
        self.clear_inputs()
        self.tab_widget.setCurrentIndex(1)
    
    def go_to_edit_mode(self):
        """수정 모드로 전환"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "선택 필요", "수정할 패턴을 선택하세요.")
            return
        
        row = selected_rows[0].row()
        pattern_item = self.table.item(row, 2)
        if pattern_item:
            pattern_data = pattern_item.data(Qt.UserRole)
            self.editing_pattern = pattern_data.get('pattern', '')
            
            # 입력 필드에 데이터 채우기
            self.name_input.setText(pattern_data.get('name', ''))
            self.pattern_input.setText(pattern_data.get('pattern', ''))
            
            # 유형 설정
            type_idx = 1 if pattern_data.get('type') == 'regex' else 0
            self.type_combo.setCurrentIndex(type_idx)
            
            # 카테고리 설정
            category = pattern_data.get('category', '사용자정의')
            idx = self.category_combo.findText(category)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setCurrentText(category)
            
            # 위험도 설정
            score = pattern_data.get('score', 8)
            if score > 15:
                score = max(1, min(15, score // 7))
            self.score_input.setValue(score)
            
            # 설명 설정
            self.desc_input.setPlainText(pattern_data.get('description', ''))
            
            self.tab_widget.setCurrentIndex(1)
    
    def clear_inputs(self):
        """입력 필드 초기화"""
        self.name_input.clear()
        self.pattern_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.category_combo.setCurrentIndex(0)
        self.score_input.setValue(8)
        self.desc_input.clear()
        self.test_input.clear()
        self.test_result_label.clear()
    
    def cancel_edit(self):
        """편집 취소"""
        self.editing_pattern = None
        self.clear_inputs()
        self.tab_widget.setCurrentIndex(0)
    
    def save_pattern(self):
        """패턴 저장 (추가 또는 수정)"""
        name = self.name_input.text().strip()
        pattern = self.pattern_input.text().strip()
        
        if not name or not pattern:
            QMessageBox.warning(self, "입력 오류", "이름과 패턴을 모두 입력하세요.")
            return
        
        pattern_type = self.type_combo.currentText()
        category = self.category_combo.currentText().strip() or "사용자정의"
        score = self.score_input.value()
        description = self.desc_input.toPlainText().strip()
        
        # 정규식 유효성 검사
        if pattern_type == 'regex':
            try:
                re.compile(pattern)
            except re.error as e:
                QMessageBox.warning(self, "정규식 오류", f"잘못된 정규식입니다:\n{e}")
                return
        
        # 수정 모드인 경우 기존 패턴 삭제
        if self.editing_pattern:
            self.pattern_manager.remove_pattern(self.editing_pattern)
        
        # 패턴 추가
        success = self.pattern_manager.add_pattern(
            name=name,
            pattern=pattern,
            pattern_type=pattern_type,
            description=description,
            score=score,
            category=category
        )
        
        if success:
            action = "수정" if self.editing_pattern else "추가"
            QMessageBox.information(self, "성공", f"패턴 '{name}'이(가) {action}되었습니다.")
            self.editing_pattern = None
            self.clear_inputs()
            self.load_patterns()
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "실패", "패턴 저장에 실패했습니다.\n(중복이거나 잘못된 정규식)")
    
    def delete_selected(self):
        """선택된 패턴 삭제"""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "선택 필요", "삭제할 패턴을 선택하세요.")
            return
        
        row = selected_rows[0].row()
        pattern_item = self.table.item(row, 2)
        name_item = self.table.item(row, 1)
        
        if pattern_item and name_item:
            reply = QMessageBox.question(
                self, "삭제 확인",
                f"'{name_item.text()}' 패턴을 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                pattern_data = pattern_item.data(Qt.UserRole)
                self.pattern_manager.remove_pattern(pattern_data.get('pattern', ''))
                self.load_patterns()
    
    def toggle_selected(self):
        """선택된 패턴 활성화/비활성화"""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "선택 필요", "토글할 패턴을 선택하세요.")
            return
        
        row = selected_rows[0].row()
        pattern_item = self.table.item(row, 2)
        
        if pattern_item:
            pattern_data = pattern_item.data(Qt.UserRole)
            self.pattern_manager.toggle_pattern(pattern_data.get('pattern', ''))
            self.load_patterns()
    
    def test_pattern(self):
        """패턴 테스트"""
        pattern = self.pattern_input.text().strip()
        test_text = self.test_input.toPlainText().strip()
        
        if not pattern:
            self.test_result_label.setText("⚠️ 패턴을 먼저 입력하세요.")
            self.test_result_label.setStyleSheet("color: orange; padding: 5px;")
            return
        
        if not test_text:
            self.test_result_label.setText("⚠️ 테스트할 텍스트를 입력하세요.")
            self.test_result_label.setStyleSheet("color: orange; padding: 5px;")
            return
        
        pattern_type = self.type_combo.currentText()
        
        try:
            if pattern_type == 'regex':
                matches = re.findall(pattern, test_text)
            else:
                # 키워드 검색 (대소문자 무시) - 모든 매치 찾기
                text_lower = test_text.lower()
                pattern_lower = pattern.lower()
                matches = []
                start = 0
                while True:
                    pos = text_lower.find(pattern_lower, start)
                    if pos == -1:
                        break
                    matches.append(test_text[pos:pos+len(pattern)])
                    start = pos + 1
            
            if matches:
                unique_matches = list(set(matches))
                self.test_result_label.setText(
                    f"✅ {len(matches)}개 매치 발견: {', '.join(unique_matches[:5])}"
                    + ("..." if len(unique_matches) > 5 else "")
                )
                self.test_result_label.setStyleSheet("color: green; padding: 5px;")
            else:
                self.test_result_label.setText("❌ 매치되는 항목이 없습니다.")
                self.test_result_label.setStyleSheet("color: red; padding: 5px;")
                
        except re.error as e:
            self.test_result_label.setText(f"⚠️ 정규식 오류: {e}")
            self.test_result_label.setStyleSheet("color: red; padding: 5px;")
    
    def import_patterns(self):
        """패턴 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "패턴 파일 가져오기", "",
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            patterns = data if isinstance(data, list) else data.get('patterns', [])
            
            imported = 0
            for p in patterns:
                if isinstance(p, dict) and 'pattern' in p:
                    success = self.pattern_manager.add_pattern(
                        name=p.get('name', p.get('pattern', '')),
                        pattern=p.get('pattern', ''),
                        pattern_type=p.get('type', 'keyword'),
                        description=p.get('description', ''),
                        score=p.get('score', 8),
                        category=p.get('category', '사용자정의')
                    )
                    if success:
                        imported += 1
            
            QMessageBox.information(
                self, "가져오기 완료",
                f"{imported}개 패턴을 가져왔습니다."
            )
            self.load_patterns()
            
        except Exception as e:
            QMessageBox.warning(self, "가져오기 실패", f"파일을 읽을 수 없습니다:\n{e}")
    
    def export_patterns(self):
        """패턴 내보내기"""
        patterns = self.pattern_manager.get_patterns(enabled_only=False)
        
        if not patterns:
            QMessageBox.warning(self, "내보내기 실패", "내보낼 패턴이 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "패턴 파일 내보내기", "user_patterns_export.json",
            "JSON 파일 (*.json);;모든 파일 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            export_data = {
                "patterns": patterns,
                "version": "2.1"
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self, "내보내기 완료",
                f"{len(patterns)}개 패턴을 내보냈습니다.\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.warning(self, "내보내기 실패", f"파일을 저장할 수 없습니다:\n{e}")
