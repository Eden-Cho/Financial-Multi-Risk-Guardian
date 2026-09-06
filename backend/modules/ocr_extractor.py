"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/ocr_extractor.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할: 
    1. EasyOCR 지연 로딩을 통한 메모리 최적화
    2. 증권사 잔고/MTS 캡처 이미지로부터 KRX 상장 종목명 및 종목코드 추출
    3. KRX 마스터(krx_stocks.json) 기반 완전 일치, 부분 일치, 퍼지 매칭(Fuzzy Matching) 3단계 보정
==============================================================================
"""

import os
import io
import re
import json
import difflib
from typing import Optional, List, Dict
from PIL import Image
import numpy as np


class StockOcrExtractor:
    """증권사 앱 스크린샷 이미지 기반 KRX 상장 종목명 및 코드 자동 추출기"""

    def __init__(self, json_path: Optional[str] = None):
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            self.json_path = os.path.join(backend_dir, "data", "krx_stocks.json")
        else:
            self.json_path = os.path.abspath(json_path)

        self.reader = None
        self.stock_dict: Dict[str, str] = {}
        self.stock_names: List[str] = []
        self._load_stock_master()

    def _load_stock_master(self):
        """KRX 상장사 마스터 JSON 파일 로드"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.stock_dict = json.load(f)
                self.stock_names = list(self.stock_dict.keys())
                print(f"[StockOcrExtractor] KRX 마스터 로드 완료: {len(self.stock_names)}개 종목")
            except Exception as e:
                print(f"[StockOcrExtractor] 마스터 파일 읽기 오류: {e}")
        else:
            print(f"[StockOcrExtractor] 경고: 마스터 파일 없음 ({self.json_path})")

    def _get_reader(self):
        """EasyOCR 지연 로딩 (메모리 최적화)"""
        if self.reader is None:
            try:
                import easyocr
                self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
            except Exception as e:
                print(f"[OCR] EasyOCR 초기화 오류: {e}")
        return self.reader

    def extract_stocks_from_image(self, image_bytes: bytes) -> List[Dict[str, str]]:
        """
        이미지 바이트 데이터를 받아 인식된 실제 KRX 상장 종목 딕셔너리 리스트 반환
        반환 예시: [{'name': '삼성전자', 'code': '005930'}, ...]
        """
        if not self.stock_dict:
            self._load_stock_master()

        detected_map: Dict[str, str] = {}

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)

            reader = self._get_reader()
            if reader is None:
                return []

            results = reader.readtext(img_np)
            valid_names_set = set(self.stock_names)

            for bbox, text, prob in results:
                clean_text = re.sub(r"[^가-힣a-zA-Z0-9]", "", text).strip()
                if not clean_text or len(clean_text) < 2:
                    continue

                # 1단계: 완전 일치 검증
                if clean_text in valid_names_set:
                    detected_map[clean_text] = self.stock_dict[clean_text]
                    continue

                # 2단계: 부분 일치 검증 (예: 긴 텍스트 안에 상장사 종목명이 포함된 경우)
                matched_partial = False
                for corp_name in self.stock_names:
                    if len(corp_name) >= 3 and corp_name in clean_text:
                        detected_map[corp_name] = self.stock_dict[corp_name]
                        matched_partial = True
                        break

                if matched_partial:
                    continue

                # 3단계: 유사도 기반 퍼지 매칭 (오타/오인식 보정)
                if len(clean_text) >= 3 and prob >= 0.2:
                    close_matches = difflib.get_close_matches(
                        clean_text, 
                        self.stock_names, 
                        n=1, 
                        cutoff=0.72
                    )
                    if close_matches:
                        matched_name = close_matches[0]
                        detected_map[matched_name] = self.stock_dict[matched_name]

        except Exception as e:
            print(f"[OCR] 종목 추출 실패: {e}")

        # 정렬된 리스트로 변환하여 반환
        return [
            {"name": name, "code": code}
            for name, code in sorted(detected_map.items(), key=lambda x: x[0])
        ]