"""
분석 이력 관리
"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from utils.logger import logger


class AnalysisHistory:
    """분석 이력 관리"""
    
    def __init__(self, history_file: str = 'analysis_history.json'):
        self.history_file = Path(history_file)
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """이력 로드"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"이력 로드 실패: {str(e)}")
                return []
        return []
    
    def _save_history(self):
        """이력 저장"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"이력 저장 실패: {str(e)}")
    
    def add_record(self, filename: str, result: Dict, detected_count: int, detected_items: List = None, document_text: str = None, llm_model: str = None):
        """분석 기록 추가"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'risk_level': result.get('risk_level', '알 수 없음'),
            'risk_score': result.get('risk_score', 0),
            'detected_count': detected_count,
            'result': result,
            'detected_items': detected_items or [],
            'document_text': document_text or '',
            'llm_model': llm_model or '규칙 기반'
        }
        
        self.history.insert(0, record)
        
        # 최대 100개까지만 저장
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self._save_history()
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """최근 분석 기록"""
        return self.history[:limit]
    
    def clear(self):
        """이력 삭제"""
        self.history = []
        self._save_history()
    
    def delete_by_timestamps(self, timestamps: List[str]) -> int:
        """특정 timestamp의 기록들 삭제
        
        Args:
            timestamps: 삭제할 기록들의 timestamp 리스트
            
        Returns:
            삭제된 기록 수
        """
        original_count = len(self.history)
        self.history = [r for r in self.history if r['timestamp'] not in timestamps]
        deleted_count = original_count - len(self.history)
        
        if deleted_count > 0:
            self._save_history()
            logger.info(f"{deleted_count}개 기록 삭제됨")
        
        return deleted_count
    
    def get_statistics(self) -> Dict:
        """통계 정보 반환"""
        if not self.history:
            return {
                'total': 0,
                'avg_score': 0,
                'high_risk_count': 0
            }
        
        total = len(self.history)
        avg_score = sum(r['risk_score'] for r in self.history) / total
        high_risk_count = sum(1 for r in self.history if r['risk_score'] >= 75)
        
        return {
            'total': total,
            'avg_score': avg_score,
            'high_risk_count': high_risk_count
        }
