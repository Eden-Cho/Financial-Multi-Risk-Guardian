import time
import logging
from backend.modules.dart_collector import DartCollector
from backend.modules.storage import StorageManager

logger = logging.getLogger("BatchSync")

DEFAULT_CORE_STOCKS = [
    "삼성전자", "SK하이닉스", "LG에너지솔루션", "삼성바이오로직스", "현대차"
]

class BatchSyncManager:
    def __init__(self):
        self.collector = DartCollector()
        self.storage = StorageManager()

    def sync_financials_for_targets(self, extra_targets: list[str] = None):
        """기본 종목 + 모든 사용자 관심 종목의 고유 합집합을 도출하여 DART 재무제표 1회씩 동기화"""
        user_targets = self.storage.get_all_unique_watchlist_stocks()
        
        # 중복 제거된 전체 대상 목록 구성
        combined_set = set(DEFAULT_CORE_STOCKS)
        if user_targets:
            combined_set.update(user_targets)
        if extra_targets:
            combined_set.update(extra_targets)
            
        target_list = list(combined_set)
        print(f"\n📦 [BatchSync] 전체 고유 대상 {len(target_list)}개 종목 (사용자 등록 종목 포함) 동기화 시작...")
        
        success_count = 0
        t0 = time.perf_counter()

        for stock in target_list:
            try:
                # 7일 이내 수집된 재무 데이터가 이미 있으면 Skip (API 절약)
                cached = self.storage.get_financial_data(stock, max_age_seconds=86400 * 7)
                if cached:
                    continue

                fin_statements = self.collector.fetch_financial_statements(stock)
                if fin_statements:
                    self.storage.save_financial_data(stock, fin_statements)
                    success_count += 1
                    print(f"  └ [동기화 완료] {stock}")
                
                # DART API 제한 방지 딜레이
                time.sleep(0.3)
            except Exception as e:
                print(f"  └ [동기화 실패] {stock}: {e}")

        elapsed = time.perf_counter() - t0
        print(f"📦 [BatchSync] 동기화 종료 (신규 적재: {success_count}건, 총 소요시간: {elapsed:.2f}s)\n")