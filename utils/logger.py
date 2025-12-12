"""
로깅 설정 모듈
"""
import logging
from pathlib import Path


def setup_logger(name: str = __name__, log_file: str = 'document_analyzer.log') -> logging.Logger:
    """로거 설정 및 반환"""
    
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """로거 가져오기 (setup_logger의 별칭)"""
    if name is None:
        return logger
    return setup_logger(name)


# 기본 로거
logger = setup_logger('DocumentAnalyzer')
