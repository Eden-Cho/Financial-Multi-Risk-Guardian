"""
==============================================================================
[수급 건전성 및 메이저 이탈 리스크 산정 기준]

네이버 증권 일별 외국인/기관 순매매 공식 집계표(frgn.naver)를 직접 파싱하여 
최근 5영업일 순매매 연속 이탈 및 누적 매도세를 정량화합니다.

1. 메이저 수급 이탈 (Smart Money Outflow) - 최대 100점
   - 외인/기관 3영업일 이상 동시 연속 순매도: 45점 (동반 이탈)
   - 외인 또는 기관 단독 3영업일 이상 연속 순매도: 25점
   - 5영업일 누적 순매매 둘 다 음수(쌍끌이 매도): 35점 가산
   - 5영업일 누적 순매매 한쪽 음수: 15점 가산
==============================================================================
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any

class SupplyRiskAnalyzer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_supply_data(self, ticker: str) -> Dict[str, Any]:
        result = {
            "ticker": ticker,
            "foreign_net_5d": 0,
            "inst_net_5d": 0,
            "foreign_consecutive": 0,
            "inst_consecutive": 0
        }

        url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"

        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(res.text, "html.parser")

            # 외국인/기관 순매매가 포함된 테이블 검색
            tables = soup.find_all("table", class_="type2")
            target_table = None
            for t in tables:
                if "기관" in t.get_text() and "외국인" in t.get_text():
                    target_table = t
                    break

            if not target_table and tables:
                target_table = tables[1] if len(tables) > 1 else tables[0]

            if target_table:
                rows = target_table.find_all("tr")
                valid_days = 0
                f_streak = 0
                i_streak = 0

                for r in rows:
                    cols = [td.get_text(strip=True).replace(",", "").replace("+", "") for td in r.find_all("td")]
                    # 유효한 행: 날짜(YYYY.MM.DD) 형식 체크
                    if len(cols) >= 7 and "." in cols[0] and len(cols[0]) == 10:
                        try:
                            # cols 구조: [0:날짜, 1:종가, 2:전일비, 3:등락률, 4:거래량, 5:기관순매매, 6:외인순매매]
                            inst_val = int(cols[5])
                            frgn_val = int(cols[6])
                        except (ValueError, IndexError):
                            continue

                        if valid_days < 5:
                            result["inst_net_5d"] += inst_val
                            result["foreign_net_5d"] += frgn_val

                            if valid_days == f_streak and frgn_val < 0:
                                f_streak += 1
                            if valid_days == i_streak and inst_val < 0:
                                i_streak += 1

                            valid_days += 1

                        if valid_days >= 5:
                            break

                result["foreign_consecutive"] = f_streak
                result["inst_consecutive"] = i_streak

        except Exception as e:
            print(f"[SupplyAnalyzer] 수급 데이터 수집 오류 ({ticker}): {e}")

        return result

    def analyze_supply_risk(self, ticker: str, stock_name: str = "") -> Dict[str, Any]:
        raw = self.fetch_supply_data(ticker)
        f_streak = raw["foreign_consecutive"]
        i_streak = raw["inst_consecutive"]
        f_net = raw["foreign_net_5d"]
        i_net = raw["inst_net_5d"]

        risk_score = 0.0

        if f_streak >= 3 and i_streak >= 3:
            risk_score += 45.0
        elif f_streak >= 3 or i_streak >= 3:
            risk_score += 25.0

        if f_net < 0 and i_net < 0:
            risk_score += 35.0
        elif f_net < 0 or i_net < 0:
            risk_score += 15.0

        final_risk_score = min(100.0, risk_score)

        risk_factors = []
        if f_streak >= 3 and i_streak >= 3:
            risk_factors.append(f"외인·기관 동반 {min(f_streak, i_streak)}영업일 연속 순매도")
        elif f_streak >= 3:
            risk_factors.append(f"외국인 {f_streak}영업일 연속 순매도")
        elif i_streak >= 3:
            risk_factors.append(f"기관 {i_streak}영업일 연속 순매도")

        if f_net < 0 and i_net < 0:
            risk_factors.append("5영업일 외인·기관 쌍끌이 순매도")

        if final_risk_score >= 50:
            level = "HIGH"
            comment = f"경고: {', '.join(risk_factors)}로 인한 수급 이탈 압력이 높습니다."
        elif final_risk_score >= 20:
            level = "MEDIUM"
            comment = f"주의: {', '.join(risk_factors) if risk_factors else '단기 매도 우위'}가 관측됩니다."
        else:
            level = "LOW"
            comment = "수급 안정: 메이저 주체의 대규모 연속 이탈 징후가 관측되지 않습니다."

        return {
            "stock_name": stock_name,
            "ticker": ticker,
            "supply_risk_score": final_risk_score,
            "foreign_net_5d": f_net,
            "inst_net_5d": i_net,
            "foreign_sell_streak": f_streak,
            "inst_sell_streak": i_streak,
            "risk_level": level,
            "summary_comment": comment
        }