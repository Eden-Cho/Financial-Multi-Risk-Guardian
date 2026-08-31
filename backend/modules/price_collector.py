import os
import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor

class StockPriceCollector:
    """네이버 금융 API 기반 병렬 우선주 탐색 및 실시간 시세 수집기"""
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.naver.com"
        }
        self.code_cache = {
            "삼성전자": "005930", "삼성전자우": "005935",
            "현대차": "005380", "현대자동차": "005380", "현대차우": "005385", "현대차2우B": "005387", "현대차3우B": "005389"
        }

    def _search_stock_code(self, name: str) -> tuple[str, str]:
        clean = name.strip()
        if clean in self.code_cache:
            return self.code_cache[clean], clean

        try:
            url = f"https://ac.finance.naver.com/ac?q={clean}&target=stock"
            res = requests.get(url, headers=self.headers, timeout=2.0)
            data = res.json()
            if data and "items" in data and len(data["items"]) > 0:
                for sublist in data["items"]:
                    for item in sublist:
                        c_code = str(item[0]).strip()
                        c_name = str(item[1]).strip()
                        if c_name.replace(" ", "") == clean.replace(" ", ""):
                            self.code_cache[clean] = c_code
                            return c_code, c_name
                if data["items"][0]:
                    c_code = str(data["items"][0][0][0]).strip()
                    c_name = str(data["items"][0][0][1]).strip()
                    self.code_cache[clean] = c_code
                    return c_code, c_name
        except Exception:
            pass

        return "", clean

    def _fetch_single_price(self, code: str) -> dict:
        if not code or code == "000000":
            return {"now": 0, "diff": 0, "rate": 0.0}

        try:
            url_summary = f"https://api.finance.naver.com/service/itemSummary.nhn?itemcode={code}"
            res = requests.get(url_summary, headers=self.headers, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                now = int(data.get("now", 0))
                diff = int(data.get("diff", 0))
                rate = float(data.get("rate", 0.0))
                if now > 0:
                    return {"now": now, "diff": diff, "rate": rate}
        except Exception:
            pass

        try:
            url_m = f"https://m.stock.naver.com/api/stock/{code}/basic"
            res_m = requests.get(url_m, headers=self.headers, timeout=2.0)
            if res_m.status_code == 200:
                d = res_m.json()
                now_str = str(d.get("nowPrice", "0")).replace(",", "")
                diff_str = str(d.get("changePrice", "0")).replace(",", "")
                rate_str = str(d.get("fluctuationsRatio", "0.0")).replace(",", "")
                now = int(now_str) if now_str.isdigit() else 0
                diff = int(diff_str) if diff_str.isdigit() or (diff_str.startswith("-") and diff_str[1:].isdigit()) else 0
                rate = float(rate_str)
                if now > 0:
                    return {"now": now, "diff": diff, "rate": rate}
        except Exception:
            pass

        return {"now": 0, "diff": 0, "rate": 0.0}

    def _probe_pref_candidate(self, args: tuple) -> dict | None:
        """우선주 후보군 1건 조회 함수 (병렬 스레드용)"""
        common_name, common_code, suffix, p_type, common_now = args
        pref_candidate_name = f"{common_name}{suffix}"
        p_code, p_real_name = self._search_stock_code(pref_candidate_name)

        if p_code and p_code != common_code:
            p_price_data = self._fetch_single_price(p_code)
            p_now = p_price_data["now"]
            p_diff = p_price_data["diff"]
            p_rate = p_price_data["rate"]

            discount_rate = 0.0
            if common_now > 0 and p_now > 0:
                discount_rate = round(((common_now - p_now) / common_now) * 100, 1)

            p_sign = "+" if p_diff > 0 else ("-" if p_diff < 0 else "")

            return {
                "name": p_real_name,
                "code": p_code,
                "type": p_type,
                "price": f"{p_now:,}원" if p_now > 0 else "종가 확인중",
                "raw_price": p_now,
                "change_str": f"{p_sign}{abs(p_diff):,}원 ({p_sign}{p_rate:.2f}%)" if p_diff != 0 else "-",
                "is_up": p_diff > 0,
                "is_down": p_diff < 0,
                "discount_rate": discount_rate,
                "discount_rate_str": f"보통주 대비 {discount_rate}% 저렴" if discount_rate > 0 else "보통주와 유사 수준",
                "dividend_benefit": "보통주 대비 추가 배당금 지급 및 높은 시가배당률",
                "voting_right": "의결권 없음",
                "liquidity_note": "보통주 대비 일일 거래량 확인 필요"
            }
        return None

    def fetch_price_info(self, stock_name: str) -> dict:
        clean_name = stock_name.strip()
        code, display_name = self._search_stock_code(clean_name)

        pref_pattern = r"((\s*\(우\))|(\s*우B?)|(\s*\d*우[A-Z]?)|(\(.*?우.*?\)))$"
        is_pref_query = bool(re.search(pref_pattern, clean_name))

        common_name = re.sub(pref_pattern, "", clean_name).strip() if is_pref_query else clean_name
        if not common_name:
            common_name = clean_name
        
        common_code, _ = self._search_stock_code(common_name)

        # 본체 및 대상 종목 시세 병렬 수집
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_curr = executor.submit(self._fetch_single_price, code)
            fut_common = executor.submit(self._fetch_single_price, common_code) if is_pref_query else None

            curr_price_data = fut_curr.result()
            common_price_data = fut_common.result() if fut_common else curr_price_data

        now_price = curr_price_data["now"]
        diff = curr_price_data["diff"]
        rate = curr_price_data["rate"]
        common_now = common_price_data["now"]

        sign = "+" if diff > 0 else ("-" if diff < 0 else "")
        price_str = f"{now_price:,}원" if now_price > 0 else "종가 확인중"
        change_str = f"{sign}{abs(diff):,}원 ({sign}{rate:.2f}%)" if now_price > 0 else "-"

        # ⚡ 7개 우선주 후보군을 동시 병렬 탐색
        candidate_suffixes = [
            ("우", "구형우선주"),
            ("우B", "신형우선주"),
            ("1우", "구형우선주"),
            ("2우B", "신형우선주(최저배당)"),
            ("3우B", "신형우선주"),
            ("4우(전환)", "전환우선주"),
            (" 우", "구형우선주")
        ]

        probe_args = [
            (common_name, common_code, suffix, p_type, common_now)
            for suffix, p_type in candidate_suffixes
        ]

        related_pref_stocks = []
        found_codes = set()

        with ThreadPoolExecutor(max_workers=7) as executor:
            results = executor.map(self._probe_pref_candidate, probe_args)
            for res in results:
                if res and res["code"] not in found_codes:
                    found_codes.add(res["code"])
                    related_pref_stocks.append(res)

        return {
            "has_price": now_price > 0,
            "code": code or common_code or "005930",
            "display_name": display_name,
            "is_preferred": is_pref_query,
            "common_name": common_name,
            "common_code": common_code,
            "common_price": f"{common_now:,}원" if common_now > 0 else price_str,
            "current_price": price_str,
            "raw_price": now_price,
            "change_str": change_str,
            "change_rate": rate,
            "is_up": diff > 0,
            "is_down": diff < 0,
            "market_status": "장마감" if (diff == 0 and rate == 0) else "실시간/직전종가",
            "has_preferred_family": len(related_pref_stocks) > 0,
            "related_pref_stocks": related_pref_stocks
        }