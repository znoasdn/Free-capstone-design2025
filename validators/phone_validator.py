"""
전화번호 검증기 (간소화 버전)

[새로운 접근]
- 정규식은 "의심"만 표시 (analyzer.py의 SuspiciousPatternDetector가 담당)
- 이 파일은 호환성 유지를 위한 기본 검증만 제공
- 실제 분류는 LLM이 담당
"""

import re
from typing import List


class BaseValidator:
    """검증기 기본 인터페이스"""
    def validate(self, value: str, context: str = "") -> bool:
        raise NotImplementedError


class PhoneValidator(BaseValidator):
    """전화번호 기본 검증기 (간단 버전)"""
    
    VALID_PREFIXES = [
        '02', '031', '032', '033', '041', '042', '043', '044',
        '051', '052', '053', '054', '055', '061', '062', '063', '064',
        '070',  # 인터넷전화
    ]
    
    def validate(self, value: str, context: str = "") -> bool:
        """전화번호 기본 검증"""
        digits = re.sub(r'[-\s]', '', value)
        
        # 길이 체크
        if len(digits) < 9 or len(digits) > 11:
            return False
        
        # 접두사 체크
        return any(digits.startswith(prefix) for prefix in self.VALID_PREFIXES)


class MobileValidator(BaseValidator):
    """휴대전화 기본 검증기 (간단 버전)"""
    
    VALID_PREFIXES = ['010', '011', '016', '017', '018', '019']
    
    def validate(self, value: str, context: str = "") -> bool:
        """휴대전화 기본 검증"""
        digits = re.sub(r'[-\s]', '', value)
        
        # 길이 체크 (10-11자리)
        if len(digits) < 10 or len(digits) > 11:
            return False
        
        # 접두사 체크
        return any(digits.startswith(prefix) for prefix in self.VALID_PREFIXES)


# ========================================
# 레거시 호환성 함수
# ========================================

def detect_phone_numbers(text: str) -> List[str]:
    """
    레거시 함수 (호환성 유지)
    
    주의: 새로운 시스템에서는 analyzer.py의 
    SuspiciousPatternDetector를 사용하세요.
    """
    # 간단한 정규식
    pattern = re.compile(r'(?<!\d)0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}(?!\d)')
    
    detected = []
    phone_validator = PhoneValidator()
    mobile_validator = MobileValidator()
    
    for match in pattern.finditer(text):
        number = match.group()
        if phone_validator.validate(number) or mobile_validator.validate(number):
            detected.append(number)
    
    return detected


if __name__ == "__main__":
    # 간단 테스트
    test_cases = [
        "010-1234-5678",
        "02-123-4567",
        "031-987-6543",
        "999-9999-9999",  # 무효
    ]
    
    print("=" * 50)
    print("전화번호 검증 테스트")
    print("=" * 50)
    
    mobile = MobileValidator()
    phone = PhoneValidator()
    
    for test in test_cases:
        is_mobile = mobile.validate(test)
        is_phone = phone.validate(test)
        
        if is_mobile:
            result = "✓ 휴대전화"
        elif is_phone:
            result = "✓ 일반전화"
        else:
            result = "✗ 무효"
        
        print(f"{test:20} → {result}")
    
    print("\n" + "=" * 50)
    print("검출 테스트")
    print("=" * 50)
    
    test_text = "연락처: 010-1234-5678, 사무실: 02-123-4567"
    detected = detect_phone_numbers(test_text)
    print(f"검출된 번호: {detected}")
