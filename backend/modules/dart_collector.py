"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/dart_collector.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할:
    1. Open DART API 연동 및 고유번호(corp_code) 매핑 관리 (자동 정규화 및 유사도 매칭 적용)
    2. 최근 공시 목록 및 표준 재무제표(BS/IS) 수집
    3. [1순위 고도화] 전환사채(CB) / 신주인수권부사채(BW) / 유상증자 공시의
        본문 원문 XML/HTML 파싱을 통한 실제 권면총액, 전환가액, 리픽싱 최저한도 추출
    4. [Rate Limiting] DART API 호출 간 최소 지연(Throttle) 보장으로 429 차단
==============================================================================
"""

import os
import re
import io
import time
import json
import zipfile
import requests
import difflib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY", "")
DART_BASE_URL = "https://opendart.fss.or.kr/api"


class DartCollector:
    """
    Open DART API와 통신하여 기업 고유번호, 전자공시 목록, 재무제표 및
    메자닌 사채 공시 본문 상세 스펙을 정밀 추출하는 데이터 수집 엔진
    """

    def __init__(self, api_key: str = DART_API_KEY):
        """
        [함수 역할]
        DART API 키를 등록하고, 기업명-고유번호 매핑 캐시 및 쓰로틀링 타임스탬프를 초기화합니다.
        """
        self.api_key = api_key
        self.corp_code_cache: Dict[str, str] = {}
        self.last_call_time = 0.0
        self.min_interval = 0.25  # 초당 최대 4회 이하로 제한하여 429 차단
        self._load_corp_codes()

    def _throttle(self):
        """DART API 호출 간 최소 간격을 강제하는 Rate Limiter"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

    def _load_corp_codes(self):
        """DART 전체 고유번호 목록(CORPCODE.zip) 다운로드 및 정규화 인메모리 색인 (1회 수행)"""
        if not self.api_key:
            return

        cache_file = "data/corp_codes.json"
        raw_dict = {}

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw_dict = json.load(f)
            except Exception:
                pass

        if not raw_dict:
            try:
                self._throttle()
                url = f"{DART_BASE_URL}/corpCode.xml"
                resp = requests.get(url, params={"crtfc_key": self.api_key}, timeout=30)
                if resp.status_code == 200 and resp.content[:2] == b"PK":
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                        xml_content = z.read("CORPCODE.xml")
                        root = ET.fromstring(xml_content)
                        for item in root.findall("list"):
                            corp_name = item.findtext("corp_name", "").strip()
                            corp_code = item.findtext("corp_code", "").strip()
                            if corp_name and corp_code:
                                raw_dict[corp_name] = corp_code

                    os.makedirs("data", exist_ok=True)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(raw_dict, f, ensure_ascii=False)
            except Exception as e:
                print(f"[DartCollector] corpCode 로드 실패: {e}")

        # [자동 정규화 매핑] 대소문자 무시, 공백 및 특수문자 제거한 키값으로 인덱싱
        self.corp_code_cache = {}
        for corp_name, corp_code in raw_dict.items():
            clean_name = re.sub(r'[^가-힣a-z0-9]', '', corp_name.strip().lower())
            if clean_name:
                self.corp_code_cache[clean_name] = corp_code
            # 원본 이름도 추가 보존
            self.corp_code_cache[corp_name.strip().lower()] = corp_code

    def get_corp_code(self, stock_name: str) -> Optional[str]:
        """기업명에 대응하는 DART 8자리 고유번호 조회 (자동 유사도 및 정규화 매칭)"""
        if not stock_name:
            return None
            
        clean_key = re.sub(r'[^가-힣a-z0-9]', '', stock_name.strip().lower())
        
        # 1. 정규화된 정확한 키가 존재하면 바로 반환
        if clean_key in self.corp_code_cache:
            return self.corp_code_cache[clean_key]
            
        original_lower = stock_name.strip().lower()
        if original_lower in self.corp_code_cache:
            return self.corp_code_cache[original_lower]

        all_keys = list(self.corp_code_cache.keys())

        # 2. 부분 일치 검색 (예: '하이닉스' 입력 시 'sk하이닉스' 탐색)
        matching_keys = [k for k in all_keys if clean_key in k or k in clean_key]
        if matching_keys:
            best_match = min(matching_keys, key=len)
            return self.corp_code_cache[best_match]

        # 3. 오타나 축약어 대응 유사도 검사 (difflib)
        close_matches = difflib.get_close_matches(clean_key, all_keys, n=1, cutoff=0.5)
        if close_matches:
            return self.corp_code_cache[close_matches[0]]

        return None

    def is_valid_company(self, stock_name: str) -> bool:
        """DART에 등록된 유효 상장사 여부 검증 (유연한 퍼지 매칭 적용)"""
        if not self.corp_code_cache:
            return True
        return self.get_corp_code(stock_name) is not None

    def fetch_recent_disclosures(self, stock_name: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        [함수 역할]
        지정 기업의 최근 공시 목록을 조회하고, 각 공시의 원문 링크를 매핑합니다.
        """
        corp_code = self.get_corp_code(stock_name)
        if not corp_code:
            return []

        self._throttle()
        end_date = datetime.now().strftime("%Y%m%d")
        bgn_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        url = f"{DART_BASE_URL}/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_date,
            "end_de": end_date,
            "page_no": 1,
            "page_count": count
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "000":
                disclosures = []
                for item in data.get("list", []):
                    rcept_no = item.get("rcept_no")
                    disclosures.append({
                        "corp_name": item.get("corp_name"),
                        "report_nm": item.get("report_nm"),
                        "rcept_no": rcept_no,
                        "flr_nm": item.get("flr_nm"),
                        "rcept_dt": item.get("rcept_dt"),
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                    })
                return disclosures
        except Exception as e:
            print(f"[DartCollector] 공시 목록 조회 실패: {e}")
        return []

    def parse_mezzanine_document_details(self, rcept_no: str) -> Dict[str, Any]:
        """
        [함수 역할 - 1순위 핵심]
        공시 문서 번호(rcept_no)로 원문 XML/HTML을 다운로드하여
        전환사채/신주인수권의 '권면총액', '전환가액', '최저 리픽싱 한도'를 정규표현식으로 정밀 추출합니다.
        """
        if not rcept_no or rcept_no == "NONE":
            return {}

        self._throttle()
        url = f"{DART_BASE_URL}/document.xml"
        params = {"crtfc_key": self.api_key, "rcept_no": rcept_no}

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200 or resp.content[:2] != b"PK":
                return {}

            text_content = ""
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                for filename in z.namelist():
                    if filename.endswith(".xml") or filename.endswith(".html"):
                        text_content += z.read(filename).decode("utf-8", errors="ignore")

            # 1. 사채의 권면(전자등록)총액 추출
            amount_match = re.search(r"(?:권면총액|전자등록총액|발행금액)[^\d]{1,30}([\d,]{5,20})\s*(?:원)?", text_content)
            extracted_amount = 0
            if amount_match:
                extracted_amount = int(amount_match.group(1).replace(",", ""))

            # 2. 전환가액 / 행사가액 추출
            conv_price_match = re.search(r"(?:전환가액|행사가액|발행가액)[^\d]{1,25}([\d,]{3,10})\s*원", text_content)
            extracted_conv_price = "공시 참조"
            if conv_price_match:
                extracted_conv_price = f"{conv_price_match.group(1)}원"

            # 3. 최저 조정가액 (리픽싱 하한선 비율 - 보통 70%)
            refix_match = re.search(r"최저\s*(?:조정가액|발행가액)[^\d]{1,30}([\d,]{3,10})\s*원", text_content)
            refix_ratio_match = re.search(r"(?:조정가액은|하한선은)[^\d]{1,20}(\d{2})%\s*이상", text_content)
            refix_str = "최대 70% 하향 리픽싱 가능"
            if refix_match:
                refix_str = f"최저 조정가액: {refix_match.group(1)}원"
            elif refix_ratio_match:
                refix_str = f"최저 리픽싱 하한선: {refix_ratio_match.group(1)}%"

            return {
                "rcept_no": rcept_no,
                "parsed_amount": extracted_amount,
                "conv_price": extracted_conv_price,
                "refixing_floor": refix_str
            }
        except Exception as e:
            print(f"[DartCollector] 본문 정밀 파싱 오류 ({rcept_no}): {e}")
            return {}

    def fetch_financial_statements(self, stock_name: str, year: int = None) -> List[Dict[str, Any]]:
        """표준 재무제표(BS/IS) 수집"""
        corp_code = self.get_corp_code(stock_name)
        if not corp_code:
            return []

        if not year:
            year = datetime.now().year - 1

        self._throttle()
        url = f"{DART_BASE_URL}/fnlttSinglAcntAll.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",  # 사업보고서
            "fs_div": "CFS"         # 연결재무제표 우선
        }

        try:
            resp = requests.get(url, params=params, timeout=12)
            data = resp.json()
            if data.get("status") == "000":
                return data.get("list", [])
            elif data.get("status") == "013":
                # 연결이 없는 경우 개별(OFS)로 재조회
                params["fs_div"] = "OFS"
                self._throttle()
                resp2 = requests.get(url, params=params, timeout=12)
                data2 = resp2.json()
                if data2.get("status") == "000":
                    return data2.get("list", [])
        except Exception as e:
            print(f"[DartCollector] 재무제표 수집 실패: {e}")
        return []