"""
검증기 테스트 스크립트 v2
- 주민등록번호 체크섬 검증
- 카드번호 Luhn 검증
- 외국인등록번호 체크섬 검증
- 계좌번호 은행별 형식 + 컨텍스트 검증
"""
from validators.rrn_validator import RRNValidator
from validators.card_validator import CardValidator
from validators.foreigner_validator import ForeignerRRNValidator
from validators.account_validator import AccountValidator
from validators.passport_validator import PassportValidator
from validators.driver_license_validator import DriverLicenseValidator


def test_rrn():
    print("=" * 70)
    print("주민등록번호 검증 테스트")
    print("=" * 70)
    
    validator = RRNValidator()
    
    test_cases = [
        ("900101-1234567", "1990년생 - 체크섬 검증 대상"),
        ("850515-2345678", "1985년생 - 체크섬 검증 대상"),
        ("201015-3123456", "2020년 10월생 - 체크섬 무작위"),
        ("230101-4567890", "2023년생 - 체크섬 무작위"),
        ("901301-1234567", "잘못된 월 (13월)"),
    ]
    
    for value, desc in test_cases:
        basic_valid = validator.validate(value)
        
        if basic_valid:
            is_valid, info_type = validator.validate_full(value)
            checksum_applicable = validator.is_checksum_applicable(value)
            
            if checksum_applicable:
                checksum_valid = validator.verify_checksum(value)
                checksum_status = "✅ 통과" if checksum_valid else "❌ 실패"
            else:
                checksum_status = "⏭️ 스킵 (2020.10 이후)"
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | 체크섬: {checksum_status}")
            print(f"  결과: {info_type}")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


def test_foreigner():
    print("\n" + "=" * 70)
    print("외국인등록번호 검증 테스트")
    print("=" * 70)
    
    validator = ForeignerRRNValidator()
    
    test_cases = [
        ("900101-5234567", "1990년생 외국인 - 체크섬 검증 대상"),
        ("850515-6345678", "1985년생 외국인 - 체크섬 검증 대상"),
        ("201015-7123456", "2020년 10월생 외국인 - 체크섬 무작위"),
        ("900101-1234567", "성별코드 1 - 내국인 (제외)"),
    ]
    
    for value, desc in test_cases:
        basic_valid = validator.validate(value)
        
        if basic_valid:
            is_valid, info_type = validator.validate_full(value)
            checksum_applicable = validator.is_checksum_applicable(value)
            
            if checksum_applicable:
                checksum_valid = validator.verify_checksum(value)
                checksum_status = "✅ 통과" if checksum_valid else "❌ 실패"
            else:
                checksum_status = "⏭️ 스킵 (2020.10 이후)"
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | 체크섬: {checksum_status}")
            print(f"  결과: {info_type}")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


def test_card():
    print("\n" + "=" * 70)
    print("카드번호 검증 테스트")
    print("=" * 70)
    
    validator = CardValidator()
    
    test_cases = [
        ("4532015112830366", "VISA - Luhn 유효"),
        ("5425233430109903", "MasterCard - Luhn 유효"),
        ("4111111111111111", "VISA 테스트 - Luhn 유효"),
        ("1234567890123456", "임의 숫자 - Luhn 무효"),
        ("4532-0151-1283-0366", "하이픈 포함 - VISA"),
    ]
    
    for value, desc in test_cases:
        basic_valid = validator.validate(value)
        
        if basic_valid:
            is_valid, info_type = validator.validate_full(value)
            luhn_valid = validator.verify_luhn(value)
            luhn_status = "✅ 통과" if luhn_valid else "❌ 실패"
            brand = validator.get_card_brand(value)
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | Luhn: {luhn_status} | 브랜드: {brand}")
            print(f"  결과: {info_type}")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


def test_account():
    print("\n" + "=" * 70)
    print("계좌번호 검증 테스트 (은행별 체계)")
    print("=" * 70)
    
    validator = AccountValidator()
    
    test_cases = [
        # (값, 컨텍스트, 설명)
        ("110-123-456789", "신한은행 계좌번호입니다", "신한은행 12자리 + 컨텍스트 O"),
        ("3333-01-1234567", "카카오뱅크 입금계좌", "카카오뱅크 13자리 + 컨텍스트 O"),
        ("123-456-789012", "국민은행으로 이체해주세요", "KB국민은행 + 컨텍스트 O"),
        ("110-123-456789", "아무런 설명 없음", "12자리 + 컨텍스트 X"),
        ("12345678901234", "", "14자리 + 컨텍스트 X"),
        ("123-45-678901", "NH농협은행 계좌", "농협 13자리 + 컨텍스트 O"),
        ("1234567890", "", "10자리 - 너무 짧음"),
        ("123456789012345", "", "15자리 - 너무 김"),
    ]
    
    for value, context, desc in test_cases:
        basic_valid = validator.validate(value, context)
        
        if basic_valid:
            is_valid, info_type, confidence = validator.validate_full(value, context)
            has_context = validator.has_account_context(context)
            detected_bank = validator.detect_bank_from_context(context)
            possible_banks = validator.get_possible_banks(value)
            
            context_status = "✅ 있음" if has_context else "❌ 없음"
            bank_info = detected_bank if detected_bank else f"후보: {', '.join(possible_banks[:3])}"
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | 컨텍스트: {context_status} | 은행: {bank_info}")
            print(f"  결과: {info_type} (신뢰도: {confidence})")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


def test_passport():
    print("\n" + "=" * 70)
    print("여권번호 검증 테스트")
    print("=" * 70)
    
    validator = PassportValidator()
    
    test_cases = [
        ("M12345678", "일반여권 (M + 8자리)"),
        ("S98765432", "관용여권 (S + 8자리)"),
        ("D11223344", "외교관여권 (D + 8자리)"),
        ("PM1234567", "전자여권 (PM + 7자리)"),
        ("R12345678", "거주여권 (R + 8자리)"),
        ("G12345678", "긴급여권 (G + 8자리)"),
        ("X12345678", "잘못된 코드 (X)"),
        ("M1234567", "자릿수 부족 (8자리)"),
        ("M123456789", "자릿수 초과 (10자리)"),
        ("12345678M", "잘못된 형식 (숫자 먼저)"),
    ]
    
    for value, desc in test_cases:
        basic_valid = validator.validate(value)
        
        if basic_valid:
            is_valid, info_type = validator.validate_full(value)
            passport_type = validator.get_passport_type(value)
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | 여권종류: {passport_type}")
            print(f"  결과: {info_type}")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


def test_driver_license():
    print("\n" + "=" * 70)
    print("운전면허번호 검증 테스트")
    print("=" * 70)
    
    validator = DriverLicenseValidator()
    
    test_cases = [
        ("11-23-123456-78", "서울 2023년 발급 (하이픈 포함)"),
        ("112312345678", "서울 2023년 발급 (하이픈 없음)"),
        ("12-20-654321-00", "부산 2020년 발급"),
        ("28-24-111111-11", "세종 2024년 발급"),
        ("13-19-999999-99", "경기 2019년 발급"),
        ("99-23-123456-78", "잘못된 지역코드 (99)"),
        ("11-23-12345-78", "자릿수 부족 (11자리)"),
        ("11-23-1234567-78", "자릿수 초과 (13자리)"),
        ("1A-23-123456-78", "숫자 아닌 문자 포함"),
    ]
    
    for value, desc in test_cases:
        basic_valid = validator.validate(value)
        
        if basic_valid:
            is_valid, info_type = validator.validate_full(value)
            region = validator.get_region(value)
            issue_year = validator.get_issue_year(value)
            checksum_valid = validator.verify_checksum(value)
            checksum_status = "✅ 통과" if checksum_valid else "❌ 실패"
            
            print(f"\n{value} ({desc})")
            print(f"  형식: ✅ | 지역: {region} | 발급년도: {issue_year} | 체크디짓: {checksum_status}")
            print(f"  결과: {info_type}")
        else:
            print(f"\n{value} ({desc})")
            print(f"  형식: ❌ | 결과: 탐지 제외")


if __name__ == "__main__":
    test_rrn()
    test_foreigner()
    test_card()
    test_account()
    test_passport()
    test_driver_license()
    print("\n" + "=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)
