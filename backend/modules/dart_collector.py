import os
import io
import re
import json
import time
import zipfile
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY", "")
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_corp_codes.json")

class DartCollector:
    def __init__(self, api_key: str = DART_API_KEY):
        self.api_key = api_key
        self.corp_code_map = {}
        self._load_corp_codes()

    def _load_corp_codes(self):
        t0 = time.perf_counter()
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.corp_code_map = json.load(f)
                elapsed = time.perf_counter() - t0
                print(f"[DART] 기업 고유번호 {len(self.corp_code_map):,}개 로드 완료 ({elapsed:.2f}s)")
                return
            except Exception as e:
                print(f"[DART] 캐시 읽기 실패: {e}")

        if not self.api_key:
            self.corp_code_map = {
                "삼성전자": "00126380",
                "카카오": "00258801",
                "SK하이닉스": "00164779",
                "현대자동차": "00164742",
                "현대차": "00164742",
                "LG화학": "00356361",
                "LG전자": "00401731",
                "노루페인트": "00607215"
            }
            return
        
        t_dl = time.perf_counter()
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": self.api_key}
        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200 and res.content.startswith(b"PK"):
                with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
                    for filename in zf.namelist():
                        if filename.endswith(".xml"):
                            xml_data = zf.read(filename)
                            root = ET.fromstring(xml_data)
                            for item in root.findall("list"):
                                corp_name = item.findtext("corp_name", "").strip()
                                corp_code = item.findtext("corp_code", "").strip()
                                if corp_name and corp_code:
                                    self.corp_code_map[corp_name] = corp_code
                                    self.corp_code_map[corp_name.replace(" ", "")] = corp_code
                
                if "현대자동차" in self.corp_code_map:
                    self.corp_code_map["현대차"] = self.corp_code_map["현대자동차"]

                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.corp_code_map, f, ensure_ascii=False)

                elapsed = time.perf_counter() - t_dl
                print(f"[DART] 기업 고유번호 {len(self.corp_code_map):,}개 다운로드 및 캐싱 완료 ({elapsed:.2f}s)")
        except Exception as e:
            print(f"[DART] 초기화 실패: {e}")

    def resolve_corp_name(self, stock_name: str) -> str:
        clean_name = stock_name.strip()
        if clean_name in self.corp_code_map:
            return clean_name

        normalized = clean_name.replace(" ", "")
        if normalized in self.corp_code_map:
            return normalized

        pref_pattern = r"((\s*\(우\))|(\s*우B?)|(\s*\d*우[A-Z]?)|(\(.*?우.*?\)))$"
        stripped_name = re.sub(pref_pattern, "", normalized).strip()

        if stripped_name and stripped_name in self.corp_code_map:
            return stripped_name

        alias_map = {
            "현대차": "현대자동차",
            "삼전": "삼성전자",
            "하닉": "SK하이닉스",
            "하이닉스": "SK하이닉스"
        }
        if stripped_name in alias_map and alias_map[stripped_name] in self.corp_code_map:
            return alias_map[stripped_name]

        return stripped_name or clean_name

    def is_valid_company(self, stock_name: str) -> bool:
        resolved = self.resolve_corp_name(stock_name)
        return resolved in self.corp_code_map

    def fetch_recent_disclosures(self, stock_name: str, months: int = 6) -> list[dict]:
        resolved = self.resolve_corp_name(stock_name)
        if resolved not in self.corp_code_map:
            return []

        corp_code = self.corp_code_map[resolved]
        end_de = datetime.now().strftime("%Y%m%d")
        bgn_de = (datetime.now() - timedelta(days=months * 30)).strftime("%Y%m%d")

        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": 100,
            "last_reprt_at": "N"
        }

        try:
            res = requests.get(url, params=params, timeout=6)
            data = res.json()
            if data.get("status") == "000" and "list" in data:
                return [
                    {
                        "report_nm": item.get("report_nm", ""),
                        "rcept_dt": item.get("rcept_dt", ""),
                        "flr_nm": item.get("flr_nm", ""),
                        "rcept_no": item.get("rcept_no", ""),
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no')}"
                    }
                    for item in data["list"]
                ]
        except Exception as e:
            print(f"[DART] 공시 수집 실패: {e}")

        return []

    def fetch_financial_statements(self, stock_name: str) -> list[dict]:
        resolved = self.resolve_corp_name(stock_name)
        if resolved not in self.corp_code_map:
            return []

        corp_code = self.corp_code_map[resolved]
        current_year = datetime.now().year - 1

        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": str(current_year),
            "reprt_code": "11011"
        }

        try:
            res = requests.get(url, params=params, timeout=6)
            data = res.json()
            if data.get("status") != "000":
                params["bsns_year"] = str(current_year - 1)
                res = requests.get(url, params=params, timeout=6)
                data = res.json()

            if data.get("status") == "000" and "list" in data:
                return data["list"]
        except Exception as e:
            print(f"[DART] 재무제표 수집 실패: {e}")

        return []