"""
검증기 기본 클래스

[역할]
- 공통 무효 패턴 필터링 (반복 숫자, 연속 숫자, 테스트 패턴)
- 공통 인터페이스 정의
"""
import re
from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """검증기 기본 클래스"""
    
    # =========================================================
    # 무효 패턴 (False Positive 방지)
    # =========================================================
    
    # 연속 숫자 패턴
    SEQUENTIAL_PATTERNS = [
        '0123456789',
        '1234567890',
        '123456789',
        '234567890',
        '012345678',
        '9876543210',
        '987654321',
        '876543210',
        '098765432',
    ]
    
    # 테스트/더미 패턴
    TEST_PATTERNS = [
        '123123123',
        '111222333',
        '333222111',
        '112233445',
        '998877665',
        '123321123',
        '111000111',
        '000111000',
        '101010101',
        '121212121',
        '123412341',
        '567856785',
        '123123123123',
        '456456456456',
    ]
    
    # 주민등록번호 테스트용 (흔히 사용되는 더미)
    RRN_TEST_PATTERNS = [
        '0000000000000',
        '1111111111111',
        '1234561234567',
        '9001011234567',
        '8001011234567',
        '7001011234567',
    ]
    
    # 카드번호 테스트용 
    CARD_TEST_PATTERNS = [
        '0000000000000000',
        '1111111111111111',
        '1234567890123456',
        '4111111111111111',  # Visa 테스트 카드
        '5500000000000004',  # MC 테스트 카드
        '378282246310005',   # Amex 테스트 카드
    ]
    
    def is_invalid_pattern(self, value: str) -> bool:
        """
        무효 패턴 여부 확인
        
        Args:
            value: 검증할 값 (하이픈 등 제거된 순수 숫자/문자열)
            
        Returns:
            True: 무효 패턴 (탐지에서 제외해야 함)
            False: 유효한 패턴 (검증 진행)
        """
        # 숫자만 추출
        digits_only = re.sub(r'[^0-9]', '', value)
        
        if not digits_only:
            return True  # 숫자가 없으면 무효
        
        if len(digits_only) < 6:
            return False  # 너무 짧으면 패턴 체크 스킵
        
        # 1. 모든 자리가 같은 숫자인지 확인 (000000, 1111111, ...)
        if len(set(digits_only)) == 1:
            return True
        
        # 2. 연속 숫자 패턴 확인
        for seq in self.SEQUENTIAL_PATTERNS:
            if digits_only == seq or (len(digits_only) >= 6 and digits_only in seq):
                return True
        
        # 3. 연속 증가/감소 패턴 직접 확인
        if self._is_sequential(digits_only):
            return True
        
        # 4. 테스트 패턴 확인
        if digits_only in self.TEST_PATTERNS:
            return True
        
        # 5. 2자리 반복 패턴 (121212, 565656, ...)
        if self._is_two_digit_repeat(digits_only):
            return True
        
        return False
    
    def _is_sequential(self, digits: str) -> bool:
        """연속 증가 또는 감소하는 숫자인지 확인"""
        if len(digits) < 6:
            return False
        
        # 연속 증가 확인
        is_ascending = True
        is_descending = True
        
        for i in range(1, len(digits)):
            curr = int(digits[i])
            prev = int(digits[i-1])
            
            # 증가 체크 (0 다음 1, 9 다음 0 허용)
            expected_next = (prev + 1) % 10
            if curr != expected_next:
                is_ascending = False
            
            # 감소 체크 (1 다음 0, 0 다음 9 허용)
            expected_prev = (prev - 1) % 10
            if curr != expected_prev:
                is_descending = False
            
            # 둘 다 아니면 조기 종료
            if not is_ascending and not is_descending:
                return False
        
        return is_ascending or is_descending
    
    def _is_two_digit_repeat(self, digits: str) -> bool:
        """2자리 반복 패턴 확인 (121212, 565656, ...)"""
        if len(digits) < 6:
            return False
        
        # 앞 2자리가 계속 반복되는지 확인
        pattern = digits[:2]
        if pattern[0] == pattern[1]:  # 11, 22 같은 건 이미 위에서 처리
            return False
        
        expected = pattern * (len(digits) // 2 + 1)
        return digits == expected[:len(digits)]
    
    def is_test_rrn(self, value: str) -> bool:
        """주민등록번호 테스트 패턴 확인"""
        normalized = re.sub(r'[^0-9]', '', value)
        
        # 일반 무효 패턴 확인
        if self.is_invalid_pattern(normalized):
            return True
        
        # 주민번호 특화 테스트 패턴
        if normalized in self.RRN_TEST_PATTERNS:
            return True
        
        # 앞 6자리가 000000, 111111 등인 경우
        if len(normalized) >= 6 and len(set(normalized[:6])) == 1:
            return True
        
        # 뒤 7자리가 0000000, 1111111 등인 경우
        if len(normalized) >= 13 and len(set(normalized[6:13])) == 1:
            return True
        
        # 뒤 7자리가 연속 숫자인 경우 (1234567, 7654321 등)
        if len(normalized) >= 13:
            back_7 = normalized[6:13]
            if self._is_sequential(back_7):
                return True
        
        return False
    
    def is_test_card(self, value: str) -> bool:
        """카드번호 테스트 패턴 확인"""
        normalized = re.sub(r'[^0-9]', '', value)
        
        # 일반 무효 패턴 확인
        if self.is_invalid_pattern(normalized):
            return True
        
        # 카드 테스트 패턴
        if normalized in self.CARD_TEST_PATTERNS:
            return True
        
        return False
    
    @abstractmethod
    def validate(self, value: str, context: str = "") -> bool:
        """
        기본 형식 검증
        
        Args:
            value: 검증할 값
            context: 주변 컨텍스트 (참고용)
            
        Returns:
            bool: 기본 형식이 맞으면 True
        """
        pass
