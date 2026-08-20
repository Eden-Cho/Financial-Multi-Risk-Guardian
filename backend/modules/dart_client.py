import os
import sys
import io
import zipfile
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()


class DartClient:
    # 전체 인스턴스가 공유하는 고유번호 캐시
    _corp_code_map = {}

    def __init__(self):
        self.api_key = os.getenv("DART_API_KEY", "").strip()
        
        # 공시 리스크 키워드
        self.risk_keywords = [
            "유상증자", "전환사채", "신주인수권부사채", "감자", "상장폐지",
            "관리종목", "횡령", "배임", "거래정지", "소송", "회생",
            "부도", "불성실공시", "최대주주변경", "주식분할", "주식병합",
            "담보제공", "채무보증", "전환청구권행사"
        ]

    def _load_corp_codes(self):
        """
        OpenDART에서 전체 고유번호 zip 파일을 다운로드하여 메모리에 캐싱합니다.
        """
        if DartClient._corp_code_map:
            return

        if not self.api_key:
            print("[오류] DART_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
            return

        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": self.api_key}

        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                    xml_data = z.read("CORPCODE.xml")
                    root = ET.fromstring(xml_data)
                    for item in root.findall("list"):
                        corp_code = item.findtext("corp_code", "").strip()
                        corp_name = item.findtext("corp_name", "").strip()
                        stock_code = item.findtext("stock_code", "").strip()

                        DartClient._corp_code_map[corp_name] = {
                            "corp_code": corp_code,
                            "stock_code": stock_code
                        }
        except Exception as e:
            print(f"[DART 고유번호 로드 오류] {e}")

    def get_corp_code(self, corp_name: str) -> str:
        """종목명으로 DART 8자리 고유번호를 반환합니다."""
        clean_name = corp_name.strip()
        if not DartClient._corp_code_map:
            self._load_corp_codes()

        # 1. 완전 일치
        if clean_name in DartClient._corp_code_map:
            return DartClient._corp_code_map[clean_name]["corp_code"]

        # 2. 부분 일치
        for name, data in DartClient._corp_code_map.items():
            if clean_name == name or clean_name in name:
                return data["corp_code"]

        return ""

    def get_stock_code_by_name(self, corp_name: str) -> str:
        """종목명으로 6자리 증권 종목코드를 반환합니다."""
        clean_name = corp_name.strip()
        if not DartClient._corp_code_map:
            self._load_corp_codes()

        if clean_name in DartClient._corp_code_map:
            return DartClient._corp_code_map[clean_name]["stock_code"]
        return ""

    def get_recent_disclosures(self, corp_name: str, months: int = 6) -> list[dict]:
        """
        해당 기업의 최근 n개월간 공시 목록을 조회하고 리스크 키워드를 탐지합니다.
        """
        if not self.api_key:
            print("[오류] DART_API_KEY가 없습니다.")
            return []

        corp_code = self.get_corp_code(corp_name)
        if not corp_code:
            print(f"[알림] '{corp_name}'의 DART 기업 고유번호를 찾지 못했습니다.")
            return []

        print(f"[*] '{corp_name}' DART 고유번호 확인: [{corp_code}]")

        today = datetime.today()
        bgn_de = (today - timedelta(days=months * 30)).strftime("%Y%m%d")
        end_de = today.strftime("%Y%m%d")

        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": 15,
            "sort": "date",
            "sort_mth": "desc"
        }

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code != 200:
                print(f"[DART API 오류] 상태코드: {res.status_code}")
                return []

            data = res.json()
            if data.get("status") != "000":
                print(f"[DART 응답 메시지] {data.get('message', '조회 내역 없음')}")
                return []

            raw_list = data.get("list", [])
            disclosure_list = []

            for item in raw_list:
                report_nm = item.get("report_nm", "").strip()
                rcept_dt = item.get("rcept_dt", "")
                rcept_no = item.get("rcept_no", "")
                flr_nm = item.get("flr_nm", "")

                # 공시 상세 링크 생성
                link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else ""

                # 리스크 키워드 탐지
                detected_risks = [k for k in self.risk_keywords if k in report_nm]
                is_risk = len(detected_risks) > 0

                disclosure_list.append({
                    "report_nm": report_nm,
                    "rcept_dt": rcept_dt,
                    "rcept_no": rcept_no,
                    "flr_nm": flr_nm,
                    "link": link,
                    "is_risk": is_risk,
                    "detected_risks": detected_risks
                })

            return disclosure_list

        except Exception as e:
            print(f"[DART 공시 수집 예외] {e}")
            return []


if __name__ == "__main__":
    dart = DartClient()
    
    test_corp = "모아데이타"
    print(f"=== [{test_corp}] DART 전자공시 실시간 수집 & 리스크 진단 ===")
    
    results = dart.get_recent_disclosures(corp_name=test_corp, months=6)
    
    if not results:
        print("수집된 공시가 없습니다.")
    else:
        for idx, item in enumerate(results, 1):
            risk_badge = f"🚨 [리스크 감지: {', '.join(item['detected_risks'])}]" if item["is_risk"] else "✅ [일반]"
            print(f"\n{idx}. {risk_badge} {item['report_nm']}")
            print(f"   - 제출인: {item['flr_nm']} | 접수일자: {item['rcept_dt']}")
            print(f"   - 공시링크: {item['link']}")