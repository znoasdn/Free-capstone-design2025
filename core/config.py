"""
설정 관리 클래스
"""
from pathlib import Path
from PyQt5.QtCore import QSettings


class Config:
    """설정 관리 클래스"""
    
    def __init__(self):
        self.settings = QSettings('DocumentAnalyzer', 'Settings')
    
    def get_last_model(self) -> str:
        """마지막 사용 모델"""
        return self.settings.value('last_model', 'llama3.2:3b')
    
    def set_last_model(self, model: str):
        """마지막 사용 모델 저장"""
        self.settings.setValue('last_model', model)
    
    def get_last_directory(self) -> str:
        """마지막 사용 디렉토리"""
        return self.settings.value('last_directory', str(Path.home()))
    
    def set_last_directory(self, directory: str):
        """마지막 사용 디렉토리 저장"""
        self.settings.setValue('last_directory', directory)
    
    def get_auto_save(self) -> bool:
        """자동 저장 설정"""
        return self.settings.value('auto_save', False, type=bool)
    
    def set_auto_save(self, enabled: bool):
        """자동 저장 설정 저장"""
        self.settings.setValue('auto_save', enabled)
    
    def get_dark_mode(self) -> bool:
        """다크모드 설정"""
        return self.settings.value('dark_mode', False, type=bool)
    
    def set_dark_mode(self, enabled: bool):
        """다크모드 설정 저장"""
        self.settings.setValue('dark_mode', enabled)
    
    def get_custom_patterns(self) -> dict:
        """커스텀 패턴"""
        return self.settings.value('custom_patterns', {}, type=dict)
    
    def set_custom_patterns(self, patterns: dict):
        """커스텀 패턴 저장"""
        self.settings.setValue('custom_patterns', patterns)
    
    # ============================================================
    # CODEF API 설정 (고급 검증용)
    # ============================================================
    
    def get_codef_enabled(self) -> bool:
        """CODEF API 활성화 여부"""
        return self.settings.value('codef_enabled', False, type=bool)
    
    def set_codef_enabled(self, enabled: bool):
        """CODEF API 활성화 설정"""
        self.settings.setValue('codef_enabled', enabled)
    
    def get_codef_client_id(self) -> str:
        """CODEF 클라이언트 ID"""
        return self.settings.value('codef_client_id', '')
    
    def set_codef_client_id(self, client_id: str):
        """CODEF 클라이언트 ID 저장"""
        self.settings.setValue('codef_client_id', client_id)
    
    def get_codef_client_secret(self) -> str:
        """CODEF 클라이언트 시크릿"""
        return self.settings.value('codef_client_secret', '')
    
    def set_codef_client_secret(self, client_secret: str):
        """CODEF 클라이언트 시크릿 저장"""
        self.settings.setValue('codef_client_secret', client_secret)
    
    def get_codef_production(self) -> bool:
        """CODEF 운영환경 여부 (False: 개발, True: 운영)"""
        return self.settings.value('codef_production', False, type=bool)
    
    def set_codef_production(self, is_production: bool):
        """CODEF 운영환경 설정"""
        self.settings.setValue('codef_production', is_production)
    
    def is_codef_configured(self) -> bool:
        """CODEF API 설정 완료 여부"""
        return bool(
            self.get_codef_enabled() and
            self.get_codef_client_id() and
            self.get_codef_client_secret()
        )
