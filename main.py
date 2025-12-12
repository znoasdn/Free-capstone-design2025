#!/usr/bin/env python3
"""
문서 위험도 분석 시스템 v2.0 (리팩토링)
엔트리 포인트
"""
import sys
from PyQt5.QtWidgets import QApplication
from gui import DocumentAnalyzerGUI


def main():
    """메인 함수"""
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        app.setApplicationName("문서 위험도 분석 시스템")
        app.setOrganizationName("DocumentAnalyzer")
        
        window = DocumentAnalyzerGUI()
        window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"애플리케이션 시작 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
