"""
검증기 패키지

[사용법 - analyzer.py에서]
    from validators import AccountValidator, PassportValidator, DriverLicenseValidator
    
    # 초기화
    self.account_validator = AccountValidator()
    
    # 체크섬 검증 (validate_full)
    is_valid, info_type, conf = self.account_validator.validate_full(value, context)

[디버깅/테스트용]
    from validators import SubjectCodeExtractor, SubjectCodeValidator
    from validators import BANK_ACCOUNT_FORMATS, get_banks_by_length
"""
from .base_validator import BaseValidator
from .rrn_validator import RRNValidator
from .foreigner_validator import ForeignerRRNValidator
from .phone_validator import PhoneValidator, MobileValidator
from .card_validator import CardValidator
from .account_validator import (
    AccountValidator,
    IPValidator,
    AccountInvalidFilter,
    SubjectCodeExtractor,
    SubjectCodeValidator,
)
from .passport_validator import PassportValidator, PassportInvalidFilter
from .driver_license_validator import DriverLicenseValidator, DriverLicenseInvalidFilter
from .bank_formats import BANK_ACCOUNT_FORMATS, get_valid_lengths_by_bank, get_banks_by_length

__all__ = [
    # ============================================
    # 메인 Validators (analyzer.py에서 사용)
    # ============================================
    'BaseValidator',
    'RRNValidator',
    'ForeignerRRNValidator',
    'PhoneValidator',
    'MobileValidator',
    'CardValidator',
    'AccountValidator',
    'IPValidator',
    'PassportValidator',
    'DriverLicenseValidator',
    
    # ============================================
    # 무효 필터 (내부 사용, 테스트용 export)
    # ============================================
    'AccountInvalidFilter',
    'PassportInvalidFilter',
    'DriverLicenseInvalidFilter',
    
    # ============================================
    # 계좌번호 상세 검증 (디버깅/테스트용)
    # ============================================
    'SubjectCodeExtractor',
    'SubjectCodeValidator',
    'BANK_ACCOUNT_FORMATS',
    'get_valid_lengths_by_bank',
    'get_banks_by_length',
]
