import os
import sys
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()


class NewsCrawler:
    _stock_code_cache = {}

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://finance.naver.com/"
        }
        
        self.risk_keywords = [
            "유상증자", "전환사채", "CB", "BW", "감자", "상장폐지", 
            "관리종목", "횡령", "배임", "거래정지", "소송", "적자전환", 
            "벌금", "압수수색", "회생", "부도", "불성실공시", "경영권 분쟁",
            "오버행", "주가급락", "디폴트", "주식병합", "실적악화"
        ]

    def _load_krx_stock_codes(self):
        """KRX 상장사 목록에서 종목명과 6자리 숫자 종목코드를 정확히 매핑합니다."""
        if NewsCrawler._stock_code_cache:
            return

        try:
            url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
            res = requests.get(url, timeout=10)
            html_text = res.content.decode("euc-kr", errors="ignore")
            
            soup = BeautifulSoup(html_text, "html.parser")
            rows = soup.select("table tr")
            
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    corp = cols[0].get_text(strip=True)
                    # 행 안의 모든 열을 돌면서 '순수 숫자'로 된 종목코드 열을 찾음
                    for col in cols[1:]:
                        text = col.get_text(strip=True)
                        digits = re.sub(r"[^0-9]", "", text)
                        if digits:
                            code = digits.zfill(6)
                            NewsCrawler._stock_code_cache[corp] = code
                            break
        except Exception as e:
            print(f"[KRX 종목코드 로드 오류] {e}")

    def get_stock_code(self, corp_name: str) -> str:
        clean_name = corp_name.strip()
        
        if not NewsCrawler._stock_code_cache:
            self._load_krx_stock_codes()

        # 1. 완전 일치
        if clean_name in NewsCrawler._stock_code_cache:
            return NewsCrawler._stock_code_cache[clean_name]

        # 2. 부분 일치
        for name, code in NewsCrawler._stock_code_cache.items():
            if clean_name in name or name in clean_name:
                return code

        return ""

    def crawl_finance_news(self, keyword_or_code: str, max_count: int = 5) -> list[dict]:
        if str(keyword_or_code).isdigit() and len(str(keyword_or_code)) == 6:
            stock_code = str(keyword_or_code)
            corp_display = stock_code
        else:
            corp_display = keyword_or_code
            stock_code = self.get_stock_code(keyword_or_code)

        if not stock_code or not stock_code.isdigit():
            print(f"[알림] '{keyword_or_code}'의 유효한 종목코드를 찾지 못했습니다.")
            return []

        print(f"[*] '{corp_display}' -> 종목코드 [{stock_code}] 연결 성공")
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
        news_list = []

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            res.encoding = "euc-kr"

            if res.status_code != 200:
                print(f"[오류] 네이버 금융 응답 실패 (상태코드: {res.status_code})")
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table.type5 tbody tr")

            for row in rows:
                if len(news_list) >= max_count:
                    break

                title_td = row.select_one("td.title")
                if not title_td:
                    continue

                a_tag = title_td.select_one("a")
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                raw_href = a_tag.get("href", "")
                link = urllib.parse.urljoin("https://finance.naver.com", raw_href)

                press_td = row.select_one("td.info")
                press = press_td.get_text(strip=True) if press_td else "언론사"

                date_td = row.select_one("td.date")
                pub_date = date_td.get_text(strip=True) if date_td else ""

                detected_risks = [k for k in self.risk_keywords if k in title]
                news_list.append({
                    "title": title,
                    "link": link,
                    "press": press,
                    "pub_date": pub_date,
                    "is_risk": len(detected_risks) > 0,
                    "detected_risks": detected_risks
                })

            return news_list

        except Exception as e:
            print(f"[크롤링 에러] {e}")
            return []


if __name__ == "__main__":
    crawler = NewsCrawler()
    
    test_corp = "모아데이타"
    print(f"=== [{test_corp}] 네이버 금융 실시간 뉴스 & 리스크 시그널 수집 ===")
    
    results = crawler.crawl_finance_news(keyword_or_code=test_corp, max_count=5)
    
    if not results:
        print("수집된 뉴스가 없습니다.")
    else:
        for idx, news in enumerate(results, 1):
            risk_badge = f"🚨 [리스크 감지: {', '.join(news['detected_risks'])}]" if news["is_risk"] else "✅ [일반]"
            print(f"\n{idx}. {risk_badge} {news['title']}")
            print(f"   - 언론사/일시: {news['press']} | {news['pub_date']}")
            print(f"   - 링크: {news['link']}")