"""
사용자 정의 패턴 관리자

사용자가 추가한 커스텀 키워드/정규식 패턴을 관리하고 탐지
"""
import re
import json
import os
from typing import List, Dict, Optional
from utils.logger import logger


class UserPatternManager:
    """사용자 정의 패턴 관리"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # 기본 경로: 프로그램 폴더 내 user_patterns.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, 'user_patterns.json')
        
        self.config_path = config_path
        self.patterns: List[Dict] = []
        self.load_patterns()
    
    def load_patterns(self):
        """저장된 패턴 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    logger.info(f"사용자 패턴 {len(self.patterns)}개 로드됨")
            else:
                self.patterns = []
        except Exception as e:
            logger.error(f"패턴 로드 실패: {e}")
            self.patterns = []
    
    def save_patterns(self):
        """패턴 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({'patterns': self.patterns}, f, ensure_ascii=False, indent=2)
            logger.info(f"사용자 패턴 {len(self.patterns)}개 저장됨")
            return True
        except Exception as e:
            logger.error(f"패턴 저장 실패: {e}")
            return False
    
    def add_pattern(self, name: str, pattern: str, pattern_type: str = 'keyword',
                    description: str = '', score: int = 8, category: str = '사용자정의') -> bool:
        """
        패턴 추가
        
        Args:
            name: 패턴 이름 (표시용)
            pattern: 키워드 또는 정규식
            pattern_type: 'keyword' 또는 'regex'
            description: 설명
            score: 위험도 점수 (1-15, 기본값 8)
            category: 카테고리 (기본값 '사용자정의')
        """
        # 정규식 유효성 검증
        if pattern_type == 'regex':
            try:
                re.compile(pattern)
            except re.error as e:
                logger.error(f"잘못된 정규식: {e}")
                return False
        
        # 중복 체크
        for p in self.patterns:
            if p['pattern'] == pattern:
                logger.warning(f"이미 존재하는 패턴: {pattern}")
                return False
        
        # 점수 범위 제한 (1-15)
        score = max(1, min(15, score))
        
        new_pattern = {
            'name': name,
            'pattern': pattern,
            'type': pattern_type,
            'description': description,
            'score': score,
            'category': category,
            'enabled': True
        }
        
        self.patterns.append(new_pattern)
        self.save_patterns()
        return True
    
    def remove_pattern(self, pattern: str) -> bool:
        """패턴 제거"""
        for i, p in enumerate(self.patterns):
            if p['pattern'] == pattern:
                self.patterns.pop(i)
                self.save_patterns()
                return True
        return False
    
    def update_pattern(self, old_pattern: str, **kwargs) -> bool:
        """패턴 수정"""
        for p in self.patterns:
            if p['pattern'] == old_pattern:
                for key, value in kwargs.items():
                    if key in p:
                        p[key] = value
                self.save_patterns()
                return True
        return False
    
    def toggle_pattern(self, pattern: str) -> bool:
        """패턴 활성화/비활성화 토글"""
        for p in self.patterns:
            if p['pattern'] == pattern:
                p['enabled'] = not p.get('enabled', True)
                self.save_patterns()
                return True
        return False
    
    def get_patterns(self, enabled_only: bool = True) -> List[Dict]:
        """패턴 목록 반환"""
        if enabled_only:
            return [p for p in self.patterns if p.get('enabled', True)]
        return self.patterns
    
    def detect_in_text(self, text: str) -> List[Dict]:
        """
        텍스트에서 사용자 정의 패턴 탐지
        
        Returns:
            탐지된 항목 리스트
        """
        detected = []
        
        for pattern_info in self.get_patterns(enabled_only=True):
            pattern = pattern_info['pattern']
            pattern_type = pattern_info.get('type', 'keyword')
            name = pattern_info.get('name', pattern)
            score = pattern_info.get('score', 10)
            
            try:
                if pattern_type == 'regex':
                    # 정규식 매칭
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        start = match.start()
                        end = match.end()
                        value = match.group()
                        
                        # 컨텍스트 추출
                        ctx_start = max(0, start - 50)
                        ctx_end = min(len(text), end + 50)
                        context = text[ctx_start:ctx_end]
                        
                        detected.append({
                            'type': f'사용자정의:{name}',
                            'value': value,
                            'start': start,
                            'end': end,
                            'context': context,
                            'method': 'user_pattern',
                            'confidence': 'high',
                            'legal_category': '사용자정의',
                            'score': score,
                            'pattern_name': name
                        })
                else:
                    # 키워드 매칭
                    text_lower = text.lower()
                    pattern_lower = pattern.lower()
                    pos = 0
                    
                    while True:
                        pos = text_lower.find(pattern_lower, pos)
                        if pos == -1:
                            break
                        
                        end = pos + len(pattern)
                        value = text[pos:end]
                        
                        # 컨텍스트 추출
                        ctx_start = max(0, pos - 50)
                        ctx_end = min(len(text), end + 50)
                        context = text[ctx_start:ctx_end]
                        
                        detected.append({
                            'type': f'사용자정의:{name}',
                            'value': value,
                            'start': pos,
                            'end': end,
                            'context': context,
                            'method': 'user_pattern',
                            'confidence': 'high',
                            'legal_category': '사용자정의',
                            'score': score,
                            'pattern_name': name
                        })
                        
                        pos += 1
                        
            except Exception as e:
                logger.warning(f"패턴 '{name}' 탐지 오류: {e}")
                continue
        
        return detected


# 싱글톤 인스턴스
_pattern_manager: Optional[UserPatternManager] = None


def get_pattern_manager() -> UserPatternManager:
    """패턴 매니저 싱글톤 반환"""
    global _pattern_manager
    if _pattern_manager is None:
        _pattern_manager = UserPatternManager()
    return _pattern_manager
