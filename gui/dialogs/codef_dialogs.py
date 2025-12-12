"""
CODEF API 관련 다이얼로그
- API 설정 다이얼로그
- 운전면허 진위확인 다이얼로그
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox,
    QMessageBox, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


class CodefSettingsDialog(QDialog):
    """CODEF API 설정 다이얼로그"""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("🔐 CODEF API 설정")
        self.setMinimumWidth(500)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 설명
        desc_label = QLabel(
            "CODEF API를 사용하면 운전면허증의 실제 진위를 확인할 수 있습니다.\n"
            "API 키는 https://codef.io 에서 발급받을 수 있습니다."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 활성화 체크박스
        self.chk_enabled = QCheckBox("CODEF API 활성화")
        layout.addWidget(self.chk_enabled)
        
        # API 키 입력 그룹
        key_group = QGroupBox("API 인증 정보")
        key_layout = QFormLayout()
        
        self.txt_client_id = QLineEdit()
        self.txt_client_id.setPlaceholderText("Client ID를 입력하세요")
        key_layout.addRow("Client ID:", self.txt_client_id)
        
        self.txt_client_secret = QLineEdit()
        self.txt_client_secret.setPlaceholderText("Client Secret을 입력하세요")
        self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addRow("Client Secret:", self.txt_client_secret)
        
        # 비밀번호 표시 체크박스
        self.chk_show_secret = QCheckBox("비밀번호 표시")
        self.chk_show_secret.toggled.connect(self.toggle_secret_visibility)
        key_layout.addRow("", self.chk_show_secret)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # 환경 설정
        env_group = QGroupBox("환경 설정")
        env_layout = QVBoxLayout()
        
        self.chk_production = QCheckBox("운영 환경 사용 (체크 해제 시 개발 환경)")
        env_layout.addWidget(self.chk_production)
        
        env_note = QLabel(
            "⚠️ 개발 환경: 테스트용 (무료)\n"
            "⚠️ 운영 환경: 실제 서비스용 (과금)"
        )
        env_note.setStyleSheet("color: gray; font-size: 11px;")
        env_layout.addWidget(env_note)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        # 경고 메시지
        warning_group = QGroupBox("⚠️ 주의사항")
        warning_layout = QVBoxLayout()
        warning_label = QLabel(
            "• API 검증 시 개인정보(운전면허번호, 성명, 생년월일)가 CODEF 서버로 전송됩니다.\n"
            "• 이는 경찰청 DB와 연동하여 진위를 확인하기 위함입니다.\n"
            "• 정보주체의 동의 없이 사용하면 개인정보보호법 위반이 될 수 있습니다.\n"
            "• API 호출당 과금이 발생할 수 있습니다."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #ff6b6b;")
        warning_layout.addWidget(warning_label)
        warning_group.setLayout(warning_layout)
        layout.addWidget(warning_group)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self.btn_test = QPushButton("🔗 연결 테스트")
        self.btn_test.clicked.connect(self.test_connection)
        btn_layout.addWidget(self.btn_test)
        
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("저장")
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def toggle_secret_visibility(self, checked: bool):
        """비밀번호 표시/숨김 토글"""
        if checked:
            self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.txt_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_settings(self):
        """설정 로드"""
        if self.config:
            self.chk_enabled.setChecked(self.config.get_codef_enabled())
            self.txt_client_id.setText(self.config.get_codef_client_id())
            self.txt_client_secret.setText(self.config.get_codef_client_secret())
            self.chk_production.setChecked(self.config.get_codef_production())
    
    def save_settings(self):
        """설정 저장"""
        if self.config:
            self.config.set_codef_enabled(self.chk_enabled.isChecked())
            self.config.set_codef_client_id(self.txt_client_id.text().strip())
            self.config.set_codef_client_secret(self.txt_client_secret.text().strip())
            self.config.set_codef_production(self.chk_production.isChecked())
            
            QMessageBox.information(self, "저장 완료", "CODEF API 설정이 저장되었습니다.")
            self.accept()
    
    def test_connection(self):
        """연결 테스트"""
        client_id = self.txt_client_id.text().strip()
        client_secret = self.txt_client_secret.text().strip()
        
        if not client_id or not client_secret:
            QMessageBox.warning(self, "입력 필요", "Client ID와 Client Secret을 입력해주세요.")
            return
        
        try:
            from api.codef_client import CodefClient
            
            client = CodefClient(
                client_id=client_id,
                client_secret=client_secret,
                is_production=self.chk_production.isChecked()
            )
            
            # 토큰 발급 테스트
            token = client.get_token()
            
            if token:
                QMessageBox.information(
                    self, 
                    "연결 성공", 
                    "✅ CODEF API 연결이 성공적으로 확인되었습니다.\n\n"
                    f"환경: {'운영' if self.chk_production.isChecked() else '개발'}"
                )
            else:
                QMessageBox.warning(self, "연결 실패", "토큰을 발급받지 못했습니다.")
                
        except Exception as e:
            QMessageBox.critical(
                self, 
                "연결 오류", 
                f"CODEF API 연결 중 오류가 발생했습니다:\n\n{str(e)}"
            )


class DriverLicenseVerifyDialog(QDialog):
    """운전면허 진위확인 다이얼로그"""
    
    def __init__(self, parent=None, license_number: str = ""):
        super().__init__(parent)
        self.license_number = license_number
        self.setWindowTitle("🔐 운전면허 진위확인")
        self.setMinimumWidth(450)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 경고 메시지
        warning_label = QLabel(
            "⚠️ 주의: 입력한 정보가 CODEF 서버로 전송됩니다.\n"
            "이는 경찰청 DB와 연동하여 진위를 확인하기 위함입니다."
        )
        warning_label.setStyleSheet(
            "background-color: #fff3cd; color: #856404; "
            "padding: 10px; border-radius: 5px;"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # 입력 폼
        form_group = QGroupBox("진위확인 정보 입력")
        form_layout = QFormLayout()
        
        # 운전면허번호 (읽기 전용)
        self.txt_license = QLineEdit(self.license_number)
        self.txt_license.setReadOnly(True)
        self.txt_license.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("운전면허번호:", self.txt_license)
        
        # 성명
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("면허증에 기재된 성명")
        form_layout.addRow("성명:", self.txt_name)
        
        # 생년월일
        self.txt_birth = QLineEdit()
        self.txt_birth.setPlaceholderText("YYYYMMDD (예: 19900101)")
        self.txt_birth.setMaxLength(8)
        form_layout.addRow("생년월일:", self.txt_birth)
        
        # 암호일련번호
        self.txt_serial = QLineEdit()
        self.txt_serial.setPlaceholderText("면허증 우측 하단 6자리")
        self.txt_serial.setMaxLength(6)
        form_layout.addRow("암호일련번호:", self.txt_serial)
        
        # 암호일련번호 안내
        serial_help = QLabel("※ 암호일련번호는 운전면허증 앞면 우측 하단에 있습니다.")
        serial_help.setStyleSheet("color: gray; font-size: 10px;")
        form_layout.addRow("", serial_help)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 진행률
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # 결과 표시
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setMaximumHeight(150)
        self.txt_result.setVisible(False)
        layout.addWidget(self.txt_result)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self.btn_verify = QPushButton("🔍 진위확인")
        self.btn_verify.clicked.connect(self.verify)
        self.btn_verify.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.btn_verify)
        
        self.btn_close = QPushButton("닫기")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def verify(self):
        """진위확인 실행"""
        # 입력 검증
        name = self.txt_name.text().strip()
        birth = self.txt_birth.text().strip()
        serial = self.txt_serial.text().strip()
        
        if not name:
            QMessageBox.warning(self, "입력 필요", "성명을 입력해주세요.")
            return
        
        if not birth or len(birth) != 8 or not birth.isdigit():
            QMessageBox.warning(self, "입력 오류", "생년월일을 YYYYMMDD 형식으로 입력해주세요.")
            return
        
        if not serial or len(serial) != 6:
            QMessageBox.warning(self, "입력 필요", "암호일련번호 6자리를 입력해주세요.")
            return
        
        # 진행 표시
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # 무한 로딩
        self.btn_verify.setEnabled(False)
        self.txt_result.setVisible(True)
        self.txt_result.setText("🔄 진위확인 중...")
        
        try:
            from validators.driver_license_validator import DriverLicenseValidator
            
            validator = DriverLicenseValidator()
            success, result_type, details = validator.validate_with_api(
                self.license_number,
                name,
                birth,
                serial
            )
            
            self.progress.setVisible(False)
            self.btn_verify.setEnabled(True)
            
            if success:
                if "API확인" in result_type:
                    self.txt_result.setStyleSheet("background-color: #d4edda; color: #155724;")
                    result_text = (
                        f"✅ 진위확인 결과: 정상\n\n"
                        f"운전면허번호: {self.license_number}\n"
                        f"성명: {name}\n"
                        f"상태: {details.get('message', '확인 완료')}"
                    )
                else:  # API불일치
                    self.txt_result.setStyleSheet("background-color: #f8d7da; color: #721c24;")
                    result_text = (
                        f"❌ 진위확인 결과: 불일치\n\n"
                        f"운전면허번호: {self.license_number}\n"
                        f"상태: {details.get('message', '정보 불일치')}\n\n"
                        f"입력한 정보가 실제 면허증과 일치하지 않습니다."
                    )
            else:
                self.txt_result.setStyleSheet("background-color: #fff3cd; color: #856404;")
                result_text = (
                    f"⚠️ 진위확인 실패\n\n"
                    f"오류: {result_type}\n\n"
                    f"API 설정을 확인하거나 다시 시도해주세요."
                )
            
            self.txt_result.setText(result_text)
            
        except Exception as e:
            self.progress.setVisible(False)
            self.btn_verify.setEnabled(True)
            self.txt_result.setStyleSheet("background-color: #f8d7da; color: #721c24;")
            self.txt_result.setText(f"❌ 오류 발생\n\n{str(e)}")
    
    def get_result(self) -> dict:
        """결과 반환"""
        return {
            "license_number": self.license_number,
            "name": self.txt_name.text().strip(),
            "birth_date": self.txt_birth.text().strip(),
            "serial_number": self.txt_serial.text().strip()
        }
