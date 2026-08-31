import io
import re
from PIL import Image
import numpy as np

class StockOcrExtractor:
    """증권사 앱 스크린샷 이미지 기반 종목명 자동 추출기"""
    def __init__(self, dart_collector):
        self.collector = dart_collector
        self.reader = None

    def _get_reader(self):
        """EasyOCR 지연 로딩 (메모리 최적화)"""
        if self.reader is None:
            try:
                import easyocr
                self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
            except Exception as e:
                print(f"[OCR] EasyOCR 초기화 오류: {e}")
        return self.reader

    def extract_stocks_from_image(self, image_bytes: bytes) -> list[str]:
        """이미지 바이트 데이터를 받아 인식된 실제 상장 종목 리스트 반환"""
        detected_stocks = set()

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)

            reader = self._get_reader()
            if reader is None:
                return []

            # OCR 실행
            results = reader.readtext(img_np)

            # DART에 등록된 전체 종목명 리스트
            valid_corp_names = set(self.collector.corp_code_map.keys())

            for bbox, text, prob in results:
                clean_text = re.sub(r"[^가-힣a-zA-Z0-9]", "", text).strip()
                if not clean_text or len(clean_text) < 2:
                    continue

                # 1. 완전 일치 검증
                if clean_text in valid_corp_names:
                    detected_stocks.add(clean_text)
                    continue

                # 2. 부분 일치/접미사 정리 (예: '삼성전자우' -> '삼성전자' 등)
                for corp_name in valid_corp_names:
                    if corp_name == clean_text or (len(corp_name) >= 3 and corp_name in clean_text):
                        detected_stocks.add(corp_name)

        except Exception as e:
            print(f"[OCR] 종목 추출 실패: {e}")

        # 정렬하여 리스트 반환
        return sorted(list(detected_stocks))