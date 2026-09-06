"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/price_collector.py
- 기능:
    1. FinanceDataReader를 이용해 한국거래소(KRX) 전 종목 리스트 연동
    2. 컬럼명 변동에 안전한 동적 티커 탐색 로직 적용
    3. 실시간 주가(OHLCV) 및 등락률 조회
==============================================================================
"""

import FinanceDataReader as fdr
import pandas as pd
from typing import Dict, Any

class StockPriceCollector:
    def __init__(self):
        try:
            self.krx_stocks = fdr.StockListing('KRX')
        except Exception as e:
            print(f"[PriceCollector 경고] KRX 종목 리스트 로드 실패: {e}")
            self.krx_stocks = pd.DataFrame()

    def fetch_price_info(self, stock_name: str) -> Dict[str, Any]:
        clean_name = stock_name.strip()
        ticker = "005930"  # 기본값 삼성전자

        # 수동 폴백 매핑 먼저 확인
        fallback_map = {
            # 대형 IT / 반도체
            "삼성전자": "005930",
            "SK하이닉스": "000660",
            "삼성전자우": "005935",
            "삼성전기": "009150",
            
            # 자동차 / 중공업 / 방산
            "현대차": "005380",
            "기아": "000270",
            "현대모비스": "012330",
            "HD현대중공업": "329180",
            "한화에어로스페이스": "012450",
            "두산에너빌리티": "034020",
            
            # 플랫폼 / IT 서비스
            "카카오": "035720",
            "NAVER": "035420",
            "SK스퀘어": "402340",
            
            # 2차전지 / 에너지 / 소재
            "LG에너지솔루션": "373220",
            "삼성SDI": "006400",
            "에코프로": "086520",
            "에코프로비엠": "247540",
            "고려아연": "010130",
            "POSCO홀딩스": "005490",
            
            # 바이오 / 제약
            "삼성바이오로직스": "207940",
            "셀트리온": "068270",
            "알테오젠": "196170",
            
            # 금융 / 지주사
            "KB금융": "105560",
            "신한지주": "055550",
            "하나금융지주": "086790",
            "메리츠금융지주": "138040",
            "삼성물산": "028260",
            "삼성생명": "032830",
            "SK": "034730",
            
            # 기타 주요 관심 / 시연 종목
            "파두": "440110",
            "모아데이타": "288980",
            "노루페인트": "090350",
            "한화": "000880",
            "풍산": "103140",
            "셀트리온제약": "068760",
            "LG화학": "051910",
            "HD현대": "267250",
            "KT": "030200",
            "SK텔레콤": "017670"
        }
        
        if clean_name in fallback_map:
            ticker = fallback_map[clean_name]
        elif not self.krx_stocks.empty:
            try:
                # 대소문자 무관하게 종목명 컬럼과 코드 컬럼 찾기
                name_col = next((c for c in self.krx_stocks.columns if c.lower() in ['name', '종목명', 'korname']), None)
                code_col = next((c for c in self.krx_stocks.columns if c.lower() in ['symbol', 'code', 'ticker', '종목코드']), None)

                if name_col and code_col:
                    match = self.krx_stocks[self.krx_stocks[name_col] == clean_name]
                    if not match.empty:
                        ticker = str(match.iloc[0][code_col]).zfill(6)
                    else:
                        match_partial = self.krx_stocks[self.krx_stocks[name_col].str.contains(clean_name, na=False)]
                        if not match_partial.empty:
                            ticker = str(match_partial.iloc[0][code_col]).zfill(6)
                            clean_name = str(match_partial.iloc[0][name_col])
            except Exception as e:
                print(f"[PriceCollector] 티커 동적 매핑 중 예외 발생: {e}")

        # 주가 데이터 수집
        try:
            df = fdr.DataReader(ticker)
            if df.empty:
                raise ValueError("시세 데이터가 비어 있습니다.")

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = int(latest['Close'])
            prev_price = int(prev['Close'])
            diff = current_price - prev_price
            change_pct = round((diff / prev_price) * 100, 2) if prev_price != 0 else 0.0

            is_up = diff > 0
            is_down = diff < 0
            
            if is_up:
                change_str = f"+{diff:,}원 (+{change_pct}%)"
            elif is_down:
                change_str = f"{diff:,}원 ({change_pct}%)"
            else:
                change_str = "0원 (0.0%)"

            return {
                "code": ticker,
                "display_name": clean_name,
                "current_price": f"{current_price:,}원",
                "change_str": change_str,
                "is_up": is_up,
                "is_down": is_down,
                "has_price": True,
                "market_status": "실시간 거래소 시세 연동",
                "has_preferred_family": False,
                "related_pref_stocks": []
            }

        except Exception as e:
            print(f"[PriceCollector] 시세 수집 오류 ({clean_name}, 티커: {ticker}): {e}")
            return {
                "code": ticker,
                "display_name": clean_name,
                "current_price": "조회 불가",
                "change_str": "-",
                "is_up": False,
                "is_down": False,
                "has_price": False,
                "market_status": "데이터 수집 실패",
                "has_preferred_family": False,
                "related_pref_stocks": []
            }