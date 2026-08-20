import os
import sys
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from backend.modules.dart_client import DartClient
from backend.modules.news_crawler import NewsCrawler
from backend.modules.anonymizer import Anonymizer
from backend.modules.slm_engine import SLMEngine


class RiskAnalyzer:
    def __init__(self):
        self.dart_client = DartClient()
        self.news_crawler = NewsCrawler()
        self.anonymizer = Anonymizer()
        self.slm_engine = SLMEngine()

    def analyze(self, stock_name: str):
        """
        종목명을 입력받아 DART 공시와 뉴스를 수집/비식별화하고,
        SLM 엔진을 통해 다차원 리스크 리포트를 생성하여 반환합니다.
        """
        if not stock_name or not stock_name.strip():
            stock_name = "모아데이타"
        stock_name = stock_name.strip()

        print(f"\n🔍 [{stock_name}] 다차원 리스크 수집 및 SLM 정밀 진단 시작...")

        # 1. 원천 데이터 실시간 수집
        raw_dart_items = self.dart_client.get_recent_disclosures(corp_name=stock_name, months=6)
        raw_news_items = self.news_crawler.crawl_finance_news(keyword_or_code=stock_name, max_count=5)

        # 2. 개인정보 비식별화 (Privacy Protection)
        dart_items = self.anonymizer.anonymize_disclosures(raw_dart_items)
        news_items = []
        for n in raw_news_items:
            clean_news = n.copy()
            clean_news["title"] = self.anonymizer.mask_text(clean_news["title"])
            clean_news["press"] = self.anonymizer.mask_text(clean_news.get("press", ""))
            news_items.append(clean_news)

        # 3. 5대 리스크 축별 위험도(0~100) 평가
        risk_dim = {
            "공시/오버행(CB·BW)": 10,
            "언론 뉴스 악재": 10,
            "지배구조/오너리스크": 10,
            "관리종목/상폐우려": 10,
            "자본변동/유상증자": 10
        }

        for item in dart_items:
            rep = item.get("report_nm", "")
            if "전환사채" in rep or "신주인수권부사채" in rep or "전환청구권" in rep:
                risk_dim["공시/오버행(CB·BW)"] = min(100, risk_dim["공시/오버행(CB·BW)"] + 30)
            if "유상증자" in rep or "주식병합" in rep or "감자" in rep or "소액공모" in rep:
                risk_dim["자본변동/유상증자"] = min(100, risk_dim["자본변동/유상증자"] + 35)
            if "최대주주변경" in rep or "담보제공" in rep or "횡령" in rep or "배임" in rep:
                risk_dim["지배구조/오너리스크"] = min(100, risk_dim["지배구조/오너리스크"] + 40)
            if "관리종목" in rep or "상장폐지" in rep or "거래정지" in rep or "불성실공시" in rep:
                risk_dim["관리종목/상폐우려"] = min(100, risk_dim["관리종목/상폐우려"] + 50)

        for news in news_items:
            if news.get("is_risk"):
                risks = news.get("detected_risks", [])
                risk_dim["언론 뉴스 악재"] = min(100, risk_dim["언론 뉴스 악재"] + 25 * len(risks))

        # 4. 안전 점수(Safety Score) 산출
        avg_risk = sum(risk_dim.values()) / len(risk_dim)
        safety_score = max(5, int(100 - avg_risk))

        if safety_score >= 80:
            status = "안전 구간"
        elif safety_score >= 60:
            status = "주의 구간"
        elif safety_score >= 40:
            status = "경고 구간"
        else:
            status = "위험 (투자유의)"

        score_info = {
            "score": safety_score,
            "status": status,
            "stock_name": stock_name,
            "dart_count": len(dart_items),
            "news_count": len(news_items)
        }

        # 5. Radar Chart용 DataFrame
        radar_data = pd.DataFrame({
            "r": list(risk_dim.values()),
            "theta": list(risk_dim.keys())
        })

        # 6. SLM 정밀 보고서 생성
        report_text = self.slm_engine.generate_risk_report(
            stock_name=stock_name,
            safety_score=safety_score,
            risk_dim=risk_dim,
            dart_items=dart_items,
            news_items=news_items
        )

        return score_info, radar_data, report_text


if __name__ == "__main__":
    analyzer = RiskAnalyzer()
    score_info, radar_df, report = analyzer.analyze("모아데이타")
    
    print("\n" + "=" * 50)
    print("📊 1. Score Info")
    print(score_info)
    print("\n📈 2. Radar Chart Data")
    print(radar_df)
    print("\n📝 3. Generated Report Text")
    print(report)