"""
계좌번호 검증 테스트 - 실제 활용 흐름 검증

테스트 목표:
1. analyzer.py의 _validate_with_context()와 동일한 호출 방식 검증
2. 과목코드 검증이 실제로 confidence에 반영되는지 확인
3. 은행별 형식 + 과목코드 조합 검증
"""
import sys
sys.path.insert(0, '.')

from validators import (
    AccountValidator,
    AccountInvalidFilter,
    SubjectCodeExtractor,
    SubjectCodeValidator,
    get_banks_by_length,
)


def test_analyzer_integration():
    """
    analyzer.py의 _validate_with_context()와 동일한 호출 방식 테스트
    
    analyzer.py에서의 호출:
        is_valid, detected_type, conf = self.account_validator.validate_full(value, context)
    """
    print("=" * 70)
    print("1. analyzer.py 통합 테스트 (validate_full 호출)")
    print("=" * 70)
    
    validator = AccountValidator()
    
    test_cases = [
        # (계좌번호, 컨텍스트, 예상_confidence, 설명)
        
        # 카카오뱅크: 13자리, 과목코드 333 (입출금)
        ("3330100123456", "카카오뱅크 계좌입니다", "high", "카카오뱅크 + 과목코드 333 일치"),
        ("3880100123456", "카카오뱅크 정기예금", "high", "카카오뱅크 + 과목코드 388 일치"),
        ("9990100123456", "카카오뱅크 계좌", "medium", "카카오뱅크 + 과목코드 999 불일치"),
        
        # 토스뱅크: 12자리, 과목코드 100 (입출금)
        ("100012345678", "토스뱅크로 입금", "high", "토스뱅크 + 과목코드 100 일치"),
        ("190012345678", "토스뱅크 토스머니", "high", "토스뱅크 + 과목코드 190 일치"),
        
        # 케이뱅크: 12자리, 과목코드 100 (입출금)
        ("100123456789", "케이뱅크 계좌", "high", "케이뱅크 + 과목코드 100 일치"),
        
        # KB국민은행: 14자리
        ("01012345678901", "국민은행 급여계좌", "high", "KB국민은행 + 과목코드 01 일치"),
        
        # 컨텍스트만 있고 은행명 없음
        ("12345678901234", "급여 입금 계좌입니다", "medium", "컨텍스트만 있음"),
        
        # 컨텍스트 없음
        ("98765432101234", "", "low", "컨텍스트 없음 → 의심"),
        
        # 무효 패턴
        ("11111111111111", "국민은행 계좌", "", "무효 패턴 → 실패"),
        ("12345678901234", "국민은행 계좌", "medium", "순차 아님, 형식만 통과"),
    ]
    
    for value, context, expected_conf, desc in test_cases:
        is_valid, info_type, confidence = validator.validate_full(value, context)
        
        # 결과 판정
        if expected_conf == "":
            success = not is_valid
        else:
            success = (confidence == expected_conf)
        
        status = "✓" if success else "✗"
        
        print(f"\n{status} {desc}")
        print(f"   입력: {value} | 컨텍스트: '{context[:30]}...' " if len(context) > 30 else f"   입력: {value} | 컨텍스트: '{context}'")
        print(f"   결과: valid={is_valid}, type={info_type}, confidence={confidence}")
        print(f"   예상: confidence={expected_conf}")


def test_subject_code_flow():
    """과목코드 추출 → 검증 흐름 테스트"""
    print("\n" + "=" * 70)
    print("2. 과목코드 추출 → 검증 흐름")
    print("=" * 70)
    
    test_cases = [
        # (계좌번호, 은행명, 예상_과목코드, 예상_계좌종류)
        ("3330100123456", "카카오뱅크", "333", "입출금"),
        ("3880100123456", "카카오뱅크", "388", "정기예금"),
        ("7770100123456", "카카오뱅크", "777", "가상계좌"),  # mini
        ("100012345678", "토스뱅크", "100", "입출금"),
        ("190012345678", "토스뱅크", "190", "토스머니"),
        ("100123456789", "케이뱅크", "100", "입출금"),
    ]
    
    for value, bank, expected_code, expected_type in test_cases:
        # 1. 과목코드 추출
        code = SubjectCodeExtractor.extract(value, bank)
        code_match = (code == expected_code)
        
        # 2. 과목코드 검증
        if code:
            is_valid, acc_type = SubjectCodeValidator.validate(code, bank)
            type_found = acc_type is not None
        else:
            is_valid, acc_type = False, None
            type_found = False
        
        status = "✓" if (code_match and type_found) else "✗"
        
        print(f"\n{status} {bank} - {value}")
        print(f"   과목코드: {code} (예상: {expected_code}) {'✓' if code_match else '✗'}")
        print(f"   계좌종류: {acc_type} (예상: {expected_type}) {'✓' if type_found else '✗'}")


def test_invalid_filter():
    """무효 필터 테스트"""
    print("\n" + "=" * 70)
    print("3. 무효 필터 테스트")
    print("=" * 70)
    
    test_cases = [
        ("11111111111", True, "동일 숫자"),
        ("12345678901", False, "순차 패턴 아님 (0이 중간에)"),
        ("01234567890", True, "순차 패턴"),
        ("12121212121", True, "2자리 반복"),
        ("11012345678", False, "정상 계좌"),
        ("3330100123456", False, "정상 (카카오뱅크)"),
    ]
    
    for value, expected_invalid, desc in test_cases:
        is_invalid, reason = AccountInvalidFilter.check(value)
        status = "✓" if is_invalid == expected_invalid else "✗"
        print(f"{status} {value} ({desc}): invalid={is_invalid}, reason={reason}")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n" + "=" * 70)
    print("4. 엣지 케이스")
    print("=" * 70)
    
    validator = AccountValidator()
    
    # 길이 불일치 (카카오뱅크는 13자리인데 12자리 입력)
    is_valid, info_type, conf = validator.validate_full("333010012345", "카카오뱅크 계좌")
    print(f"길이 불일치 (12자리 vs 카카오뱅크 13자리): conf={conf} (expected: medium)")
    
    # 알 수 없는 은행 + 컨텍스트
    is_valid, info_type, conf = validator.validate_full("12345678901234", "ABC은행 계좌입니다")
    print(f"알 수 없는 은행 + 계좌 컨텍스트: conf={conf} (expected: medium)")
    
    # 은행명만 있고 '계좌' 키워드 없음
    is_valid, info_type, conf = validator.validate_full("3330100123456", "카카오뱅크로 보내주세요")
    print(f"은행명만 있음 (계좌 키워드 없음): conf={conf} (expected: high - 은행명이 컨텍스트)")


def test_possible_banks():
    """길이별 가능한 은행 조회"""
    print("\n" + "=" * 70)
    print("5. 길이별 가능한 은행")
    print("=" * 70)
    
    for length in [11, 12, 13, 14]:
        banks = get_banks_by_length(length)
        bank_names = set(b['bank'] for b in banks)
        print(f"\n{length}자리: {len(bank_names)}개 은행")
        for name in sorted(bank_names)[:5]:
            print(f"  - {name}")
        if len(bank_names) > 5:
            print(f"  ... 외 {len(bank_names) - 5}개")


if __name__ == "__main__":
    test_analyzer_integration()
    test_subject_code_flow()
    test_invalid_filter()
    test_edge_cases()
    test_possible_banks()
    
    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)
