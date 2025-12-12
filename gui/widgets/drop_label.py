"""
드래그 앤 드롭 지원 라벨 위젯
"""
from pathlib import Path
from PyQt5.QtWidgets import QLabel, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from utils.constants import SUPPORTED_EXTENSIONS


class DropLabel(QLabel):
    """드래그 앤 드롭 지원 라벨"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
                font-size: 14px;
            }
        """)
        self.default_text = text
        self.is_dragging = False
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.is_dragging = True
            self.setStyleSheet("""
                QLabel {
                    border: 3px dashed #4CAF50;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """드래그 이탈"""
        self.is_dragging = False
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
                font-size: 14px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """드롭 이벤트"""
        self.is_dragging = False
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 20px;
                background-color: #f9f9f9;
                color: #666;
                font-size: 14px;
            }
        """)
        
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                ext = Path(file_path).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(file_path)
        
        if files:
            self.files_dropped.emit(files)
        else:
            QMessageBox.warning(
                self, '경고',
                '지원하는 파일 형식이 아닙니다.\n(PDF, DOCX, TXT, HWP, HWPX만 지원)'
            )
