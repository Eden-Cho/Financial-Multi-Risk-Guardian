import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()

# 모듈 불러오기
try:
    from backend.modules.dart_client import DartClient
except ImportError:
    DartClient = None

from backend.modules.news_crawler import NewsCrawler


class RiskGuardianPipeline:
    def __init__(self):
        self.news_crawler = NewsCrawler()
        self.dart_client = DartClient() if DartClient else None

    def analyze_company(self, corp_name: str, max_news: int = 5):
        print("\n" + "=" * 60)
        print(f"🛡️ [Financial Multi-Risk Guardian] '{corp_name}' 통합 리스크 진단")
        print("=" * 60)

        # 1. 네이버 금융 뉴스 및 시그널 수집
        print(f"\n[1/2] 📰 최신 금융 뉴스 및 리스크 시그널 수집 중...")
        news_results = self.news_crawler.crawl_finance_news(corp_name, max_count=max_news)
        
        detected_news_risks = []
        if news_results:
            for idx, news in enumerate(news_results, 1):
                badge = f"🚨 [감지: {', '.join(news['detected_risks'])}]" if news["is_risk"] else "✅ [일반]"
                print(f"  {idx}. {badge} {news['title']}")
                print(f"     언론사: {news['press']} | 일시: {news['pub_date']}")
                if news["is_risk"]:
                    detected_news_risks.extend(news["detected_risks"])
        else:
            print("  ℹ️ 최근 뉴스가 없거나 수집되지 않았습니다.")

        # 2. DART 공시 수집 (DART 모듈 연동 시)
        print(f"\n[2/2] 📑 DART 전자공시 데이터 수집 중...")
        dart_disclosures = []
        if self.dart_client and hasattr(self.dart_client, "get_recent_disclosures"):
            try:
                dart_disclosures = self.dart_client.get_recent_disclosures(corp_name)
                print(f"  -> 공시 {len(dart_disclosures)}건 수집 완료")
            except Exception as e:
                print(f"  ⚠️ DART 공시 조회 중 오류: {e}")
        else:
            print("  ℹ️ DART 모듈 연동 준비 중 (뉴스 데이터 우선 분석)")

        # 3. 종합 요약 브리핑
        print("\n" + "-" * 60)
        print("📊 [종합 리스크 진단 요약]")
        print("-" * 60)
        
        all_risks = list(set(detected_news_risks))
        if all_risks:
            print(f"🚨 위험 시그널 감지됨: {', '.join(all_risks)}")
            print(f"⚠️ 권고사항: 해당 종목의 자본 변동 및 악재성 키워드에 대한 상세 공시 검토가 필요합니다.")
        else:
            print("✅ 특이 리스크 시그널이 감지되지 않았습니다. (안정권)")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    # 분석 대상 종목 지정
    target_corp = "모아데이타"
    
    guardian = RiskGuardianPipeline()
    guardian.analyze_company(corp_name=target_corp)