"""
운전면허번호 검증기

[검증 전략]
- 형식: 지역코드(2자리) + 년도(2자리) + 일련번호(6자리) + 체크디짓(2자리)
- 총 12자리 숫자 (하이픈 제외)
- 예: 11-23-123456-78 또는 1123123456-78
- 탐지 단계: 형식만 검증 (무효 필터 미적용)
- 체크섬 단계: 전용 무효 필터 + 체크디짓 검증
"""
import re
from typing import Optional, Tuple
from .base_validator import BaseValidator


class DriverLicenseInvalidFilter:
    """
    운전면허번호 전용 무효 필터
    - 체크섬(validate_full) 단계에서만 사용
    - 탐지(validate) 단계에서는 사용하지 않음
    """
    
    # 유효 지역코드 (11~28: 서울~세종)
    VALID_REGION_CODES = frozenset({11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28})
    
    # 무효 일련번호 패턴 (6자리)
    INVALID_SERIAL_PATTERNS = frozenset({
        '000000', '111111', '222222', '333333', '444444',
        '555555', '666666', '777777', '888888', '999999',
        '123456', '234567', '345678', '456789',
        '654321', '765432', '876543', '987654',
        '012345', '543210',
    })
    
    # 무효 전체 패턴 (12자리)
    INVALID_FULL_PATTERNS = frozenset({
        '000000000000', '111111111111', '222222222222',
        '333333333333', '444444444444', '555555555555',
        '666666666666', '777777777777', '888888888888',
        '999999999999', '123456789012', '012345678901',
        '210987654321', '109876543210',
    })
    
    @classmethod
    def check(cls, license_number: str) -> Tuple[bool, Optional[str]]:
        """
        무효 여부 검사
        
        Args:
            license_number: 운전면허번호 (하이픈 제거된 12자리)
            
        Returns:
            (is_invalid, reason): (무효 여부, 무효 사유)
        """
        if not license_number:
            return True, "빈 값"
        
        cleaned = license_number.replace('-', '').replace(' ', '')
        
        # 길이 검증 (12자리)
        if len(cleaned) != 12:
            return True, f"길이 불일치: {len(cleaned)}자리"
        
        # 모두 숫자인지 확인
        if not cleaned.isdigit():
            return True, "숫자가 아닌 문자 포함"
        
        # 전체 무효 패턴
        if cleaned in cls.INVALID_FULL_PATTERNS:
            return True, f"무효 패턴: {cleaned}"
        
        # 동일 숫자 10자리 이상 연속
        if re.search(r'(\d)\1{9,}', cleaned):
            return True, "동일 숫자 10자리 이상 반복"
        
        # 일련번호 부분 (4~9번째 자리) 무효 패턴
        serial = cleaned[4:10]
        if serial in cls.INVALID_SERIAL_PATTERNS:
            return True, f"무효 일련번호: {serial}"
        
        # 일련번호 동일 숫자 5자리 이상 연속
        if re.search(r'(\d)\1{4,}', serial):
            return True, "일련번호 동일 숫자 5자리 이상 반복"
        
        return False, None


class DriverLicenseValidator(BaseValidator):
    """운전면허번호 검증기 (한국)"""
    
    # 지역코드 (경찰청 코드)
    # 11: 서울, 12: 부산, 13: 경기(경기남부), 14: 강원, 15: 충북
    # 16: 충남, 17: 전북, 18: 전남, 19: 경북, 20: 경남
    # 21: 제주, 22: 대구, 23: 인천, 24: 광주, 25: 대전
    # 26: 울산, 28: 세종, 경기북부는 13 또는 별도 코드
    VALID_REGION_CODES = [
        11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 24, 25, 26, 28
    ]
    
    REGION_NAMES = {
        11: '서울', 12: '부산', 13: '경기', 14: '강원', 15: '충북',
        16: '충남', 17: '전북', 18: '전남', 19: '경북', 20: '경남',
        21: '제주', 22: '대구', 23: '인천', 24: '광주', 25: '대전',
        26: '울산', 28: '세종'
    }
    
    # 체크디짓 가중치 (앞 10자리에 적용)
    CHECKSUM_WEIGHTS = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3]
    
    def validate(self, value: str, context: str = "") -> bool:
        """
        운전면허번호 기본 형식 검증 (탐지 단계)
        - 무효 필터 미적용 (순수 패턴 매칭만)
        """
        # 하이픈, 공백 제거
        digits = re.sub(r'[-\s]', '', value)
        
        # 길이 체크 (12자리)
        if len(digits) != 12:
            return False
        
        # 모두 숫자인지 확인
        if not digits.isdigit():
            return False
        
        # 지역코드 유효성 (앞 2자리)
        region_code = int(digits[:2])
        if region_code not in self.VALID_REGION_CODES:
            return False
        
        # 년도 코드 범위 체크 (00~99)
        # 기본적으로 모든 2자리 허용 (유효한 년도 범위는 시대에 따라 변함)
        
        return True
    
    def verify_checksum(self, value: str) -> bool:
        """
        체크디짓 검증
        
        알고리즘:
        1. 앞 10자리에 가중치 [2,3,4,5,6,7,8,9,2,3]을 곱함
        2. 합계를 구함
        3. 합계 % 100 = 마지막 2자리 (체크디짓)
        
        주의: 이 알고리즘은 공개된 정보 기반이며, 
              실제 경찰청 알고리즘과 다를 수 있음
        """
        digits = re.sub(r'[-\s]', '', value)
        
        if len(digits) != 12 or not digits.isdigit():
            return False
        
        try:
            # 앞 10자리
            base_digits = [int(d) for d in digits[:10]]
            # 마지막 2자리 (체크디짓)
            check_digits = int(digits[10:12])
            
            # 가중치 적용 합계
            total = sum(d * w for d, w in zip(base_digits, self.CHECKSUM_WEIGHTS))
            
            # 체크디짓 계산
            calculated = total % 100
            
            return calculated == check_digits
        except:
            return False
    
    def validate_full(self, value: str) -> tuple:
        """
        전체 검증 (체크섬 단계)
        - 전용 무효 필터 적용 후 체크디짓 검증
        
        Returns:
            (is_valid, info_type)
            - (True, "운전면허번호"): 형식 O, 무효필터 통과, 체크섬 O
            - (True, "운전면허번호(의심)"): 형식 O, 무효필터 통과, 체크섬 X
            - (False, ""): 형식 X 또는 무효 패턴
        """
        # 기본 형식 검증
        if not self.validate(value):
            return False, ""
        
        digits = re.sub(r'[-\s]', '', value)
        
        # =========================================================
        # 전용 무효 필터 적용 (체크섬 단계에서만)
        # =========================================================
        is_invalid, reason = DriverLicenseInvalidFilter.check(digits)
        if is_invalid:
            return False, ""
        
        # 체크디짓 검증
        # 주의: 체크디짓 알고리즘이 공개되지 않아 정확도 보장 어려움
        # 따라서 체크섬 실패해도 '의심'으로 분류
        if self.verify_checksum(value):
            return True, "운전면허번호"
        else:
            # 체크섬 알고리즘이 정확하지 않을 수 있으므로
            # 형식만 맞으면 '의심'으로 분류
            return True, "운전면허번호(의심)"
    
    def get_region(self, value: str) -> str:
        """지역 정보 반환"""
        digits = re.sub(r'[-\s]', '', value)
        
        if len(digits) < 2:
            return ""
        
        try:
            region_code = int(digits[:2])
            return self.REGION_NAMES.get(region_code, '알 수 없음')
        except:
            return ""
    
    def get_issue_year(self, value: str) -> str:
        """발급 년도 추정 (2자리)"""
        digits = re.sub(r'[-\s]', '', value)
        
        if len(digits) < 4:
            return ""
        
        try:
            year_code = int(digits[2:4])
            # 00~30은 2000년대, 31~99는 1900년대로 추정
            # (실제로는 더 복잡할 수 있음)
            if year_code <= 30:
                return f"20{year_code:02d}"
            else:
                return f"19{year_code:02d}"
        except:
            return ""
    
    # ============================================================
    # CODEF API 검증 (고급 기능)
    # ============================================================
    
    def validate_with_api(
        self,
        value: str,
        name: str,
        birth_date: str,
        serial_number: str
    ) -> tuple:
        """
        CODEF API를 통한 운전면허증 진위확인
        
        Args:
            value: 운전면허번호 (12자리)
            name: 성명
            birth_date: 생년월일 (YYYYMMDD)
            serial_number: 암호일련번호 (면허증 우측 하단 6자리)
            
        Returns:
            (success, result_type, details)
            - (True, "운전면허번호(API확인)", {...}): API 검증 성공, 진위 확인
            - (True, "운전면허번호(API불일치)", {...}): API 검증 성공, 정보 불일치
            - (False, "오류 메시지", {}): API 호출 실패
        """
        try:
            from core.config import Config
            from api.codef_client import CodefClient
            
            config = Config()
            
            # API 설정 확인
            if not config.is_codef_configured():
                return False, "CODEF API가 설정되지 않았습니다", {}
            
            # 클라이언트 생성
            client = CodefClient(
                client_id=config.get_codef_client_id(),
                client_secret=config.get_codef_client_secret(),
                is_production=config.get_codef_production()
            )
            
            # API 호출
            result = client.verify_driver_license(
                license_number=value,
                name=name,
                birth_date=birth_date,
                serial_number=serial_number
            )
            
            # 결과 파싱
            if result["success"]:
                if result["valid"]:
                    return True, "운전면허번호(API확인)", result
                else:
                    return True, "운전면허번호(API불일치)", result
            else:
                return False, result["message"], result
                
        except ImportError as e:
            return False, f"모듈 로드 실패: {str(e)}", {}
        except Exception as e:
            return False, f"API 오류: {str(e)}", {}
