"""
카드번호 검증기

[검증 전략]
- 16자리 숫자 형식 검증
- Luhn 알고리즘으로 체크섬 검증
- 체크섬 실패 시 '의심'으로 분류
"""
import re
from .base_validator import BaseValidator


class CardValidator(BaseValidator):
    """카드번호 검증기"""
    
    def validate(self, value: str, context: str = "") -> bool:
        """카드번호 기본 형식 검증"""
        digits = re.sub(r'[-\s]', '', value)
        
        # 길이 체크 (15-16자리, AMEX는 15자리)
        if len(digits) < 15 or len(digits) > 16:
            return False
        
        # 모두 숫자인지 확인
        if not digits.isdigit():
            return False
        
        # 모든 숫자가 같은 경우 제외 (0000-0000-0000-0000)
        if len(set(digits)) == 1:
            return False
        
        # 연속 숫자 제외 (1234567890123456)
        if self._is_sequential(digits):
            return False
        
        return True
    
    def _is_sequential(self, digits: str) -> bool:
        """연속된 숫자인지 확인"""
        # 오름차순 연속
        ascending = ''.join(str(i % 10) for i in range(len(digits)))
        # 내림차순 연속
        descending = ''.join(str((10 - i) % 10) for i in range(len(digits)))
        
        return digits == ascending[:len(digits)] or digits == descending[:len(digits)]
    
    def verify_luhn(self, value: str) -> bool:
        """
        Luhn 알고리즘 검증 (카드번호 체크섬)
        
        1. 오른쪽부터 짝수 위치 숫자를 2배
        2. 2배한 값이 9보다 크면 9를 뺌
        3. 모든 숫자의 합이 10의 배수면 유효
        """
        digits = re.sub(r'[-\s]', '', value)
        
        if not digits.isdigit():
            return False
        
        try:
            total = 0
            for i, d in enumerate(reversed(digits)):
                n = int(d)
                if i % 2 == 1:  # 짝수 위치 (0-indexed에서 홀수)
                    n *= 2
                    if n > 9:
                        n -= 9
                total += n
            
            return total % 10 == 0
        except:
            return False
    
    def get_card_brand(self, value: str) -> str:
        """카드 브랜드 추정"""
        digits = re.sub(r'[-\s]', '', value)
        
        if not digits or len(digits) < 2:
            return "알 수 없음"
        
        # 첫 자리(들)로 브랜드 판단
        if digits.startswith('4'):
            return "VISA"
        elif digits.startswith(('51', '52', '53', '54', '55')):
            return "MasterCard"
        elif digits.startswith(('34', '37')):
            return "AMEX"
        elif digits.startswith('6'):
            return "Discover/UnionPay"
        elif digits.startswith(('35',)):
            return "JCB"
        elif digits.startswith(('9',)):
            return "국내전용"
        else:
            return "기타"
    
    def validate_full(self, value: str) -> tuple:
        """
        전체 검증 (형식 + Luhn)
        
        Returns:
            (is_valid, info_type)
            - (True, "카드번호"): 형식 O, Luhn O
            - (True, "카드번호(의심)"): 형식 O, Luhn X
            - (False, ""): 형식 X 또는 무효 패턴 (0000..., 1111..., 1234... 등)
        """
        # 무효 패턴 필터 (0000..., 1111..., 1234... 등 더미 데이터만 제외)
        if self.is_test_card(value):
            return False, ""
        
        # 기본 형식 검증
        if not self.validate(value):
            return False, ""
        
        # Luhn 체크섬 검증
        if self.verify_luhn(value):
            return True, "카드번호"
        else:
            # Luhn 실패 → 완전 제외
            return False, ""
