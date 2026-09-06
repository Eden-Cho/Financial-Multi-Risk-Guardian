"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/news_crawler.py
- 기능:
    1. 구글 뉴스 공식 RSS 검색 피드를 통한 실시간 기사 수집 (차단 회피)
    2. 중대 리스크 키워드 탐지 및 점수 산출
    3. 프론트엔드 노출용 핵심 기사 헤드라인(top_headlines) 매핑 지원
==============================================================================
"""
"""
==============================================================================
[미디어/평판 리스크 가중치 산정 기준]

본 리스크 스코어링 체계는 한국거래소(KRX) 유가증권/코스닥 상장규정의
'상장적격성 실질심사 사유' 및 '시장조치 기준'을 기반으로 설계되었습니다.

1. Tier 1: 상장 존폐 및 거래정지 직결 리스크 (35 ~ 45점)
   - 근거: KRX 상장규정 상 즉각적인 '매매거래정지' 및 '상장폐지 실질심사' 개시 사유.
   - 투자자 입장에서 원금 회수 불가(환금성 상실)로 이어지는 최고 위험군.
   - 키워드: 상장폐지(45), 거래정지(40), 횡령·배임(35), 압수수색(35), 회계부정(35)

2. Tier 2: 경영권 구조 격변 및 규제 제재 리스크 (25 ~ 30점)
   - 근거: 불성실공시 벌점 누적(관리종목 지정 위험), 의결권 가처분 소송, 
     지배구조 불안정으로 인한 극단적 주가 변동성 유발 요인.
   - 키워드: 불성실공시(30), 경영권(25), 표싸움·표대결(25), 가처분(25), 구속(25), 감사의견(25), 하한가(25)

3. Tier 3: 사법 리스크 및 단기 충격 노이즈 (15 ~ 20점)
   - 근거: 금융당국 과징금, 어닝 쇼크, 민·형사 소송 등 펀더멘털 일시적 훼손 위험.
   - 키워드: 수사(20), 고발(20), 과징금·제재(20), 어닝쇼크(20), 지분 경쟁(20), 소송(15), 갈등(15), 의결권(15)

4. Tier 4: 통상적 실적 둔화 및 경기 순환 노이즈 (10 ~ 15점)
   - 근거: 경기민감주 또는 R&D 중심 바이오·성장주의 통상적 손실 구간.
   - 키워드: 적자(15), 체불(15)
==============================================================================
"""

import urllib.parse
import xml.etree.ElementTree as ET
import html
import re
import requests
from typing import List, Dict, Any

HIGH_RISK_KEYWORDS = {
    # 경영권 / 분쟁
    "경영권": 25,
    "표싸움": 25,
    "표대결": 25,
    "지분 경쟁": 20,
    "갈등": 15,
    "가처분": 25,
    "의결권": 15,
    
    # 사법 / 수사
    "횡령": 35,
    "배임": 35,
    "압수수색": 35,
    "구속": 25,
    "소송": 15,
    "고발": 20,
    "수사": 20,
    
    # 상장 / 회계 / 재무
    "거래정지": 40,
    "상장폐지": 45,
    "회계부정": 35,
    "감사의견": 25,
    "적자": 15,
    "어닝쇼크": 20,
    "하한가": 25,
    "과징금": 20,
    "제재": 20,
    "불성실공시": 30
}

class NewsRiskAnalyzer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def _clean_text(self, text: str) -> str:
        """HTML 태그 및 엔티티 제거"""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        return html.unescape(clean).strip()

    def fetch_latest_news(self, stock_name: str, max_items: int = 15) -> List[Dict[str, str]]:
        """구글 뉴스 RSS 피드 파싱 (차단 없이 가장 신뢰성 높음)"""
        encoded_query = urllib.parse.quote(f"{stock_name}")
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

        news_list = []
        try:
            res = requests.get(rss_url, headers=self.headers, timeout=5)
            if res.status_code != 200:
                return news_list

            root = ET.fromstring(res.content)
            items = root.findall("./channel/item")

            for item in items[:max_items]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pubdate_elem = item.find("pubDate")

                raw_title = title_elem.text if title_elem is not None else ""
                clean_title = self._clean_text(raw_title)
                link = link_elem.text if link_elem is not None else ""
                pub_date = pubdate_elem.text if pubdate_elem is not None else ""

                if clean_title:
                    # 언론사명 분리 추출 (구글 RSS 제목은 보통 '제목 - 언론사명' 형태로 구성됨)
                    press_name = "언론사"
                    if "-" in clean_title:
                        parts = clean_title.rsplit("-", 1)
                        if len(parts) == 2 and len(parts[1].strip()) < 15:
                            clean_title = parts[0].strip()
                            press_name = parts[1].strip()

                    news_list.append({
                        "title": clean_title,
                        "url": link,
                        "link": link,
                        "press": press_name,
                        "date": pub_date,
                        "pub_date": pub_date
                    })
        except Exception as e:
            print(f"[NewsCrawler] RSS 수집 오류 ({stock_name}): {e}")

        return news_list

    def analyze_news_risk(self, stock_name: str, sentiment_analyzer=None) -> Dict[str, Any]:
        news_items = self.fetch_latest_news(stock_name, max_items=15)
        
        if not news_items:
            return {
                "stock_name": stock_name,
                "news_risk_score": 0.0,
                "risk_level": "LOW",
                "detected_keywords": [],
                "flagged_titles": [],
                "total_fetched": 0,
                "sample_titles": [],
                "top_headlines": [],
                "summary_comment": f"'{stock_name}' 관련 최신 기사 피드를 확인할 수 없습니다."
            }

        detected_kw_map = {}
        flagged_titles = []
        top_headlines = [] # 프론트엔드 연동용 뉴스 상세 리스트 배열 초기화

        for item in news_items:
            title = item["title"]
            matched_for_this = []
            for kw, weight in HIGH_RISK_KEYWORDS.items():
                if kw in title:
                    detected_kw_map[kw] = max(detected_kw_map.get(kw, 0), weight)
                    matched_for_this.append(kw)
            
            if matched_for_this:
                flagged_titles.append(f"[{','.join(matched_for_this)}] {title}")

            # [추가] 허깅페이스 감성 분석기 연동 및 개별 기사 감성 라벨 부여
            sentiment = "중립"
            if sentiment_analyzer:
                try:
                    res = sentiment_analyzer.analyze_single(title)
                    sentiment = res.get("label", "중립")
                except Exception:
                    pass

            # [추가] 사용자가 클릭해 원문을 볼 수 있도록 링크(url)와 감성 정보 매핑
            top_headlines.append({
                "title": title,
                "link": item["url"],
                "url": item["url"],
                "press": item["press"],
                "pub_date": item["date"][:16] if item["date"] else "",
                "sentiment": sentiment
            })

        raw_score = sum(detected_kw_map.values())
        final_risk_score = round(min(100.0, float(raw_score)), 1)
        detected_keywords = list(detected_kw_map.keys())

        if final_risk_score >= 40:
            level = "HIGH"
            comment = f"주의: 최근 기사에서 {', '.join(detected_keywords)} 키워드가 감지되었습니다."
        elif final_risk_score >= 15:
            level = "MEDIUM"
            comment = f"노이즈 관측: {', '.join(detected_keywords)} 관련 기사가 확인됩니다."
        else:
            level = "LOW"
            comment = "최근 주요 언론 보도에서 법적/경영적 위험 키워드가 포착되지 않았습니다."

        return {
            "stock_name": stock_name,
            "news_risk_score": final_risk_score,
            "risk_level": level,
            "detected_keywords": detected_keywords,
            "flagged_titles": flagged_titles,
            "total_fetched": len(news_items),
            "sample_titles": [item["title"] for item in news_items[:3]],
            "top_headlines": top_headlines[:4],  # [수정] 원문 링크와 감성이 포함된 상위 4건의 헤드라인 전송
            "summary_comment": comment
        }