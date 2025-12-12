"""
계좌번호 검증기 (은행별 체계 반영)

[검증 전략]
- 탐지 단계: 형식만 검증 (무효 필터 미적용)
- 체크섬 단계: 전용 무효 필터 + 은행별 형식 + 과목코드 검증

[은행별 계좌번호 형식]
- 길이: 10~16자리
- 각 은행마다 고유한 형식 존재
- 컨텍스트(은행명)와 함께 검증 시 정확도 향상
"""
import re
from typing import Optional, Tuple, List, Dict, Any
from .base_validator import BaseValidator
from .bank_formats import BANK_ACCOUNT_FORMATS, get_valid_lengths_by_bank, get_banks_by_length


class AccountInvalidFilter:
    """
    계좌번호 전용 무효 필터
    - 체크섬(validate_full) 단계에서만 사용
    - 탐지(validate) 단계에서는 사용하지 않음
    """
    
    INVALID_PATTERNS = frozenset({
        '0000000000', '1111111111', '2222222222', '3333333333', '4444444444',
        '5555555555', '6666666666', '7777777777', '8888888888', '9999999999',
        '1234567890', '0123456789', '9876543210', '0987654321',
        '00000000000', '11111111111', '22222222222', '33333333333', '44444444444',
        '55555555555', '66666666666', '77777777777', '88888888888', '99999999999',
        '12345678901', '01234567890', '98765432109', '10987654321',
        '000000000000', '111111111111', '222222222222', '333333333333', '444444444444',
        '555555555555', '666666666666', '777777777777', '888888888888', '999999999999',
        '123456789012', '012345678901',
        '0000000000000', '1111111111111', '2222222222222', '3333333333333', '4444444444444',
        '5555555555555', '6666666666666', '7777777777777', '8888888888888', '9999999999999',
        '00000000000000', '11111111111111', '22222222222222', '33333333333333', '44444444444444',
        '55555555555555', '66666666666666', '77777777777777', '88888888888888', '99999999999999',
    })
    
    @classmethod
    def check(cls, account_number: str) -> Tuple[bool, Optional[str]]:
        """무효 여부 검사. Returns: (is_invalid, reason)"""
        if not account_number:
            return True, "빈 값"
        
        cleaned = account_number.replace('-', '').replace(' ', '')
        digits_only = re.sub(r'[^0-9]', '', cleaned)
        
        if len(digits_only) < 10 or len(digits_only) > 16:
            return True, f"길이 범위 이탈: {len(digits_only)}자리"
        
        if digits_only in cls.INVALID_PATTERNS:
            return True, f"무효 패턴: {digits_only}"
        
        if len(set(digits_only)) == 1:
            return True, "전체 동일 숫자"
        
        if re.search(r'(\d)\1{7,}', digits_only):
            return True, "동일 숫자 8자리 이상 반복"
        
        if cls._has_sequential_pattern(digits_only, 8):
            return True, "순차 패턴 8자리 이상"
        
        if cls._has_two_digit_repeat(digits_only, 8):
            return True, "2자리 반복 패턴"
        
        return False, None
    
    @classmethod
    def _has_sequential_pattern(cls, digits: str, min_length: int) -> bool:
        if len(digits) < min_length:
            return False
        asc_count = desc_count = 1
        for i in range(1, len(digits)):
            curr, prev = int(digits[i]), int(digits[i-1])
            if curr == (prev + 1) % 10:
                asc_count += 1
                if asc_count >= min_length:
                    return True
            else:
                asc_count = 1
            if curr == (prev - 1) % 10:
                desc_count += 1
                if desc_count >= min_length:
                    return True
            else:
                desc_count = 1
        return False
    
    @classmethod
    def _has_two_digit_repeat(cls, digits: str, min_length: int) -> bool:
        if len(digits) < min_length:
            return False
        pattern = digits[:2]
        if pattern[0] == pattern[1]:
            return False
        expected = pattern * (len(digits) // 2 + 1)
        return digits == expected[:len(digits)]


class SubjectCodeExtractor:
    """
    은행별 과목코드 추출기
    
    [설계 원칙]
    - 각 은행의 계좌번호 형식에서 과목코드 위치가 다름
    - 2자리 또는 3자리 과목코드 사용
    - 동일 은행도 길이에 따라 과목코드 위치가 다를 수 있음
    
    [형식 범례]
    - X: 지점코드/기관코드
    - Y: 과목코드 (계좌종류)
    - Z: 일련번호
    - C: 체크디짓
    - T: 업무구분
    """
    
    # 은행별 과목코드 추출 규칙: {길이: (시작인덱스, 코드길이)}
    EXTRACTION_RULES = {
        # 한국산업은행: 구계좌 XXX-YY-ZZZZZC (11자리) → 인덱스 3~4
        #              현행 YYY-ZZZZZZZ-C-XXX (14자리) → 인덱스 0~2
        '한국산업은행': {11: (3, 2), 14: (0, 3)},
        
        # IBK기업은행: XXX-YY-ZZZZZZ-C (12자리) → 인덱스 3~4
        'IBK기업은행': {12: (3, 2), 14: (9, 2)},
        
        # KB국민은행: XXX-YY-ZZZZ-ZZC (12자리) → 인덱스 3~4
        #            XXXXYY-ZZ-ZZZZZC (14자리) → 인덱스 4~5
        'KB국민은행': {12: (3, 2), 14: (4, 2)},
        
        # KEB하나은행: XXX-YY-ZZZZZ-C (11자리) → 인덱스 3~4
        #             YYY-ZZZZZZ-ZZC (12자리) → 인덱스 0~2
        #             XXX-ZZZZZZ-ZZCYY (14자리) → 인덱스 12~13
        'KEB하나은행': {11: (3, 2), 12: (0, 3), 14: (12, 2)},
        
        # 수협중앙회: XXX-YY-ZZZZZ-C (11자리) → 인덱스 3~4
        #           YYYZ-ZZZZ-ZZZC (12자리) → 인덱스 0~2
        '수협중앙회': {11: (3, 2), 12: (0, 3)},
        
        # NH농협은행: XXX-YY-ZZZZZC (11자리) → 인덱스 3~4
        #           YYY-ZZZZ-ZZZZ-CT (13자리) → 인덱스 0~2
        'NH농협은행': {11: (3, 2), 12: (4, 2), 13: (0, 3)},
        
        # 단위농협: YYY-ZZZZ-ZZZZ-CT (13자리) → 인덱스 0~2
        '단위농협': {13: (0, 3), 14: (6, 2)},
        
        # 우리은행: SYYY-CZZ-ZZZZZZ (13자리) → S=구분, YYY 인덱스 1~3
        '우리은행': {11: (3, 2), 12: (3, 2), 13: (1, 3), 14: (9, 2)},
        
        # SC제일은행: XXX-YY-ZZZZZC (11자리) → 인덱스 3~4
        'SC제일은행': {11: (3, 2), 14: (3, 2)},
        
        # 신한은행: YYY-ZZZ-ZZZZZC (12자리) → 인덱스 0~2
        '신한은행': {11: (3, 2), 12: (0, 3), 14: (0, 3)},
        
        # 한국씨티은행: XXX-ZZZZZ-YYC-ZZ (14자리) → 인덱스 8~9
        '한국씨티은행': {11: (3, 2), 14: (8, 2)},
        
        # 대구은행: XXX-YY-ZZZZZC (11자리) → 인덱스 3~4
        #          YYY-ZZ-ZZZZZZZC (12자리) → 인덱스 0~2
        '대구은행': {11: (3, 2), 12: (0, 3)},
        
        # 새마을금고: 9YYY-ZZZZ-ZZZZ-C (13자리) → 9=고정, YYY 인덱스 1~3
        '새마을금고': {13: (1, 3), 14: (4, 3)},
        
        # 케이뱅크: YYY-NNN-ZZZZZZ (12자리) → 인덱스 0~2
        '케이뱅크': {12: (0, 3)},
        
        # 카카오뱅크: TYYY-ZZ-ZZZZZZZ (13자리)
        # T=업무구분(3=일반,7=가상), YYY=과목코드 인덱스 1~3
        # 예: 3333... → YYY=333(입출금), 3388... → YYY=388(정기예금)
        '카카오뱅크': {13: (1, 3)},
        
        # 토스뱅크: YYYZ-ZZZZ-ZZZC (12자리) → 인덱스 0~2
        # 예: 100=입출금, 106=모으기, 190=토스머니
        '토스뱅크': {12: (0, 3)},
    }
    
    @classmethod
    def extract(cls, account_number: str, bank_name: str) -> Optional[str]:
        """계좌번호에서 과목코드 추출"""
        if bank_name not in cls.EXTRACTION_RULES:
            return None
        
        digits = re.sub(r'[-\s]', '', account_number)
        length = len(digits)
        rules = cls.EXTRACTION_RULES[bank_name]
        
        if length not in rules:
            return None
        
        start_idx, code_len = rules[length]
        if start_idx + code_len > length:
            return None
        
        return digits[start_idx:start_idx + code_len]


class SubjectCodeValidator:
    """과목코드 검증기"""
    
    @classmethod
    def validate(cls, subject_code: str, bank_name: str) -> Tuple[bool, Optional[str]]:
        """과목코드 유효성 검증. Returns: (is_valid, account_type)"""
        if not subject_code or bank_name not in BANK_ACCOUNT_FORMATS:
            return True, None
        
        bank_data = BANK_ACCOUNT_FORMATS[bank_name]
        subject_codes = bank_data.get('subject_codes', {})
        virtual_codes = bank_data.get('virtual_codes', [])
        extra_codes = bank_data.get('extra_codes', {})
        
        # 가상계좌 코드 확인
        if isinstance(virtual_codes, dict):
            for vtype, vcodes in virtual_codes.items():
                if cls._match_code(subject_code, vcodes):
                    return True, f"가상계좌({vtype})"
        elif isinstance(virtual_codes, list):
            if cls._match_code(subject_code, virtual_codes):
                return True, "가상계좌"
        
        # 일반 과목코드 확인
        for category, codes in subject_codes.items():
            if isinstance(codes, dict):
                for acc_type, type_codes in codes.items():
                    if cls._match_code(subject_code, type_codes):
                        return True, f"{category}_{acc_type}"
            else:
                if cls._match_code(subject_code, codes):
                    return True, category
        
        # 기타 과목코드 확인
        for extra_type, extra_codes_list in extra_codes.items():
            if cls._match_code(subject_code, extra_codes_list):
                return True, extra_type
        
        # 매칭되는 코드 없음 (형식은 맞을 수 있음)
        return False, None
    
    @classmethod
    def _match_code(cls, code: str, valid_codes) -> bool:
        if isinstance(valid_codes, str):
            return code == valid_codes
        elif isinstance(valid_codes, list):
            for vc in valid_codes:
                if isinstance(vc, str) and '~' in vc:
                    start, end = vc.split('~')
                    try:
                        if int(start) <= int(code) <= int(end):
                            return True
                    except ValueError:
                        pass
                elif code == str(vc):
                    return True
        return False


class AccountValidator(BaseValidator):
    """계좌번호 검증기 (은행별 체계 반영)"""
    
    BANK_KEYWORDS = {
        '산업은행': '한국산업은행', '산은': '한국산업은행', 'KDB': '한국산업은행',
        '기업은행': 'IBK기업은행', 'IBK': 'IBK기업은행', '중소기업은행': 'IBK기업은행',
        '국민은행': 'KB국민은행', 'KB': 'KB국민은행', '주택은행': 'KB국민은행',
        '하나은행': 'KEB하나은행', 'KEB': 'KEB하나은행', '외환은행': 'KEB하나은행',
        '신한은행': '신한은행', '신한': '신한은행', '조흥은행': '신한은행',
        '우리은행': '우리은행', '우리': '우리은행', '상업은행': '우리은행',
        '한일은행': '우리은행', '평화은행': '우리은행',
        'SC제일': 'SC제일은행', '제일은행': 'SC제일은행',
        '씨티은행': '한국씨티은행', '씨티': '한국씨티은행', '한미은행': '한국씨티은행',
        '대구은행': '대구은행', 'DGB': '대구은행',
        '부산은행': 'BNK부산은행', 'BNK': 'BNK부산은행',
        '농협': 'NH농협은행', 'NH': 'NH농협은행',
        '단위농협': '단위농협', '지역농협': '단위농협',
        '수협': '수협중앙회',
        '새마을금고': '새마을금고', '새마을': '새마을금고',
        '카카오뱅크': '카카오뱅크', '카카오': '카카오뱅크',
        '케이뱅크': '케이뱅크',
        '토스뱅크': '토스뱅크', '토스': '토스뱅크',
    }
    
    ACCOUNT_CONTEXT_KEYWORDS = [
        '계좌', '계좌번호', 'account', '입금', '송금', '이체', '출금',
        '은행', 'bank', '예금', '적금', '급여', '월급', '정산',
        '입금계좌', '출금계좌', '환불계좌', '급여계좌', '결제계좌',
        '보통예금', '저축예금', '자유저축', '정기예금', '정기적금',
    ]
    
    def validate(self, value: str, context: str = "") -> bool:
        """탐지 단계: 형식만 검증 (무효 필터 미적용)"""
        digits = re.sub(r'[-\s]', '', value)
        if len(digits) < 10 or len(digits) > 16:
            return False
        if not digits.isdigit():
            return False
        return True
    
    def detect_bank_from_context(self, context: str) -> str:
        """컨텍스트에서 은행명 추출"""
        context_lower = context.lower()
        for keyword, bank_name in self.BANK_KEYWORDS.items():
            if keyword.lower() in context_lower or keyword in context:
                return bank_name
        return ""
    
    def has_account_context(self, context: str) -> bool:
        """계좌번호 관련 컨텍스트 확인"""
        context_lower = context.lower()
        for keyword in self.ACCOUNT_CONTEXT_KEYWORDS:
            if keyword.lower() in context_lower or keyword in context:
                return True
        for keyword in self.BANK_KEYWORDS.keys():
            if keyword.lower() in context_lower or keyword in context:
                return True
        return False
    
    def validate_full(self, value: str, context: str = "") -> tuple:
        """
        체크섬 단계: 전용 무효 필터 + 은행별 형식 + 과목코드 검증
        
        ⭐ 실제 활용되는 메인 검증 메서드 (analyzer.py에서 호출)
        
        Returns:
            (is_valid, info_type, confidence)
            - (True, "계좌번호", "high"): 은행 형식 + 과목코드 모두 일치
            - (True, "계좌번호", "medium"): 은행 형식만 일치 또는 컨텍스트만 있음
            - (True, "계좌번호(의심)", "low"): 컨텍스트 없음
            - (False, "", ""): 형식 X 또는 무효 패턴
        """
        # 1. 기본 형식 검증
        if not self.validate(value, context):
            return False, "", ""
        
        digits = re.sub(r'[-\s]', '', value)
        
        # 2. 전용 무효 필터 적용
        is_invalid, reason = AccountInvalidFilter.check(digits)
        if is_invalid:
            return False, "", ""
        
        # 3. 컨텍스트 분석
        detected_bank = self.detect_bank_from_context(context)
        has_context = self.has_account_context(context)
        
        # 4. 은행별 검증 (은행명이 있는 경우)
        if detected_bank:
            # 4-1. 길이 검증
            valid_lengths = get_valid_lengths_by_bank(detected_bank)
            length_match = len(digits) in valid_lengths if valid_lengths else True
            
            if not length_match:
                # 길이 불일치 → 다른 은행일 수 있음 → medium
                return True, "계좌번호", "medium"
            
            # 4-2. 과목코드 추출 및 검증
            subject_code = SubjectCodeExtractor.extract(digits, detected_bank)
            
            if subject_code:
                code_valid, account_type = SubjectCodeValidator.validate(subject_code, detected_bank)
                
                if code_valid and account_type:
                    # 길이 + 과목코드 모두 일치 → high
                    return True, "계좌번호", "high"
                elif code_valid:
                    # 과목코드 형식은 맞지만 DB에 없음 → high (새 상품일 수 있음)
                    return True, "계좌번호", "high"
                else:
                    # 과목코드 불일치 → medium
                    return True, "계좌번호", "medium"
            else:
                # 과목코드 추출 실패 (규칙 없음) → 길이만 맞으면 high
                return True, "계좌번호", "high"
        
        # 5. 은행명 없이 컨텍스트만 있는 경우
        if has_context:
            return True, "계좌번호", "medium"
        
        # 6. 컨텍스트 없음 → 의심
        return True, "계좌번호(의심)", "low"
    
    def get_possible_banks(self, value: str) -> List[dict]:
        """계좌번호 길이로 가능한 은행 목록 반환"""
        digits = re.sub(r'[-\s]', '', value)
        return get_banks_by_length(len(digits))
    
    def analyze_account(self, value: str, context: str = "") -> Dict[str, Any]:
        """
        계좌번호 상세 분석 (디버깅/로깅용)
        
        Note: analyzer.py에서는 사용하지 않음. 독립 테스트용.
        """
        digits = re.sub(r'[-\s]', '', value)
        detected_bank = self.detect_bank_from_context(context)
        
        result = {
            'value': value,
            'digits': digits,
            'length': len(digits),
            'detected_bank': detected_bank,
            'is_valid_format': self.validate(value),
            'subject_code': None,
            'subject_code_valid': None,
            'account_type': None,
            'possible_banks': self.get_possible_banks(value),
        }
        
        # 무효 필터
        is_invalid, reason = AccountInvalidFilter.check(digits)
        result['is_invalid_pattern'] = is_invalid
        result['invalid_reason'] = reason
        
        if is_invalid:
            return result
        
        # 과목코드 분석
        if detected_bank:
            subject_code = SubjectCodeExtractor.extract(digits, detected_bank)
            result['subject_code'] = subject_code
            
            if subject_code:
                code_valid, account_type = SubjectCodeValidator.validate(subject_code, detected_bank)
                result['subject_code_valid'] = code_valid
                result['account_type'] = account_type
        
        return result


class IPValidator(BaseValidator):
    """IP 주소 기본 형식 검증기"""
    
    def validate(self, value: str, context: str = "") -> bool:
        parts = value.split('.')
        if len(parts) != 4:
            return False
        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            if all(int(p) == 0 for p in parts):
                return False
            return True
        except:
            return False
