"""
여권번호 검증기

[검증 전략]
- 한국 여권번호 형식 (총 9자리)
- 탐지 단계: 형식만 검증 (무효 필터 미적용)
- 체크섬 단계: 전용 무효 필터 적용

[여권번호 형식 - 3가지]
1. 기존 여권: 알파벳1 + 숫자8 (예: M12345678) - ~2021.12.20
2. 차세대 전자여권: 알파벳1 + 숫자3 + 알파벳1 + 숫자4 (예: M123A4567) - 2021.12.21~
3. 구형 (지역코드): 알파벳2 + 숫자7 (예: PM1234567) - 과거 형식

[여권 코드 체계]
- PM: 복수 여권 (Passport Multiple) - 가장 일반적
- PS: 단수 여권 (Passport Single) - 1회용
- PE: 긴급 여권 - 청색, 비전자, 12면
- PT: 여행증명서 - 검은색, 12면
- PZ: 난민용 여행증명서 - 법무부 발급

[첫 글자 의미]
- M: 일반여권 (가장 흔함)
- S: 관용여권
- D: 외교관여권
- R: 거주여권
- G: 긴급여권
- O: 관광취업여권

[체크섬]
- 여권번호 자체에는 체크섬 없음 (MRZ 영역은 별도)
"""
import re
from typing import Optional, Tuple
from .base_validator import BaseValidator


class PassportInvalidFilter:
    """
    여권번호 전용 무효 필터
    - 체크섬(validate_full) 단계에서만 사용
    - 탐지(validate) 단계에서는 사용하지 않음
    """
    
    # 레거시 형식 무효 숫자 패턴 (8자리)
    INVALID_LEGACY_PATTERNS = frozenset({
        '11111111', '22222222', '33333333', '44444444',
        '55555555', '66666666', '77777777', '88888888',
        '99999999', '00000000',
        '12345678', '23456789', '34567890',
        '87654321', '98765432', '09876543',
    })
    
    # 차세대/구형 형식 무효 숫자 패턴 (7자리)
    INVALID_7DIGIT_PATTERNS = frozenset({
        '1111111', '2222222', '3333333', '4444444',
        '5555555', '6666666', '7777777', '8888888',
        '9999999', '0000000',
        '1234567', '2345678', '3456789',
        '7654321', '8765432', '9876543',
    })
    
    @classmethod
    def check(cls, passport_number: str, format_type: str) -> Tuple[bool, Optional[str]]:
        """
        무효 여부 검사
        
        Args:
            passport_number: 여권번호 (정규화된 값)
            format_type: 'legacy', 'next_gen', 'old'
            
        Returns:
            (is_invalid, reason): (무효 여부, 무효 사유)
        """
        if not passport_number:
            return True, "빈 값"
        
        cleaned = passport_number.upper().replace('-', '').replace(' ', '')
        digits = re.sub(r'[^0-9]', '', cleaned)
        
        if format_type == 'legacy':
            # 레거시: M12345678 (알파벳1 + 숫자8)
            if len(digits) == 8:
                if digits in cls.INVALID_LEGACY_PATTERNS:
                    return True, f"무효 패턴: {digits}"
                # 동일 숫자 6자리 이상 연속
                if re.search(r'(\d)\1{5,}', digits):
                    return True, "동일 숫자 6자리 이상 반복"
                    
        elif format_type in ('next_gen', 'old'):
            # 차세대: M123A4567 (숫자 7자리)
            # 구형: PM1234567 (숫자 7자리)
            if len(digits) == 7:
                if digits in cls.INVALID_7DIGIT_PATTERNS:
                    return True, f"무효 패턴: {digits}"
                # 동일 숫자 5자리 이상 연속
                if re.search(r'(\d)\1{4,}', digits):
                    return True, "동일 숫자 5자리 이상 반복"
        
        return False, None


class PassportValidator(BaseValidator):
    """여권번호 검증기 (한국)"""
    
    # 여권 종류 코드 (첫 글자)
    VALID_TYPE_CODES = ['M', 'S', 'D', 'R', 'G', 'O', 'P']
    
    # 전자여권 두 번째 문자 코드
    # PM: 복수, PS: 단수, PE: 긴급, PT: 여행증명서, PZ: 난민용
    VALID_SECOND_CODES = ['M', 'S', 'E', 'T', 'Z']
    
    # 차세대 여권 중간 알파벳 (4번째 위치) - 일련번호 확장용
    # 실제로는 A~Z 전체 사용 가능 (단, I, O 제외 - 숫자와 혼동)
    NEXT_GEN_MIDDLE_CODES = [chr(i) for i in range(65, 91) if chr(i) not in ['I', 'O']]
    
    def validate(self, value: str, context: str = "") -> bool:
        """
        여권번호 기본 형식 검증 (탐지 단계)
        - 무효 필터 미적용 (순수 패턴 매칭만)
        """
        value = value.strip().upper()
        
        # 길이 체크 (9자리)
        if len(value) != 9:
            return False
        
        # =========================================================
        # 패턴 1: 기존 여권 - 알파벳1 + 숫자8 (예: M12345678)
        # =========================================================
        pattern_legacy = r'^[A-Z][0-9]{8}$'
        
        # =========================================================
        # 패턴 2: 차세대 전자여권 (2021.12.21~)
        # 알파벳1 + 숫자3 + 알파벳1 + 숫자4 (예: M123A4567)
        # =========================================================
        pattern_next_gen = r'^[A-Z][0-9]{3}[A-Z][0-9]{4}$'
        
        # =========================================================
        # 패턴 3: 구형 (지역코드) - 알파벳2 + 숫자7 (예: PM1234567)
        # =========================================================
        pattern_old = r'^[A-Z]{2}[0-9]{7}$'
        
        # 패턴 1: 기존 여권
        if re.match(pattern_legacy, value):
            if value[0] not in self.VALID_TYPE_CODES:
                return False
            return True
        
        # 패턴 2: 차세대 전자여권
        if re.match(pattern_next_gen, value):
            # 첫 글자: 여권 종류 코드
            if value[0] not in self.VALID_TYPE_CODES:
                return False
            # 4번째 글자: 중간 알파벳 (I, O 제외)
            if value[4] in ['I', 'O']:
                return False
            return True
        
        # 패턴 3: 구형 (PM, PS, PE 등)
        if re.match(pattern_old, value):
            # 첫 글자가 P인 경우: 두 번째 글자 확인
            if value[0] == 'P':
                if value[1] not in self.VALID_SECOND_CODES:
                    return False
                return True
            # 다른 조합도 허용 (예: SM, DM 등)
            if value[0] in self.VALID_TYPE_CODES:
                return True
            return False
        
        return False
    
    def _detect_format(self, value: str) -> str:
        """여권번호 형식 감지"""
        value = value.strip().upper()
        
        # 차세대: 알파벳1 + 숫자3 + 알파벳1 + 숫자4
        if re.match(r'^[A-Z][0-9]{3}[A-Z][0-9]{4}$', value):
            return 'next_gen'
        
        # 기존: 알파벳1 + 숫자8
        if re.match(r'^[A-Z][0-9]{8}$', value):
            return 'legacy'
        
        # 구형: 알파벳2 + 숫자7
        if re.match(r'^[A-Z]{2}[0-9]{7}$', value):
            return 'old'
        
        return 'unknown'
    
    def validate_full(self, value: str) -> tuple:
        """
        전체 검증 (체크섬 단계)
        - 전용 무효 필터 적용
        
        Returns:
            (is_valid, info_type)
            - (True, "여권번호"): 확정 (유효한 코드 + 형식 + 무효필터 통과)
            - (True, "여권번호(의심)"): 형식은 맞지만 코드 불확실
            - (False, ""): 형식 X 또는 무효 패턴
        """
        value = value.strip().upper()
        
        # 기본 형식 검증
        if not self.validate(value):
            return False, ""
        
        # 형식 감지
        passport_format = self._detect_format(value)
        
        # =========================================================
        # 전용 무효 필터 적용 (체크섬 단계에서만)
        # =========================================================
        is_invalid, reason = PassportInvalidFilter.check(value, passport_format)
        if is_invalid:
            return False, ""
        
        first_char = value[0]
        
        # 일반적인 여권 코드 (M, S, D, R, G, O, P)
        if first_char in self.VALID_TYPE_CODES:
            # 차세대 여권은 더 확실 (최신 형식)
            if passport_format == 'next_gen':
                return True, "여권번호"
            # 기존/구형도 유효한 코드면 확정
            return True, "여권번호"
        else:
            # 알 수 없는 코드
            return True, "여권번호(의심)"
    
    def get_passport_type(self, value: str) -> str:
        """여권 종류 반환"""
        value = value.strip().upper()
        
        if not self.validate(value):
            return ""
        
        first_char = value[0]
        passport_format = self._detect_format(value)
        
        # 기본 타입명
        type_names = {
            'M': '일반여권',
            'S': '관용여권',
            'D': '외교관여권',
            'R': '거주여권',
            'G': '긴급여권',
            'O': '관광취업여권',
            'P': '전자여권'
        }
        
        base_type = type_names.get(first_char, '기타')
        
        # 차세대 여권 표시
        if passport_format == 'next_gen':
            return f"{base_type}(차세대)"
        
        # 구형 PM, PS 등
        if passport_format == 'old' and first_char == 'P':
            second_char = value[1]
            old_type_names = {
                'M': '복수여권',
                'S': '단수여권',
                'E': '긴급여권',
                'T': '여행증명서',
                'Z': '난민용여행증명서'
            }
            return old_type_names.get(second_char, '전자여권')
        
        return base_type
    
    def get_format_info(self, value: str) -> dict:
        """여권번호 상세 정보 반환"""
        value = value.strip().upper()
        
        if not self.validate(value):
            return {}
        
        passport_format = self._detect_format(value)
        
        info = {
            'value': value,
            'format': passport_format,
            'type': self.get_passport_type(value),
            'first_code': value[0],
        }
        
        if passport_format == 'next_gen':
            info['description'] = '차세대 전자여권 (2021.12.21~)'
            info['middle_code'] = value[4]
        elif passport_format == 'legacy':
            info['description'] = '기존 여권 형식'
        elif passport_format == 'old':
            info['description'] = '구형 여권 형식 (지역코드 포함)'
            info['second_code'] = value[1]
        
        return info
