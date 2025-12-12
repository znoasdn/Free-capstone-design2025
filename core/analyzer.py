"""
LLM 기반 개인정보 분석기 (개인정보보호법 준수)
v2.1 - 민감정보 탐지 LLM 전환 버전

법적 분류 체계:
- 고유식별정보 (제24조): 주민등록번호, 여권번호, 운전면허번호, 외국인등록번호
- 민감정보 (제23조): 사상·신념, 노동조합·정당, 정치적 견해, 건강, 성생활 등 → LLM 판단
- 금융정보 (제34조의2): 계좌번호, 카드번호 (노출금지)
- 일반개인정보 (제2조): 전화번호, 이메일, 주소 등
- 사용자정의: 사용자가 추가한 커스텀 패턴
"""
import re
import json
import requests
from typing import List, Dict, Tuple, Optional
from utils.constants import (
    SENSITIVE_PATTERNS, OLLAMA_URL, OLLAMA_TAGS_URL, OLLAMA_TIMEOUT,
    SENSITIVE_KEYWORDS, CONFIDENTIAL_KEYWORDS, SEVERITY_WEIGHTS, INFO_LEGAL_CATEGORY,
    LEGAL_CATEGORY_DESCRIPTIONS, UNIQUE_IDENTIFIERS, EXPOSURE_PROHIBITED_INFO,
    CONTEXT_KEYWORDS
)
from utils.logger import logger
from core.recommendation_engine import SecurityRecommendationEngine
from validators.rrn_validator import RRNValidator
from validators.card_validator import CardValidator
from validators.foreigner_validator import ForeignerRRNValidator
from validators.account_validator import AccountValidator
from validators.passport_validator import PassportValidator
from validators.driver_license_validator import DriverLicenseValidator
# user_pattern_manager는 detect_user_patterns에서 지연 로딩


class LocalLLMAnalyzer:
    """LLM 분석 엔진 (개인정보보호법 기반 분류)"""
    
    # 탐지 우선순위 (법적 중요도 + 패턴 명확성 순서)
    PRIORITY_ORDER = [
        # 1순위: 고유식별정보 (제24조)
        "주민등록번호",
        "외국인등록번호",
        "여권번호",
        "운전면허번호",
        
        # 2순위: 명확한 형식
        "카드번호",
        "휴대전화",
        "전화번호",
        "이메일",
        
        # 3순위: 컨텍스트 검증 필요
        "계좌번호",
        "주소",
        "IP주소",
    ]
    
    def __init__(self, model_name: str = "llama3.2:3b", status_callback=None):
        self.model_name = model_name
        self.ollama_url = OLLAMA_URL
        self.recommendation_engine = SecurityRecommendationEngine()
        self.status_callback = status_callback
        self.sensitive_types = SENSITIVE_PATTERNS.copy()
        
        # 검증기 초기화
        self.rrn_validator = RRNValidator()
        self.card_validator = CardValidator()
        self.foreigner_validator = ForeignerRRNValidator()
        self.account_validator = AccountValidator()
        self.passport_validator = PassportValidator()
        self.driver_license_validator = DriverLicenseValidator()
    
    def _emit_status(self, message: str):
        """상태 메시지 전송"""
        if self.status_callback:
            self.status_callback(message)
    
    def add_custom_pattern(self, name: str, pattern: str) -> bool:
        """커스텀 패턴 추가"""
        try:
            re.compile(pattern)
            self.sensitive_types[name] = pattern
            return True
        except:
            return False
    
    def check_ollama_connection(self) -> Tuple[bool, str]:
        """Ollama 연결 확인"""
        try:
            response = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if response.status_code == 200:
                models = [m.get('name', '') for m in response.json().get('models', [])]
                if self.model_name in models:
                    return True, f"연결 성공: {self.model_name}"
                return False, f"모델 없음. 사용가능: {', '.join(models[:3])}"
            return False, "Ollama 서버 응답 없음"
        except:
            return False, "Ollama가 실행되지 않았습니다."
    
    def _is_overlapping(self, start1: int, end1: int, start2: int, end2: int) -> bool:
        """두 범위가 겹치는지 확인"""
        return not (end1 <= start2 or end2 <= start1)
    
    def _get_legal_category(self, info_type: str) -> str:
        """정보 유형의 법적 분류 반환"""
        return INFO_LEGAL_CATEGORY.get(info_type, "일반개인정보")
    
    def _is_exposure_prohibited(self, info_type: str) -> bool:
        """노출금지 정보 여부 확인 (제34조의2)"""
        return info_type in EXPOSURE_PROHIBITED_INFO

    # =========================================================================
    # 정규식 기반 탐지 (고유식별정보, 금융정보, 연락처)
    # =========================================================================
    
    def detect_sensitive_info_regex(self, text: str) -> List[Dict]:
        """정규식 기반 개인정보 탐지 (민감정보 제외)"""
        detected = []
        detected_ranges = []
        
        for info_type in self.PRIORITY_ORDER:
            pattern = self.sensitive_types.get(info_type)
            if not pattern:
                continue
            
            try:
                for match in re.finditer(
                    pattern, 
                    text, 
                    re.IGNORECASE if info_type == "주소" else 0
                ):
                    start = match.start()
                    end = match.end()
                    value = match.group().strip()
                    
                    # 중복 범위 체크
                    is_duplicate = False
                    for detected_start, detected_end, detected_type in detected_ranges:
                        if self._is_overlapping(start, end, detected_start, detected_end):
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        continue
                    
                    # 컨텍스트 추출
                    context_start = max(0, start - 100)
                    context_end = min(len(text), end + 100)
                    context = text[context_start:context_end].replace('\n', ' ')
                    
                    # 컨텍스트 기반 검증 (체크섬 포함)
                    has_context, confidence = self._validate_with_context(
                        info_type, value, context
                    )
                    
                    # 계좌번호는 컨텍스트 없으면 제외
                    if info_type == "계좌번호" and not has_context:
                        continue
                    
                    # 체크섬 실패 또는 컨텍스트 부족 시 type에 (의심) 추가
                    display_type = info_type
                    if confidence == 'medium' and info_type in ['주민등록번호', '외국인등록번호', '카드번호', '계좌번호']:
                        display_type = f"{info_type}(의심)"
                    elif confidence == 'low' and info_type == '계좌번호':
                        display_type = "계좌번호(의심)"
                    
                    legal_category = self._get_legal_category(info_type)
                    
                    detected.append({
                        'type': display_type,
                        'value': value,
                        'start': start,
                        'end': end,
                        'context': context,
                        'method': 'regex',
                        'confidence': confidence,
                        'legal_category': legal_category,
                        'exposure_prohibited': self._is_exposure_prohibited(info_type),
                        'has_context': has_context
                    })
                    detected_ranges.append((start, end, info_type))
                    
            except Exception as e:
                logger.error(f"패턴 매칭 오류 ({info_type}): {str(e)}")
                continue
        
        detected.sort(key=lambda x: x['start'])
        return detected
    
    def _validate_with_context(self, info_type: str, value: str, context: str) -> Tuple[bool, str]:
        """컨텍스트 키워드 기반 검증 (체크섬 검증 포함)"""
        context_lower = context.lower()
        
        # 주민등록번호: 체크섬 검증 적용
        if info_type == '주민등록번호':
            is_valid, detected_type = self.rrn_validator.validate_full(value)
            if is_valid:
                # 체크섬 통과 또는 2020.10 이후 → 'high'
                # 체크섬 실패 (의심) → 'medium'
                if '의심' in detected_type:
                    return True, 'medium'
                return True, 'high'
            return False, 'low'
        
        # 외국인등록번호: 체크섬 검증 적용
        if info_type == '외국인등록번호':
            is_valid, detected_type = self.foreigner_validator.validate_full(value)
            if is_valid:
                if '의심' in detected_type:
                    return True, 'medium'
                return True, 'high'
            return False, 'low'
        
        # 여권번호: 형식 검증
        if info_type == '여권번호':
            is_valid, detected_type = self.passport_validator.validate_full(value)
            if is_valid:
                if '의심' in detected_type:
                    return True, 'medium'
                return True, 'high'
            return False, 'low'
        
        # 운전면허번호: 형식 + 체크디짓 검증
        if info_type == '운전면허번호':
            is_valid, detected_type = self.driver_license_validator.validate_full(value)
            if is_valid:
                if '의심' in detected_type:
                    return True, 'medium'
                return True, 'high'
            return False, 'low'
        
        # 카드번호: Luhn 체크섬 검증 적용
        if info_type == '카드번호':
            is_valid, detected_type = self.card_validator.validate_full(value)
            if is_valid:
                if '의심' in detected_type:
                    return True, 'medium'
                return True, 'high'
            return False, 'low'
        
        if info_type == '이메일':
            return True, 'high'
        
        # 계좌번호: 은행별 형식 + 컨텍스트 검증
        if info_type == '계좌번호':
            is_valid, detected_type, conf = self.account_validator.validate_full(value, context)
            if is_valid:
                return True, conf
            return False, 'low'
        
        # 주소
        if info_type == '주소':
            keywords = CONTEXT_KEYWORDS.get('주소', [])
            for kw in keywords:
                if kw.lower() in context_lower:
                    return True, 'high'
            return False, 'medium'
        
        # 전화번호/휴대전화
        if info_type in ['전화번호', '휴대전화']:
            return False, 'high'
        
        if info_type == 'IP주소':
            return True, 'medium'
        
        return False, 'medium'

    # =========================================================================
    # 민감정보 탐지 (제23조) - LLM 기반
    # =========================================================================
    
    def _scan_sensitive_keywords(self, text: str) -> List[Dict]:
        """
        1차: 민감정보 키워드 스캔 (판단 없이 의심 구간만 추출)
        """
        suspects = []
        text_lower = text.lower()
        
        for category, keywords in SENSITIVE_KEYWORDS.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                pos = 0
                while True:
                    pos = text_lower.find(keyword_lower, pos)
                    if pos == -1:
                        break
                    
                    # 앞뒤 200자 컨텍스트
                    ctx_start = max(0, pos - 200)
                    ctx_end = min(len(text), pos + len(keyword) + 200)
                    
                    suspects.append({
                        'category': category,
                        'keyword': keyword,
                        'position': pos,
                        'end_position': pos + len(keyword),
                        'context': text[ctx_start:ctx_end],
                        'context_start': ctx_start
                    })
                    pos += 1
        
        if not suspects:
            return []
        
        # 중복/인접 구간 병합
        return self._merge_overlapping_contexts(suspects)
    
    def _merge_overlapping_contexts(self, suspects: List[Dict]) -> List[Dict]:
        """겹치거나 인접한 구간 병합"""
        if not suspects:
            return []
        
        # 위치 기준 정렬
        sorted_suspects = sorted(suspects, key=lambda x: x['position'])
        merged = []
        current = sorted_suspects[0].copy()
        current['categories'] = [current['category']]
        current['keywords'] = [current['keyword']]
        
        for item in sorted_suspects[1:]:
            # 200자 이내면 같은 구간으로 병합
            if item['position'] - current['end_position'] < 200:
                # 범위 확장
                current['end_position'] = max(current['end_position'], item['end_position'])
                # 카테고리/키워드 추가
                if item['category'] not in current['categories']:
                    current['categories'].append(item['category'])
                if item['keyword'] not in current['keywords']:
                    current['keywords'].append(item['keyword'])
                # 컨텍스트 확장
                new_ctx_end = min(len(item['context']) + item['context_start'], 
                                  item['position'] + len(item['keyword']) + 200)
                if new_ctx_end > current['context_start'] + len(current['context']):
                    # 컨텍스트 재계산 필요 시 나중에 처리
                    pass
            else:
                merged.append(current)
                current = item.copy()
                current['categories'] = [current['category']]
                current['keywords'] = [current['keyword']]
        
        merged.append(current)
        return merged
    
    def _verify_sensitive_with_llm(self, suspects: List[Dict], full_text: str) -> List[Dict]:
        """
        2차: LLM이 실제 민감정보인지 최종 판단
        """
        if not suspects:
            return []
        
        # 10개 초과시 배치 처리
        if len(suspects) > 10:
            results = []
            for i in range(0, len(suspects), 10):
                batch = suspects[i:i+10]
                batch_results = self._verify_sensitive_batch(batch, full_text)
                results.extend(batch_results)
            return results
        
        return self._verify_sensitive_batch(suspects, full_text)
    
    def _verify_sensitive_batch(self, suspects: List[Dict], full_text: str) -> List[Dict]:
        """배치 단위 LLM 검증"""
        
        # 검증할 구간 텍스트 생성
        contexts_text = "\n\n---\n\n".join([
            f"[구간 {i+1}]\n"
            f"발견된 키워드: {', '.join(s.get('keywords', [s.get('keyword', '')]))}\n"
            f"카테고리 힌트: {', '.join(s.get('categories', [s.get('category', '')]))}\n"
            f"내용:\n{s['context']}"
            for i, s in enumerate(suspects)
        ])
        
        prompt = f"""당신은 개인정보보호 전문가입니다. 
다음 텍스트 구간들이 개인정보보호법 제23조의 "민감정보"에 해당하는지 판단하세요.

【제23조 민감정보 정의】
"특정 개인에 관한" 다음 정보만 민감정보입니다:

1. 건강정보: 특정인의 질병, 진단명, 장애, 치료/투약 이력
   예) "환자 김OO, 진단명: 우울증" → 민감정보 O
   예) "우울증의 원인과 치료법" → 민감정보 X (일반 지식)

2. 사상·신념 (종교 포함): 특정인의 종교, 신앙, 종교활동
   예) "홍길동 과장은 기독교 신자이며 교회 집사입니다" → 민감정보 O
   예) "매주 일요일 예배에 참석" (특정인 문서) → 민감정보 O
   예) "기독교의 역사" → 민감정보 X (일반 지식)

3. 노동조합·정당: 특정인의 노조/정당 가입, 활동
   예) "김OO은 민주노총 조합원입니다" → 민감정보 O
   예) "노동조합의 역할" → 민감정보 X (일반 지식)

4. 정치적 견해: 특정인의 정치 성향, 지지 정당
   예) "박팀장은 국민의힘 지지자라고 밝혔다" → 민감정보 O
   예) "총선 결과 분석" → 민감정보 X (일반 뉴스)

5. 성생활: 특정인의 성적 지향, 성생활 정보

6. 범죄경력: 특정인의 전과, 수사/재판/구속 기록
   예) "피의자 최OO는 사기죄 전과 2범이다" → 민감정보 O

【민감정보가 아닌 경우 - 반드시 제외】
- 일반적인 의학/법률/종교 지식 설명
- 학습/연구 맥락의 내용
- 특정 개인과 연결되지 않는 단순 키워드

【중요】특정 개인의 이름, 직함, 또는 식별 가능한 정보와 함께 언급된 경우에만 민감정보입니다.

【검토 대상 구간들】
{contexts_text}

【출력 형식】
반드시 아래 JSON 형식으로만 응답하세요:
{{
  "results": [
    {{
      "index": 1,
      "is_sensitive": true,
      "type": "사상_신념",
      "value": "민감정보에 해당하는 실제 텍스트 발췌",
      "person_identifier": "개인 식별 근거",
      "reason": "판단 근거"
    }},
    {{
      "index": 2,
      "is_sensitive": false,
      "reason": "제외 사유"
    }}
  ]
}}

JSON만 출력하세요."""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=90
            )
            
            if response.status_code == 200:
                llm_response = response.json().get('response', '')
                result = self._parse_json(llm_response)
                
                if result and 'results' in result:
                    verified = []
                    for r in result['results']:
                        if r.get('is_sensitive', False):
                            idx = r.get('index', 1) - 1
                            if 0 <= idx < len(suspects):
                                suspect = suspects[idx]
                                
                                # 원본 텍스트에서 위치 찾기
                                value = r.get('value', suspect.get('keyword', ''))
                                pos = full_text.find(value)
                                if pos == -1:
                                    pos = suspect['position']
                                
                                verified.append({
                                    'type': r.get('type', suspect.get('categories', ['민감정보'])[0]),
                                    'value': value,
                                    'start': pos,
                                    'end': pos + len(value),
                                    'context': suspect['context'],
                                    'method': 'llm',
                                    'confidence': 'high',
                                    'legal_category': '민감정보',
                                    'exposure_prohibited': False,
                                    'person_identifier': r.get('person_identifier', ''),
                                    'reason': r.get('reason', '')
                                })
                    
                    logger.info(f"LLM 민감정보 검증: {len(suspects)}개 중 {len(verified)}개 확정")
                    return verified
                    
        except requests.exceptions.Timeout:
            logger.error("LLM 민감정보 검증 타임아웃")
        except Exception as e:
            logger.error(f"LLM 민감정보 검증 실패: {str(e)}")
        
        return []
    
    def detect_sensitive_info_v2(self, text: str) -> List[Dict]:
        """
        민감정보 탐지 v2: 순수 LLM 기반 (키워드 스캔 없음)
        
        문서를 청크로 나눠서 LLM에게 직접 민감정보 탐지 요청
        - 키워드에 의존하지 않고 LLM이 문맥을 이해하여 탐지
        - 개인정보보호법 제23조 민감정보 6가지 유형 탐지
        """
        if not text or len(text.strip()) < 50:
            return []
        
        self._emit_status("🔍 민감정보 탐지 중 (LLM 직접 분석)...")
        
        # 문서를 청크로 분할 (1500자 단위)
        chunks = self._split_text_into_chunks(text, chunk_size=1500, overlap=150)
        logger.info(f"문서를 {len(chunks)}개 청크로 분할")
        
        all_results = []
        for i, chunk_info in enumerate(chunks):
            self._emit_status(f"🤖 민감정보 분석 중... ({i+1}/{len(chunks)})")
            chunk_results = self._detect_sensitive_in_chunk_direct(
                chunk_info['text'], 
                chunk_info['start_offset'],
                i + 1,
                len(chunks),
                text  # 전체 텍스트 (위치 보정용)
            )
            all_results.extend(chunk_results)
        
        # 중복 제거 (오버랩 구간)
        deduplicated = self._deduplicate_sensitive_results(all_results)
        
        self._emit_status(f"✅ 민감정보 {len(deduplicated)}개 탐지 완료")
        logger.info(f"민감정보 탐지 완료: {len(deduplicated)}개")
        return deduplicated
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1500, overlap: int = 150) -> List[Dict]:
        """문서를 청크로 분할 (문장 경계 고려)"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # 문장 경계에서 자르기 시도
            if end < len(text):
                # 마지막 마침표, 줄바꿈 찾기
                last_break = max(
                    text.rfind('.', start + chunk_size // 2, end),
                    text.rfind('\n', start + chunk_size // 2, end),
                    text.rfind('。', start + chunk_size // 2, end),
                    text.rfind('?', start + chunk_size // 2, end),
                    text.rfind('!', start + chunk_size // 2, end)
                )
                if last_break > start + chunk_size // 2:
                    end = last_break + 1
            
            chunks.append({
                'text': text[start:end],
                'start_offset': start,
                'end_offset': end
            })
            
            # 다음 시작점 (오버랩 적용)
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def _detect_sensitive_in_chunk_direct(self, chunk: str, offset: int, 
                                           chunk_num: int, total_chunks: int,
                                           full_text: str) -> List[Dict]:
        """
        단일 청크에서 LLM으로 민감정보 직접 탐지 (키워드 스캔 없음)
        """
        prompt = f"""당신은 개인정보보호 전문가입니다.
아래 문서에서 개인정보보호법 제23조의 "민감정보"를 모두 찾아주세요.

【제23조 민감정보 - 6가지 유형】

1. 건강정보
   - 특정인의 질병, 진단명, 장애, 의료기록, 약물 복용, 건강상태, 검진결과
   - 예: "김OO 환자는 우울증 진단을 받았다", "당뇨 전단계 판정"

2. 사상·신념 (종교 포함)
   - 특정인의 종교, 신앙, 종교활동, 신앙고백, 종교적 직분
   - 예: "기독교 신자", "교회 집사", "매주 예배 참석", "불교 신자"

3. 노동조합·정당
   - 특정인의 노조 가입/활동, 정당 가입/탈퇴
   - 예: "민주노총 조합원", "OO당 당원", "노조 상담"

4. 정치적 견해
   - 특정인의 정치 성향, 지지 정당, 정치적 발언
   - 예: "국민의힘 지지", "진보 성향", "OO당을 지지한다고 발언"

5. 성생활
   - 특정인의 성적 지향, 성정체성, 성생활 정보
   - 예: "동성애자", "성소수자"

6. 범죄경력
   - 특정인의 전과, 수사/재판/구속 기록
   - 예: "전과 2범", "사기죄로 기소", "구속 수감 중"

【핵심 판단 기준】
✅ 민감정보인 경우:
- "특정 개인"(이름, 직함, 대명사 등)과 연결된 위 6가지 정보

❌ 민감정보가 아닌 경우:
- 일반적인 의학/법률/종교 지식 설명
- 특정 개인과 연결되지 않은 단순 용어

【필수 제외 - 테스트/더미 데이터】
다음 패턴이 포함된 데이터는 절대 탐지하지 마세요:
- 연속 숫자: 1234567, 123456, 0000000, 1111111
- 반복 숫자: 같은 숫자가 4회 이상 연속 (예: 1111, 0000)
- 명백한 테스트 값: 000000-0000000, 123456-1234567
- 샘플/예시 표기: "예)", "예시:", "sample", "test"와 함께 사용된 값

【분석 대상】 (청크 {chunk_num}/{total_chunks})
---
{chunk}
---

【출력 형식】
민감정보를 발견하면 아래 JSON으로 응답하세요.
발견하지 못하면 {{"results": []}}로 응답하세요.

{{
  "results": [
    {{
      "type": "건강정보",
      "value": "발견된 원문 텍스트 (그대로 복사)",
      "person": "해당되는 개인 (이름, 직함 등)",
      "reason": "판단 근거"
    }}
  ]
}}

type은 반드시 다음 중 하나: 건강정보, 사상_신념, 노동조합_정당, 정치적_견해, 성생활, 범죄경력

JSON만 출력하세요."""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                parsed = self._parse_json(response_text)
                
                if parsed and 'results' in parsed:
                    detected = []
                    for item in parsed['results']:
                        value = item.get('value', '')
                        if not value or len(value) < 2:
                            continue
                        
                        # 원문에서 정확한 위치 찾기
                        pos = chunk.find(value)
                        if pos == -1:
                            # 부분 매칭 시도
                            value_words = value.split()
                            for word in value_words:
                                if len(word) > 3:
                                    pos = chunk.find(word)
                                    if pos != -1:
                                        break
                        
                        if pos == -1:
                            pos = 0
                        
                        actual_start = offset + pos
                        actual_end = actual_start + len(value)
                        
                        info_type = item.get('type', '민감정보')
                        # 타입명 정규화
                        type_mapping = {
                            '건강정보': '건강정보',
                            '사상신념': '사상_신념',
                            '사상_신념': '사상_신념',
                            '사상·신념': '사상_신념',
                            '종교': '사상_신념',
                            '노동조합정당': '노동조합_정당',
                            '노동조합_정당': '노동조합_정당',
                            '노동조합': '노동조합_정당',
                            '정당': '노동조합_정당',
                            '정치적견해': '정치적_견해',
                            '정치적_견해': '정치적_견해',
                            '정치': '정치적_견해',
                            '성생활': '성생활',
                            '범죄경력': '범죄경력',
                            '범죄': '범죄경력'
                        }
                        info_type = type_mapping.get(info_type, info_type)
                        
                        # 컨텍스트 추출
                        ctx_start = max(0, pos - 50)
                        ctx_end = min(len(chunk), pos + len(value) + 50)
                        
                        detected.append({
                            'type': info_type,
                            'value': value[:100],  # 최대 100자
                            'start': actual_start,
                            'end': actual_end,
                            'context': chunk[ctx_start:ctx_end],
                            'legal_category': '민감정보',
                            'detection_method': 'llm_direct',
                            'person': item.get('person', ''),
                            'reason': item.get('reason', '')
                        })
                    
                    return detected
        
        except requests.exceptions.Timeout:
            logger.warning(f"청크 {chunk_num} LLM 타임아웃")
        except Exception as e:
            logger.warning(f"청크 {chunk_num} 민감정보 탐지 오류: {e}")
        
        return []
    
    def _apply_checksum_filter(self, detected_items: List[Dict]) -> List[Dict]:
        """
        결과 병합 후 체크섬 일괄 검증 (v2.2 추가)
        
        LLM이 탐지한 결과에서도 테스트 패턴/체크섬 실패 데이터를 제거
        - 주민등록번호, 외국인등록번호, 카드번호 패턴 추출 후 체크섬 검증
        - 테스트 패턴(1234567, 0000000 등) 제거
        """
        if not detected_items:
            return []
        
        filtered = []
        
        # 테스트 패턴 정규식
        test_patterns = [
            r'1234567',
            r'0000000',
            r'1111111',
            r'123456',
            r'000000',
            r'(\d)\1{3,}',  # 같은 숫자 4회 이상 반복
        ]
        
        # 주민등록번호/외국인등록번호 패턴 (YYMMDD-NNNNNNN)
        rrn_pattern = re.compile(r'\d{6}[\s-]?\d{7}')
        # 카드번호 패턴 (16자리)
        card_pattern = re.compile(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}')
        
        for item in detected_items:
            value = item.get('value', '')
            should_exclude = False
            
            # 1. 테스트 패턴 체크
            for pattern in test_patterns:
                if re.search(pattern, value):
                    should_exclude = True
                    logger.debug(f"테스트 패턴 제외: {value[:30]}...")
                    break
            
            if should_exclude:
                continue
            
            # 2. value 내 주민등록번호 패턴 추출 후 체크섬 검증
            rrn_matches = rrn_pattern.findall(value)
            for rrn in rrn_matches:
                # 공백/하이픈 제거
                rrn_clean = re.sub(r'[\s-]', '', rrn)
                if len(rrn_clean) == 13:
                    is_valid, _ = self.rrn_validator.validate_full(rrn_clean[:6] + '-' + rrn_clean[6:])
                    if not is_valid:
                        # 외국인등록번호로도 검증
                        is_valid_foreigner, _ = self.foreigner_validator.validate_full(rrn_clean[:6] + '-' + rrn_clean[6:])
                        if not is_valid_foreigner:
                            should_exclude = True
                            logger.debug(f"체크섬 실패 제외 (RRN): {rrn}")
                            break
            
            if should_exclude:
                continue
            
            # 3. value 내 카드번호 패턴 추출 후 Luhn 검증
            card_matches = card_pattern.findall(value)
            for card in card_matches:
                card_clean = re.sub(r'[\s-]', '', card)
                if len(card_clean) == 16:
                    is_valid, _ = self.card_validator.validate_full(card_clean)
                    if not is_valid:
                        should_exclude = True
                        logger.debug(f"Luhn 실패 제외 (Card): {card}")
                        break
            
            if should_exclude:
                continue
            
            filtered.append(item)
        
        excluded_count = len(detected_items) - len(filtered)
        if excluded_count > 0:
            logger.info(f"체크섬 필터로 {excluded_count}개 항목 제외")
        
        return filtered

    def _deduplicate_sensitive_results(self, results: List[Dict]) -> List[Dict]:
        """중복 결과 제거 (오버랩 구간 처리)"""
        if not results:
            return []
        
        # value 기준 중복 제거 + 위치 기준 중복 제거
        seen_values = set()
        deduplicated = []
        
        # 시작 위치로 정렬
        sorted_results = sorted(results, key=lambda x: x.get('start', 0))
        
        for item in sorted_results:
            value_key = item.get('value', '')[:50]  # 앞 50자로 중복 체크
            
            if value_key in seen_values:
                continue
            
            # 위치 겹침 확인
            is_overlapping = False
            for existing in deduplicated:
                overlap_start = max(item['start'], existing['start'])
                overlap_end = min(item['end'], existing['end'])
                overlap_len = max(0, overlap_end - overlap_start)
                
                item_len = item['end'] - item['start']
                if item_len > 0 and overlap_len / item_len > 0.5:
                    is_overlapping = True
                    break
            
            if not is_overlapping:
                seen_values.add(value_key)
                deduplicated.append(item)
        
        return deduplicated

    # =========================================================================
    # 기업기밀 탐지 (부정경쟁방지법) - LLM 기반
    # =========================================================================
    
    def _scan_confidential_keywords(self, text: str) -> List[Dict]:
        """1차: 기업기밀 키워드 스캔"""
        suspects = []
        text_lower = text.lower()
        
        for category, keywords in CONFIDENTIAL_KEYWORDS.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                pos = 0
                while True:
                    pos = text_lower.find(keyword_lower, pos)
                    if pos == -1:
                        break
                    
                    ctx_start = max(0, pos - 200)
                    ctx_end = min(len(text), pos + len(keyword) + 200)
                    
                    suspects.append({
                        'category': category,
                        'keyword': keyword,
                        'position': pos,
                        'end_position': pos + len(keyword),
                        'context': text[ctx_start:ctx_end],
                        'context_start': ctx_start
                    })
                    pos += 1
        
        if not suspects:
            return []
        
        return self._merge_overlapping_contexts(suspects)
    
    def _verify_confidential_with_llm(self, suspects: List[Dict], full_text: str) -> List[Dict]:
        """2차: LLM이 실제 기업기밀인지 판단"""
        if not suspects:
            return []
        
        if len(suspects) > 10:
            results = []
            for i in range(0, len(suspects), 10):
                batch = suspects[i:i+10]
                batch_results = self._verify_confidential_batch(batch, full_text)
                results.extend(batch_results)
            return results
        
        return self._verify_confidential_batch(suspects, full_text)
    
    def _verify_confidential_batch(self, suspects: List[Dict], full_text: str) -> List[Dict]:
        """배치 단위 기업기밀 LLM 검증"""
        
        contexts_text = "\n\n---\n\n".join([
            f"[구간 {i+1}]\n"
            f"발견된 키워드: {', '.join(s.get('keywords', [s.get('keyword', '')]))}\n"
            f"카테고리 힌트: {', '.join(s.get('categories', [s.get('category', '')]))}\n"
            f"내용:\n{s['context']}"
            for i, s in enumerate(suspects)
        ])
        
        prompt = f"""당신은 기업 보안 전문가입니다.
다음 텍스트 구간들이 부정경쟁방지법상 "영업비밀" 또는 "기업기밀"에 해당하는지 판단하세요.

【영업비밀 정의 (부정경쟁방지법 제2조 제2호)】
다음 요건을 모두 충족해야 영업비밀입니다:
1. 비공개성: 공개되지 않은 정보
2. 경제적 가치: 경쟁상 유용한 정보
3. 비밀관리성: 비밀로 관리되는 정보

【기업기밀 유형】
1. 영업비밀: 대외비, 기밀, confidential 등 명시적 표시
2. 기술정보: 특허출원 전 기술, 설계도, 소스코드, 제조공정, 알고리즘
3. 경영정보: 미공개 재무정보, 거래처 목록, 가격표, 계약조건
4. 인사급여: 개인별 연봉, 성과급, 인사평가 등급
5. 전략정보: 미발표 사업계획, 신제품 출시일정, M&A 계획

【기업기밀이 아닌 경우 - 반드시 제외】
- 이미 공개된 정보 (뉴스, 공시, 홈페이지 게시)
- 일반적인 업무 용어 사용 (단순히 "매출", "전략" 단어만 있는 경우)
- 교육/학습 자료의 일반적 설명
- 구체적 수치/내용 없이 용어만 언급

【검토 대상 구간들】
{contexts_text}

【출력 형식】
반드시 아래 JSON 형식으로만 응답하세요:
{{
  "results": [
    {{
      "index": 1,
      "is_confidential": true,
      "type": "기술정보",
      "value": "기밀에 해당하는 실제 텍스트 발췌",
      "confidentiality_indicator": "기밀 판단 근거 (예: 대외비 표시, 미공개 설계도)",
      "reason": "판단 근거"
    }},
    {{
      "index": 2,
      "is_confidential": false,
      "reason": "제외 사유"
    }}
  ]
}}

JSON만 출력하세요."""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=90
            )
            
            if response.status_code == 200:
                llm_response = response.json().get('response', '')
                result = self._parse_json(llm_response)
                
                if result and 'results' in result:
                    verified = []
                    for r in result['results']:
                        if r.get('is_confidential', False):
                            idx = r.get('index', 1) - 1
                            if 0 <= idx < len(suspects):
                                suspect = suspects[idx]
                                
                                value = r.get('value', suspect.get('keyword', ''))
                                pos = full_text.find(value)
                                if pos == -1:
                                    pos = suspect['position']
                                
                                verified.append({
                                    'type': r.get('type', suspect.get('categories', ['기업기밀'])[0]),
                                    'value': value,
                                    'start': pos,
                                    'end': pos + len(value),
                                    'context': suspect['context'],
                                    'method': 'llm',
                                    'confidence': 'high',
                                    'legal_category': '기업기밀',
                                    'exposure_prohibited': True,
                                    'confidentiality_indicator': r.get('confidentiality_indicator', ''),
                                    'reason': r.get('reason', '')
                                })
                    
                    logger.info(f"LLM 기업기밀 검증: {len(suspects)}개 중 {len(verified)}개 확정")
                    return verified
                    
        except requests.exceptions.Timeout:
            logger.error("LLM 기업기밀 검증 타임아웃")
        except Exception as e:
            logger.error(f"LLM 기업기밀 검증 실패: {str(e)}")
        
        return []
    
    def detect_confidential_info(self, text: str) -> List[Dict]:
        """
        기업기밀 탐지: 순수 LLM 기반 (키워드 스캔 없음)
        
        부정경쟁방지법 제2조 영업비밀 직접 탐지
        """
        if not text or len(text.strip()) < 50:
            return []
        
        self._emit_status("🔍 기업기밀 탐지 중 (LLM 직접 분석)...")
        
        # 문서를 청크로 분할
        chunks = self._split_text_into_chunks(text, chunk_size=1500, overlap=150)
        logger.info(f"기업기밀 탐지: {len(chunks)}개 청크")
        
        all_results = []
        for i, chunk_info in enumerate(chunks):
            self._emit_status(f"🤖 기업기밀 분석 중... ({i+1}/{len(chunks)})")
            chunk_results = self._detect_confidential_in_chunk_direct(
                chunk_info['text'], 
                chunk_info['start_offset'],
                i + 1,
                len(chunks)
            )
            all_results.extend(chunk_results)
        
        # 중복 제거
        deduplicated = self._deduplicate_sensitive_results(all_results)
        
        self._emit_status(f"✅ 기업기밀 {len(deduplicated)}개 탐지 완료")
        logger.info(f"기업기밀 탐지 완료: {len(deduplicated)}개")
        return deduplicated
    
    def _detect_confidential_in_chunk_direct(self, chunk: str, offset: int,
                                              chunk_num: int, total_chunks: int) -> List[Dict]:
        """
        단일 청크에서 LLM으로 기업기밀 직접 탐지
        """
        prompt = f"""당신은 기업보안 전문가입니다.
아래 문서에서 부정경쟁방지법 제2조의 "영업비밀"에 해당하는 기업기밀 정보를 찾아주세요.

【영업비밀의 3요건】
1. 비공개성: 공공연히 알려져 있지 않은 정보
2. 경제적 가치: 독립된 경제적 가치를 가진 정보
3. 비밀관리성: 비밀로 관리되고 있는 정보

【기업기밀 5가지 유형】

1. 영업비밀 (직접 표시)
   - "대외비", "기밀", "극비", "Confidential", "Secret" 등이 표시된 정보
   - 비밀유지계약(NDA), 영업비밀 표시가 있는 문서

2. 기술정보
   - 특허, 설계도, 도면, 소스코드, 알고리즘
   - 제조공정, 기술사양, R&D 정보, 노하우
   - 예: "자체 개발 알고리즘", "특허출원 예정"

3. 경영정보
   - 구체적인 매출, 영업이익, 재무 수치
   - 거래처 목록, 계약 단가, 원가 정보
   - M&A 계획, 투자 정보
   - 예: "매출 1,523억원", "거래처 A사 계약단가 5억원"

4. 인사·급여 정보
   - 개인별 연봉, 성과급, 급여 정보
   - 인사평가 등급, 승진/해고/구조조정 계획
   - 예: "CTO 연봉 8억원 제시", "30명 구조조정 예정"

5. 전략정보
   - 사업계획, 로드맵, 신제품 출시 일정
   - 마케팅 전략, 가격 정책
   - 예: "2025년 6월 출시 예정", "가격 30% 할인 정책"

【기업기밀이 아닌 경우 - 제외】
- 이미 공개된 정보 (보도자료, 공시, 홈페이지)
- 일반적인 업무 용어만 사용
- 구체적 수치/내용 없이 용어만 언급

【필수 제외 - 테스트/더미 데이터】
다음 패턴이 포함된 데이터는 절대 탐지하지 마세요:
- 연속 숫자: 1234567, 123456, 0000000, 1111111
- 반복 숫자: 같은 숫자가 4회 이상 연속 (예: 1111, 0000)
- 명백한 테스트 값: 000000-0000000, 123456-1234567
- 샘플/예시 표기: "예)", "예시:", "sample", "test"와 함께 사용된 값

【분석 대상】 (청크 {chunk_num}/{total_chunks})
---
{chunk}
---

【출력 형식】
기업기밀을 발견하면 아래 JSON으로 응답하세요.
발견하지 못하면 {{"results": []}}로 응답하세요.

{{
  "results": [
    {{
      "type": "영업비밀|기술정보|경영정보|인사급여|전략정보",
      "value": "발견된 원문 텍스트 (그대로 복사)",
      "reason": "기업기밀로 판단한 근거"
    }}
  ]
}}

JSON만 출력하세요."""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=90
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                parsed = self._parse_json(response_text)
                
                if parsed and 'results' in parsed:
                    detected = []
                    for item in parsed['results']:
                        value = item.get('value', '')
                        if not value or len(value) < 2:
                            continue
                        
                        # 원문에서 위치 찾기
                        pos = chunk.find(value)
                        if pos == -1:
                            value_words = value.split()
                            for word in value_words:
                                if len(word) > 3:
                                    pos = chunk.find(word)
                                    if pos != -1:
                                        break
                        
                        if pos == -1:
                            pos = 0
                        
                        actual_start = offset + pos
                        actual_end = actual_start + len(value)
                        
                        info_type = item.get('type', '기업기밀')
                        
                        ctx_start = max(0, pos - 50)
                        ctx_end = min(len(chunk), pos + len(value) + 50)
                        
                        detected.append({
                            'type': info_type,
                            'value': value[:100],
                            'start': actual_start,
                            'end': actual_end,
                            'context': chunk[ctx_start:ctx_end],
                            'legal_category': '기업기밀',
                            'detection_method': 'llm_direct',
                            'reason': item.get('reason', '')
                        })
                    
                    return detected
        
        except requests.exceptions.Timeout:
            logger.warning(f"기업기밀 청크 {chunk_num} LLM 타임아웃")
        except Exception as e:
            logger.warning(f"기업기밀 청크 {chunk_num} 탐지 오류: {e}")
        
        return []

    # =========================================================================
    # LLM 종합 분석 (위험도 평가)
    # =========================================================================
    
    def analyze_with_llm(self, text: str) -> Dict:
        """LLM 종합 위험도 분석"""
        text_sample = text[:2000]
        
        prompt = f"""문서 보안 전문가로서 개인정보보호법에 따라 다음 문서를 분석하세요.

【문서】
{text_sample}

【분류 기준】
1. 고유식별정보 (제24조): 주민등록번호, 여권번호, 운전면허번호, 외국인등록번호
2. 민감정보 (제23조): 특정 개인의 건강, 사상·신념, 노조·정당, 정치적 견해, 성생활, 범죄경력
3. 금융정보 (제34조의2): 계좌번호, 카드번호
4. 일반개인정보 (제2조): 전화번호, 이메일, 주소 등

【위험도 기준】
- 낮음: 0-24점
- 보통: 25-49점
- 높음: 50-74점
- 심각: 75-100점

【출력 형식】
{{
  "detected_info": [{{"type": "유형", "value": "값", "legal_category": "법적분류"}}],
  "risk_level": "낮음|보통|높음|심각",
  "risk_score": 숫자(0-100),
  "reasoning": "판단 근거",
  "recommendations": ["권고1", "권고2", "권고3"]
}}

JSON만 출력하세요."""

        try:
            try:
                self._emit_status("🔗 Ollama 서버 확인 중...")
                health_response = requests.get(OLLAMA_TAGS_URL, timeout=2)
                if health_response.status_code != 200:
                    return self._create_enhanced_analysis(text)
            except:
                return self._create_enhanced_analysis(text)
            
            self._emit_status(f"🤖 {self.model_name} 위험도 분석 중...")
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2,
                },
                timeout=OLLAMA_TIMEOUT
            )
            
            if response.status_code == 200:
                self._emit_status("📝 LLM 응답 파싱 중...")
                llm_response = response.json().get('response', '')
                parsed = self._parse_json(llm_response)
                
                if parsed and 'recommendations' in parsed:
                    logger.info("LLM 위험도 분석 성공")
                    self._emit_status("✅ LLM 분석 성공")
                    return parsed
                    
        except requests.exceptions.Timeout:
            logger.warning(f"LLM 타임아웃")
        except Exception as e:
            logger.warning(f"LLM 분석 실패: {str(e)}")
        
        return self._create_enhanced_analysis(text)
    
    def _parse_json(self, response: str) -> Optional[Dict]:
        """JSON 파싱"""
        try:
            return json.loads(response)
        except:
            pass
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        
        return None
    
    def _create_enhanced_analysis(self, text: str) -> Dict:
        """규칙 기반 분석 (LLM 폴백)"""
        # 정규식 탐지
        regex_detected = self.detect_sensitive_info_regex(text)
        
        # 민감정보 LLM 탐지
        sensitive_detected = self.detect_sensitive_info_v2(text)
        
        # 기업기밀 LLM 탐지
        confidential_detected = self.detect_confidential_info(text)
        
        # 통합
        all_detected = regex_detected.copy()
        existing_ranges = [(d['start'], d['end']) for d in regex_detected]
        
        for item in sensitive_detected:
            is_dup = any(
                self._is_overlapping(item['start'], item['end'], s, e)
                for s, e in existing_ranges
            )
            if not is_dup:
                all_detected.append(item)
                existing_ranges.append((item['start'], item['end']))
        
        for item in confidential_detected:
            is_dup = any(
                self._is_overlapping(item['start'], item['end'], s, e)
                for s, e in existing_ranges
            )
            if not is_dup:
                all_detected.append(item)
                existing_ranges.append((item['start'], item['end']))
        
        # 법적 분류별 집계
        category_counts = {
            "고유식별정보": 0,
            "민감정보": 0,
            "금융정보": 0,
            "기업기밀": 0,
            "일반개인정보": 0
        }
        
        for item in all_detected:
            cat = item.get('legal_category', '일반개인정보')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # 위험도 계산
        risk_score = 0
        risk_score += category_counts.get("고유식별정보", 0) * 20
        risk_score += category_counts.get("금융정보", 0) * 15
        risk_score += category_counts.get("민감정보", 0) * 12
        risk_score += category_counts.get("기업기밀", 0) * 12
        risk_score += category_counts.get("일반개인정보", 0) * 5
        
        active_categories = sum(1 for c in category_counts.values() if c > 0)
        if active_categories >= 3:
            risk_score += 20
        elif active_categories >= 2:
            risk_score += 10
        
        total_count = len(all_detected)
        if total_count >= 50:
            risk_score += 15
        elif total_count >= 20:
            risk_score += 10
        elif total_count >= 10:
            risk_score += 5
        
        risk_score = min(risk_score, 100)
        
        if risk_score >= 75:
            risk_level = "심각"
        elif risk_score >= 50:
            risk_level = "높음"
        elif risk_score >= 25:
            risk_level = "보통"
        else:
            risk_level = "낮음"
        
        # 법적 위반 가능성
        legal_violations = []
        if category_counts.get("고유식별정보", 0) > 0:
            legal_violations.append("제24조(고유식별정보 처리제한) 위반 가능성")
        if category_counts.get("민감정보", 0) > 0:
            legal_violations.append("제23조(민감정보 처리제한) 위반 가능성")
        if category_counts.get("금융정보", 0) > 0:
            legal_violations.append("제34조의2(노출금지) 위반 가능성")
        if category_counts.get("기업기밀", 0) > 0:
            legal_violations.append("부정경쟁방지법(영업비밀 보호) 위반 가능성")
        
        # 판단 근거
        reasoning_parts = [f"총 {total_count}개의 민감정보가 탐지되었습니다."]
        
        if category_counts.get("고유식별정보", 0) > 0:
            reasoning_parts.append(
                f"🔴 고유식별정보 {category_counts['고유식별정보']}개 (제24조)"
            )
        if category_counts.get("금융정보", 0) > 0:
            reasoning_parts.append(
                f"🟣 금융정보 {category_counts['금융정보']}개 (제34조의2)"
            )
        if category_counts.get("민감정보", 0) > 0:
            reasoning_parts.append(
                f"🟠 민감정보 {category_counts['민감정보']}개 (제23조)"
            )
        if category_counts.get("기업기밀", 0) > 0:
            reasoning_parts.append(
                f"🔷 기업기밀 {category_counts['기업기밀']}개 (부정경쟁방지법)"
            )
        if category_counts.get("일반개인정보", 0) > 0:
            reasoning_parts.append(
                f"🔵 일반개인정보 {category_counts['일반개인정보']}개 (제2조)"
            )
        
        reasoning = "\n".join(reasoning_parts)
        
        # 권고사항
        recommendations = self.recommendation_engine.generate_recommendations(
            all_detected, risk_level, risk_score, text
        )
        
        return {
            "detected_info": [
                {
                    "type": i['type'], 
                    "value": i['value'], 
                    "context": i.get('context', ''),
                    "legal_category": i.get('legal_category', '일반개인정보')
                }
                for i in all_detected
            ],
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasoning": reasoning,
            "legal_violations": legal_violations,
            "category_summary": category_counts,
            "recommendations": recommendations
        }

    # =========================================================================
    # 종합 분석 (메인 진입점)
    # =========================================================================
    
    def comprehensive_analysis(self, text: str) -> Tuple[Dict, List[Dict]]:
        """
        종합 분석 (개인정보보호법 기반)
        
        v2.1 변경사항:
        - 민감정보 탐지를 LLM 기반으로 전환
        - 기존 복잡한 규칙/교차검증 로직 제거
        - 사용자 정의 패턴 탐지 추가
        """
        logger.info("분석 시작 - v2.1 (민감정보 LLM 탐지)")
        
        # 1단계: 정규식 기반 탐지 (고유식별정보, 금융정보, 연락처)
        self._emit_status("🔍 정규식 기반 개인정보 탐지 중...")
        regex_detected = self.detect_sensitive_info_regex(text)
        logger.info(f"정규식 탐지 완료: {len(regex_detected)}개")
        self._emit_status(f"✅ 정규식 탐지: {len(regex_detected)}개")
        
        # 2단계: 민감정보 LLM 탐지 (제23조)
        self._emit_status("🔍 민감정보 탐지 중 (LLM)...")
        sensitive_detected = self.detect_sensitive_info_v2(text)
        logger.info(f"민감정보 탐지 완료: {len(sensitive_detected)}개")
        
        # 3단계: 기업기밀 LLM 탐지 (부정경쟁방지법)
        self._emit_status("🔍 기업기밀 탐지 중 (LLM)...")
        confidential_detected = self.detect_confidential_info(text)
        logger.info(f"기업기밀 탐지 완료: {len(confidential_detected)}개")
        
        # 4단계: 사용자 정의 패턴 탐지
        self._emit_status("🔍 사용자 정의 패턴 탐지 중...")
        user_pattern_detected = self.detect_user_patterns(text)
        logger.info(f"사용자 패턴 탐지 완료: {len(user_pattern_detected)}개")
        
        # 5단계: 결과 병합
        all_detected = regex_detected.copy()
        existing_ranges = [(d['start'], d['end']) for d in regex_detected]
        
        # 민감정보 병합
        for item in sensitive_detected:
            is_dup = any(
                self._is_overlapping(item['start'], item['end'], s, e)
                for s, e in existing_ranges
            )
            if not is_dup:
                all_detected.append(item)
                existing_ranges.append((item['start'], item['end']))
        
        # 기업기밀 병합
        for item in confidential_detected:
            is_dup = any(
                self._is_overlapping(item['start'], item['end'], s, e)
                for s, e in existing_ranges
            )
            if not is_dup:
                all_detected.append(item)
                existing_ranges.append((item['start'], item['end']))
        
        # 사용자 정의 패턴 병합
        for item in user_pattern_detected:
            is_dup = any(
                self._is_overlapping(item['start'], item['end'], s, e)
                for s, e in existing_ranges
            )
            if not is_dup:
                all_detected.append(item)
                existing_ranges.append((item['start'], item['end']))
        
        all_detected.sort(key=lambda x: x.get('start', 0))
        
        # 5.5단계: 체크섬 일괄 검증 (v2.2 추가)
        self._emit_status("🔍 체크섬 검증 중...")
        all_detected = self._apply_checksum_filter(all_detected)
        logger.info(f"체크섬 필터 후: {len(all_detected)}개")
        
        # 6단계: 위험도 분석
        self._emit_status("📊 위험도 분석 중...")
        analysis_result = self._create_analysis_from_detected(all_detected, text)
        
        # 7단계: LLM 추가 분석 (선택적)
        try:
            self._emit_status("🤖 LLM 종합 분석 중...")
            llm_analysis = self.analyze_with_llm(text)
            
            if llm_analysis and 'risk_level' in llm_analysis:
                # LLM이 더 높은 위험도를 반환하면 채택 (보수적)
                if llm_analysis.get('risk_score', 0) > analysis_result.get('risk_score', 0):
                    analysis_result['risk_score'] = llm_analysis['risk_score']
                    analysis_result['risk_level'] = llm_analysis['risk_level']
                
                # 권고사항 병합
                llm_recs = llm_analysis.get('recommendations', [])
                existing_recs = analysis_result.get('recommendations', [])
                merged_recs = list(dict.fromkeys(existing_recs + llm_recs))
                analysis_result['recommendations'] = merged_recs[:10]
                
                self._emit_status("✅ LLM 분석 완료")
        except Exception as e:
            logger.warning(f"LLM 추가 분석 실패: {e}")
        
        # 8단계: 권고사항 보장
        if len(analysis_result.get('recommendations', [])) < 3:
            enhanced_recs = self.recommendation_engine.generate_recommendations(
                all_detected,
                analysis_result.get('risk_level', '보통'),
                analysis_result.get('risk_score', 50),
                text
            )
            analysis_result['recommendations'] = enhanced_recs
        
        logger.info(f"분석 완료: {len(all_detected)}개 항목, 위험도 {analysis_result['risk_level']}")
        
        return analysis_result, all_detected
    
    def detect_user_patterns(self, text: str) -> List[Dict]:
        """
        사용자 정의 패턴 탐지
        
        사용자가 추가한 키워드/정규식을 사용하여 탐지
        """
        try:
            # 지연 로딩으로 순환 참조 방지
            from core.user_pattern_manager import get_pattern_manager
            pattern_manager = get_pattern_manager()
            detected = pattern_manager.detect_in_text(text)
            return detected
        except Exception as e:
            logger.warning(f"사용자 패턴 탐지 오류: {e}")
            return []
    
    def _create_analysis_from_detected(self, detected_items: List[Dict], text: str) -> Dict:
        """탐지 결과로부터 분석 결과 생성"""
        
        # 법적 분류별 집계
        category_counts = {
            "고유식별정보": 0,
            "민감정보": 0,
            "금융정보": 0,
            "기업기밀": 0,
            "사용자정의": 0,
            "일반개인정보": 0
        }
        
        # 사용자정의 패턴 점수 합산
        user_pattern_score_total = 0
        
        for item in detected_items:
            cat = item.get('legal_category', '일반개인정보')
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # 사용자정의 패턴은 개별 점수 합산
            if cat == '사용자정의':
                user_pattern_score_total += item.get('score', 10)
        
        # 위험도 계산
        risk_score = 0
        risk_score += category_counts.get("고유식별정보", 0) * 20
        risk_score += category_counts.get("금융정보", 0) * 15
        risk_score += category_counts.get("민감정보", 0) * 12
        risk_score += category_counts.get("기업기밀", 0) * 12
        risk_score += user_pattern_score_total  # 사용자정의: 개별 점수 합산
        risk_score += category_counts.get("일반개인정보", 0) * 5
        
        active_categories = sum(1 for c in category_counts.values() if c > 0)
        if active_categories >= 3:
            risk_score += 20
        elif active_categories >= 2:
            risk_score += 10
        
        total_count = len(detected_items)
        if total_count >= 50:
            risk_score += 15
        elif total_count >= 20:
            risk_score += 10
        elif total_count >= 10:
            risk_score += 5
        
        risk_score = min(risk_score, 100)
        
        if risk_score >= 75:
            risk_level = "심각"
        elif risk_score >= 50:
            risk_level = "높음"
        elif risk_score >= 25:
            risk_level = "보통"
        else:
            risk_level = "낮음"
        
        # 법적 위반 가능성
        legal_violations = []
        if category_counts.get("고유식별정보", 0) > 0:
            legal_violations.append("제24조(고유식별정보 처리제한)")
        if category_counts.get("민감정보", 0) > 0:
            legal_violations.append("제23조(민감정보 처리제한)")
        if category_counts.get("금융정보", 0) > 0:
            legal_violations.append("제34조의2(노출금지)")
        if category_counts.get("기업기밀", 0) > 0:
            legal_violations.append("부정경쟁방지법(영업비밀 보호)")
        if category_counts.get("사용자정의", 0) > 0:
            legal_violations.append("사용자정의 패턴 탐지")
        
        # 판단 근거
        reasoning_parts = [f"총 {total_count}개의 민감정보가 탐지되었습니다."]
        
        if category_counts.get("고유식별정보", 0) > 0:
            reasoning_parts.append(f"🔴 고유식별정보 {category_counts['고유식별정보']}개")
        if category_counts.get("금융정보", 0) > 0:
            reasoning_parts.append(f"🟣 금융정보 {category_counts['금융정보']}개")
        if category_counts.get("민감정보", 0) > 0:
            reasoning_parts.append(f"🟠 민감정보 {category_counts['민감정보']}개")
        if category_counts.get("기업기밀", 0) > 0:
            reasoning_parts.append(f"🔷 기업기밀 {category_counts['기업기밀']}개")
        if category_counts.get("사용자정의", 0) > 0:
            reasoning_parts.append(f"⭐ 사용자정의 {category_counts['사용자정의']}개 (+{user_pattern_score_total}점)")
        if category_counts.get("일반개인정보", 0) > 0:
            reasoning_parts.append(f"🔵 일반개인정보 {category_counts['일반개인정보']}개")
        
        # 권고사항
        recommendations = self.recommendation_engine.generate_recommendations(
            detected_items, risk_level, risk_score, text
        )
        
        return {
            "detected_info": [
                {
                    "type": i['type'],
                    "value": i['value'],
                    "context": i.get('context', ''),
                    "legal_category": i.get('legal_category', '일반개인정보')
                }
                for i in detected_items
            ],
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasoning": "\n".join(reasoning_parts),
            "legal_violations": legal_violations,
            "category_summary": category_counts,
            "recommendations": recommendations
        }

    # =========================================================================
    # 유틸리티
    # =========================================================================
    
    def mask_sensitive_info(self, text: str, detected_items: List[Dict]) -> str:
        """민감정보 마스킹"""
        masked_text = text
        offset = 0
        
        for item in sorted(detected_items, key=lambda x: x.get('start', 0)):
            start = item.get('start', 0) + offset
            end = item.get('end', 0) + offset
            value = item.get('value', '')
            info_type = item['type']
            
            if value:
                mask_char = '*'
                
                if info_type in ['주민등록번호', '여권번호', '운전면허번호', '외국인등록번호']:
                    masked = value[:4] + mask_char * (len(value) - 4)
                elif info_type in ['카드번호', '계좌번호']:
                    masked = value[:4] + mask_char * (len(value) - 4)
                elif info_type in ['전화번호', '휴대전화']:
                    parts = value.split('-')
                    if len(parts) == 3:
                        masked = f"{parts[0]}-{mask_char * len(parts[1])}-{parts[2]}"
                    else:
                        masked = mask_char * len(value)
                elif info_type == '이메일':
                    at_pos = value.find('@')
                    if at_pos > 0:
                        masked = value[0] + mask_char * (at_pos - 1) + value[at_pos:]
                    else:
                        masked = mask_char * len(value)
                else:
                    masked = mask_char * len(value)
                
                masked_text = masked_text[:start] + masked + masked_text[end:]
                offset += len(masked) - len(value)
        
        return masked_text
    
    def get_legal_summary(self, detected_items: List[Dict]) -> Dict:
        """법적 분류별 요약"""
        summary = {
            "고유식별정보": {
                "count": 0,
                "items": [],
                "legal_basis": "제24조",
                "requirement": "처리 제한, 암호화 의무"
            },
            "민감정보": {
                "count": 0,
                "items": [],
                "legal_basis": "제23조",
                "requirement": "원칙적 처리 금지, 별도 동의"
            },
            "금융정보": {
                "count": 0,
                "items": [],
                "legal_basis": "제34조의2",
                "requirement": "노출 금지"
            },
            "일반개인정보": {
                "count": 0,
                "items": [],
                "legal_basis": "제2조",
                "requirement": "기본 보호 원칙"
            }
        }
        
        for item in detected_items:
            category = item.get('legal_category', '일반개인정보')
            if category in summary:
                summary[category]["count"] += 1
                summary[category]["items"].append({
                    "type": item['type'],
                    "value": item['value'][:20] + "..." if len(item['value']) > 20 else item['value']
                })
        
        return summary
