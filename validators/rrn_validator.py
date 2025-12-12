"""
주민등록번호 검증기

[검증 전략]
- 2020.10 이전 출생: 체크섬 검증 가능 → 실패 시 '의심'
- 2020.10 이후 출생: 체크섬 무작위 → 형식만 검증, '의심'으로 분류
"""
import re
from datetime import date
from .base_validator import BaseValidator


class RRNValidator(BaseValidator):
    """주민등록번호 검증기"""
    
    # 체크섬 가중치 (주민등록번호 검증 공식)
    CHECKSUM_WEIGHTS = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    
    # 체크섬 검증 기준일 (2020.10.01 이후 출생자는 체크섬 무작위)
    CHECKSUM_CUTOFF_DATE = date(2020, 10, 1)
    
    def validate(self, value: str, context: str = "") -> bool:
        """주민등록번호 기본 형식 검증"""
        digits = re.sub(r'[-\s]', '', value)
        
        # 길이 체크
        if len(digits) != 13:
            return False
        
        # 모두 숫자인지 확인
        if not digits.isdigit():
            return False
        
        # 생년월일 유효성 체크
        if not self._is_valid_date(digits):
            return False
        
        # 성별 코드 체크 (1-4, 5-8은 외국인)
        gender = int(digits[6])
        if gender not in [1, 2, 3, 4]:
            return False
        
        return True
    
    def _is_valid_date(self, digits: str) -> bool:
        """생년월일 유효성 검증"""
        try:
            year = int(digits[0:2])
            month = int(digits[2:4])
            day = int(digits[4:6])
            
            # 월 체크
            if month < 1 or month > 12:
                return False
            
            # 일 체크 (월별 최대 일수)
            max_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if day < 1 or day > max_days[month - 1]:
                return False
            
            return True
        except:
            return False
    
    def get_birth_date(self, digits: str) -> date:
        """주민번호에서 출생일 추출"""
        digits = re.sub(r'[-\s]', '', digits)
        
        year = int(digits[0:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
        gender = int(digits[6])
        
        # 성별코드로 세기 판단
        if gender in [1, 2, 5, 6]:
            year += 1900
        elif gender in [3, 4, 7, 8]:
            year += 2000
        else:
            year += 1800  # 0, 9는 1800년대 (거의 없음)
        
        return date(year, month, day)
    
    def verify_checksum(self, value: str) -> bool:
        """
        체크섬 검증 (13번째 자리 검증)
        
        공식: 11 - (Σ(각 자리 × 가중치) % 11) = 마지막 자리
        결과가 10이면 0, 11이면 1
        """
        digits = re.sub(r'[-\s]', '', value)
        
        if len(digits) != 13 or not digits.isdigit():
            return False
        
        try:
            total = 0
            for i in range(12):
                total += int(digits[i]) * self.CHECKSUM_WEIGHTS[i]
            
            remainder = total % 11
            check_digit = (11 - remainder) % 10
            
            return check_digit == int(digits[12])
        except:
            return False
    
    def is_checksum_applicable(self, value: str) -> bool:
        """
        체크섬 검증이 적용 가능한지 확인
        
        2020.10.01 이후 출생자는 체크섬이 무작위이므로 검증 불가
        """
        try:
            birth_date = self.get_birth_date(value)
            return birth_date < self.CHECKSUM_CUTOFF_DATE
        except:
            return False
    
    def validate_full(self, value: str) -> tuple:
        """
        전체 검증 (형식 + 체크섬)
        
        Returns:
            (is_valid, info_type)
            - (True, "주민등록번호"): 형식 O, 체크섬 O
            - (True, "주민등록번호(의심)"): 형식 O, 체크섬 X 또는 2020.10 이후
            - (False, ""): 형식 X 또는 무효 패턴 (000000, 111111, 123456789 등)
        """
        # 무효 패턴 필터 (000000, 111111, 123456789 등 더미 데이터만 제외)
        if self.is_test_rrn(value):
            return False, ""
        
        # 기본 형식 검증
        if not self.validate(value):
            return False, ""
        
        # 체크섬 적용 가능 여부 확인
        if self.is_checksum_applicable(value):
            # 2020.10 이전: 체크섬 검증
            if self.verify_checksum(value):
                return True, "주민등록번호"
            else:
                # 체크섬 실패 → 완전 제외
                return False, ""
        else:
            # 2020.10 이후: 체크섬 검증 불가, 형식만 통과하면 의심으로 분류
            return True, "주민등록번호(의심)"
