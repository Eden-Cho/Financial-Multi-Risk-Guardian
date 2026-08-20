import sys
import os

# 현재 폴더(루트)를 파이썬 경로로 인식
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.modules.analyzer import RiskAnalyzer
from frontend.layout import create_ui

if __name__ == "__main__":
    analyzer = RiskAnalyzer()
    demo = create_ui(analyzer)
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)