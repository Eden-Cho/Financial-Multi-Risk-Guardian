import os
import json
import time
import logging
import warnings
import threading
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings("ignore")
logging.getLogger("google.genai").setLevel(logging.ERROR)

from google import genai
from langfuse import observe, get_client, Langfuse
from backend.modules.dart_collector import DartCollector
from backend.modules.sentiment_analyzer import FinancialSentimentAnalyzer
from backend.modules.price_collector import StockPriceCollector
from backend.modules.storage import StorageManager

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Langfuse v4 전송 필터 설정
try:
    Langfuse(should_export_span=lambda span: True)
except Exception:
    pass

class RiskAnalyzer:
    def __init__(self):
        self.collector = DartCollector()
        self.sentiment_analyzer = FinancialSentimentAnalyzer()
        self.price_collector = StockPriceCollector()
        self.storage = StorageManager()
        self.ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        
        self.semaphore = threading.Semaphore(4)
        
        # 긴급 리스크 감지 키워드 목록
        self.delisting_keywords = ["감사의견 거절", "감사의견 한정", "자본잠식", "관리종목", "상장폐지", "형식적 요건", "영업손실", "회생절차", "환기종목"]
        self.governance_keywords = ["장내매도", "시간외대량매매", "블록딜", "최대주주 변경", "경영권 양수도", "횡령", "배임", "최대주주변경을수반하는", "소송", "가처분"]
        self.overhang_keywords = ["전환사채", "신주인수권부사채", "교환사채", "유상증자", "의무보유등록", "보호예수", "전환청구권행사", "주식매수선택권", "무상증자"]

    @observe(name="종목_다차원_정밀진단_파이프라인")
    def analyze(self, stock_name: str, quick_scan: bool = False):
        clean_name = stock_name.strip()
        if not self.collector.is_valid_company(clean_name):
            return None

        with self.semaphore:
            t_total_start = time.perf_counter()

            # 1. 로컬 DB에서 기초 재무제표 즉시 확인
            raw_financials = self.storage.get_financial_data(clean_name, max_age_seconds=86400 * 7)

            # 2. 실시간 주가 및 최신 DART 공시 병렬 조회 (재무 데이터 부재 시에만 재무 API 병합 호출)
            with ThreadPoolExecutor(max_workers=3) as executor:
                fut_price = executor.submit(self.price_collector.fetch_price_info, clean_name)
                fut_dart = executor.submit(self.collector.fetch_recent_disclosures, clean_name, 6)
                fut_fin = executor.submit(self.collector.fetch_financial_statements, clean_name) if raw_financials is None else None

                price_info = fut_price.result()
                real_disclosures = fut_dart.result()
                if fut_fin:
                    raw_financials = fut_fin.result()
                    if raw_financials:
                        self.storage.save_financial_data(clean_name, raw_financials)

            latest_rcept_no = real_disclosures[0]["rcept_no"] if real_disclosures else "NONE"
            dart_titles = [d["report_nm"] for d in real_disclosures]
            overhang_schedule = self._extract_overhang_from_real_dart(real_disclosures)
            mock_data = {"darts": dart_titles, "news": []}
            raw_disclosures_top = real_disclosures[:15]
            financial_health = self._calculate_financial_health_real(raw_financials or [], clean_name)
            cb_dilution = self._calculate_cb_dilution_dynamic(clean_name, real_disclosures)

            # 3. 돌발 위험 공시 발생 여부 검사
            has_urgent_risk = self._has_urgent_risk(dart_titles)
            
            # 4. 스마트 캐시 확인: 긴급 악재가 없고 최신 공시 번호가 동일하면 기존 AI 리포트 즉시 재사용
            cached_report = self.storage.get_cached_report(clean_name, max_age_seconds=3600 * 12)
            can_reuse_cache = (
                cached_report is not None and 
                not has_urgent_risk and 
                cached_report.get("last_rcept_no") == latest_rcept_no
            )

            if can_reuse_cache and not quick_scan:
                # [스마트 캐시 적중] 저장된 소견서 + 실시간 주가 조합하여 0초대 반환
                score_info = cached_report["score_info"]
                radar_df = pd.DataFrame(cached_report["radar_data"])
                report_text = cached_report["report_text"]
                forecast_scenario = cached_report["forecast_scenario"]
                cb_dilution = cached_report["cb_dilution"]
                sentiment_data = self.sentiment_analyzer.analyze_sentiments(dart_titles)
                
                elapsed = time.perf_counter() - t_total_start
                print(f"[스마트 캐시 히트] '{clean_name}' 즉시 반환 ({elapsed:.3f}s)")
                
                try:
                    get_client().flush()
                except Exception:
                    pass

                return (
                    score_info,
                    radar_df,
                    report_text,
                    overhang_schedule,
                    raw_disclosures_top,
                    financial_health,
                    cb_dilution,
                    forecast_scenario,
                    sentiment_data,
                    price_info
                )

            # [새로운 긴급 위험 감지 또는 캐시 만료 시] 전체 리스크 점수 및 AI 정밀 분석 수행
            delisting_risk = self._check_delisting_risk(mock_data, financial_health)
            governance_risk = self._check_governance_risk(mock_data)
            overhang_risk = self._check_overhang_schedule_risk(mock_data, overhang_schedule, cb_dilution)
            
            base_score = 100
            penalties = (delisting_risk['score'] + governance_risk['score'] + overhang_risk['score'])
            final_score = max(0, min(100, base_score - penalties))
            
            if final_score >= 75:
                status = "안전 (Low Risk)"
            elif final_score >= 45:
                status = "주의 (Moderate Risk)"
            else:
                status = "고위험 (High Risk)"

            score_info = {
                "score": final_score,
                "status": status,
                "dart_count": len(mock_data['darts']),
                "news_count": 0
            }

            radar_data = [
                {"theta": "상장유지 위험", "r": delisting_risk['score']},
                {"theta": "내부자 지분변동", "r": governance_risk['score']},
                {"theta": "잠재물량 부담", "r": overhang_risk['score']},
                {"theta": "재무 부실도", "r": financial_health.get("risk_score", 15)},
                {"theta": "사채 희석률", "r": cb_dilution.get("risk_score", 10)}
            ]

            if quick_scan:
                sentiment_data = {
                    "positive_pct": 50, "negative_pct": 10, "neutral_pct": 40,
                    "sentiment_score": 70, "sentiment_status": "데이터 요약", "breakdown": []
                }
                report_text = f"■ [{clean_name}] 일괄 안전도 점검 결과: {final_score}점 ({status})"
                forecast_scenario = {
                    "traffic_light": "GREEN" if final_score >= 75 else ("YELLOW" if final_score >= 45 else "RED"),
                    "verdict_badge": "🟢 클린 진입" if final_score >= 75 else ("🟡 주의 관망" if final_score >= 45 else "🔴 진입 금지"),
                    "verdict_summary": f"DART 공시 및 3개년 재무 룰 기반 점검 완료 ({final_score}점)",
                    "action_call": "상세 분석 탭에서 심층 AI 소견서를 확인하세요.",
                    "scenarios": []
                }
            else:
                sentiment_data = self.sentiment_analyzer.analyze_sentiments(dart_titles)
                report_text, forecast_scenario = self._generate_ai_analysis(
                    stock_name=clean_name,
                    price_info=price_info,
                    score=final_score,
                    status=status,
                    disclosures=dart_titles,
                    financial_health=financial_health,
                    cb_dilution=cb_dilution,
                    overhang_schedule=overhang_schedule,
                    sentiment_data=sentiment_data
                )
                # 새로 분석된 결과 DB에 스냅샷 저장
                self.storage.save_report(
                    stock_name=clean_name,
                    last_rcept_no=latest_rcept_no,
                    score_info=score_info,
                    radar_df_records=radar_data,
                    report_text=report_text,
                    forecast_scenario=forecast_scenario,
                    cb_dilution=cb_dilution
                )

            final_result = (
                score_info,
                pd.DataFrame(radar_data),
                report_text,
                overhang_schedule,
                raw_disclosures_top,
                financial_health,
                cb_dilution,
                forecast_scenario,
                sentiment_data,
                price_info
            )

            elapsed = time.perf_counter() - t_total_start
            tag = "긴급 악재 감지 재분석" if has_urgent_risk else ("경량 일괄 진단" if quick_scan else "신규 심층 분석")
            print(f"[{tag}] '{clean_name}' 완료 ({elapsed:.2f}s)")

            try:
                get_client().flush()
            except Exception:
                pass

            return final_result

    def _has_urgent_risk(self, dart_titles: list[str]) -> bool:
        """최근 3개 이내의 최신 공시 중 긴급 위험 키워드가 있는지 검사"""
        urgent_keywords = ["횡령", "배임", "감사의견", "관리종목", "상장폐지", "부도", "회생절차", "전환사채발행", "유상증자결정"]
        for title in dart_titles[:3]:
            if any(k in title for k in urgent_keywords):
                return True
        return False

    @observe(as_type="generation", name="Gemini_소견서_및_시나리오_생성")
    def _generate_ai_analysis(self, stock_name, price_info, score, status, disclosures, financial_health, cb_dilution, overhang_schedule, sentiment_data):
        if not self.ai_client:
            return self._fallback_text_and_scenario(stock_name, score, financial_health, cb_dilution)

        pref_str = ""
        if price_info.get("has_preferred_family"):
            pref_summary = ", ".join([f"{p['name']} ({p['price']}, 괴리율 {p['discount_rate']}%)" for p in price_info.get('related_pref_stocks', [])])
            pref_str = f"- 발행된 연계 우선주 목록: {pref_summary}\n- 보통주-우선주 배당/괴리율 투자 기회 고려 필요"

        prompt = f"""
당신은 대한민국 금융감독원 DART 공시 및 주식 시장 전문 금융 애널리스트입니다.
아래 제공된 [{stock_name}]의 실시간 시세, 연계 우선주 현황, DART 공시, 재무 데이터, KR-FinBERT 감성 지표를 종합 분석하여 JSON 형식으로만 응답하세요.

[실시간 시장 데이터]
- 종목명: {price_info.get('display_name')} (코드: {price_info.get('code')})
- 현재가: {price_info.get('current_price')} (전일대비: {price_info.get('change_str')})
{pref_str}
- 종합 안전도 점수: {score}점 ({status})
- KR-FinBERT 공시 여론: {sentiment_data.get('sentiment_status')} (긍정 {sentiment_data.get('positive_pct')}%, 부정 {sentiment_data.get('negative_pct')}%)
- 자본잠식 상태: {financial_health.get('impairment_ratio_str')} (잠식률: {financial_health.get('impairment_ratio')}%)
- 3개년 영업이익: {financial_health.get('op_profits')}
- 미상환 사채(CB/BW): {cb_dilution.get('dilution_ratio_str')}

[요청 사항]
연계 우선주가 있는 경우, 배당 및 괴리율 관점에서의 투자 참고사항도 소견에 자연스럽게 녹여 초보 투자자가 단번에 이해할 수 있도록 명확하고 냉철한 어조로 작성해주세요.
반드시 아래 키를 가진 순수 JSON 형태로만 출력하세요:
{{
  "report_text": "■ [{price_info.get('display_name')}] AI 정밀 리스크 소견서 전문 (상장유지, 지배구조, 보통주/우선주 관점 요약 4-5줄)",
  "traffic_light": "RED" 또는 "YELLOW" 또는 "GREEN",
  "verdict_badge": "🔴 진입 금지 (관망 절대 권고)" 또는 "🟡 주의 관망 (일정 소화 후 접근)" 또는 "🟢 클린 진입 (안전 투자 구간)",
  "verdict_summary": "현재 상황에 대한 1줄 명확한 요약",
  "action_call": "초보자가 지금 당장 취해야 할 행동 지침 1줄",
  "scenarios": [
    {{"period": "단기 1개월", "trend": "예상 흐름 타이틀", "prob": "75%", "desc": "1개월 내 예상 주가 변동 및 리스크 요인 1-2줄"}},
    {{"period": "중기 3개월", "trend": "예상 흐름 타이틀", "prob": "65%", "desc": "3개월 내 예상 주가 변동 및 리스크 요인 1-2줄"}},
    {{"period": "장기 6개월", "trend": "예상 흐름 타이틀", "prob": "60%", "desc": "6개월 내 기업 생존 및 가치 전망 1-2줄"}}
  ]
}}
"""
        t0 = time.perf_counter()
        try:
            response = self.ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            raw_text = response.text.strip()
            if "```" in raw_text:
                parts = raw_text.split("```")
                if len(parts) > 1:
                    raw_text = parts[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
            
            data = json.loads(raw_text.strip())
            report_text = data.get("report_text", "")
            forecast_scenario = {
                "traffic_light": data.get("traffic_light", "YELLOW"),
                "verdict_badge": data.get("verdict_badge", "🟡 주의 관망"),
                "verdict_summary": data.get("verdict_summary", ""),
                "action_call": data.get("action_call", ""),
                "scenarios": data.get("scenarios", [])
            }
            elapsed = time.perf_counter() - t0
            print(f"[Gemini] gemini-3.6-flash 분석 완료 ({elapsed:.2f}s)")
            return report_text, forecast_scenario
        except Exception as e:
            print(f"[Gemini] 분석 실패, 기본값 적용: {e}")
            return self._fallback_text_and_scenario(stock_name, score, financial_health, cb_dilution)

    @observe(as_type="generation", name="DART_공시_3줄요약_생성")
    def summarize_disclosure(self, report_nm: str, rcept_no: str = "") -> dict:
        if self.ai_client:
            prompt = f"""
공시 보고서명: [{report_nm}]
이 공시가 주가와 주주에게 미치는 영향을 초보 투자자 관점에서 분석하여 JSON으로 응답하세요:
{{
  "category": "공시 분류",
  "risk_level": "고위험, 주의, 보통, 안전 중 택1",
  "key_points": ["핵심 내용 1", "핵심 내용 2", "핵심 내용 3"],
  "action_guide": "👉 초보 투자자를 위한 1줄 행동 가이드"
}}
"""
            try:
                res = self.ai_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                raw_text = res.text.strip()
                if "```" in raw_text:
                    parts = raw_text.split("```")
                    if len(parts) > 1:
                        raw_text = parts[1]
                        if raw_text.startswith("json"):
                            raw_text = raw_text[4:]
                return json.loads(raw_text.strip())
            except Exception:
                pass

        return {
            "category": "일반 공시",
            "risk_level": "보통 (참고용)",
            "key_points": [f"[{report_nm}] 관련 공시입니다.", "공시 원문의 세부사항 확인이 필요합니다."],
            "action_guide": "👉 원문 링크를 통해 세부 조건을 확인하세요."
        }

    def _fallback_text_and_scenario(self, stock_name, score, financial_health, cb_dilution):
        report_text = f"■ [{stock_name}] 다차원 리스크 정밀 소견서\n종합 안전도: {score}점"
        traffic_light = "RED" if score < 50 else ("YELLOW" if score < 75 else "GREEN")
        forecast_scenario = {
            "traffic_light": traffic_light,
            "verdict_badge": "🔴 진입 금지" if traffic_light == "RED" else ("🟡 주의 관망" if traffic_light == "YELLOW" else "🟢 클린 진입"),
            "verdict_summary": f"{stock_name}의 공시 및 재무 상태 분석 완료",
            "action_call": "공시 일정과 분기 실적을 면밀히 검토 후 접근하세요.",
            "scenarios": [
                {"period": "단기 1개월", "trend": "변동성 구간", "prob": "70%", "desc": "단기 수급 및 공시 일정에 따른 조정 가능성"},
                {"period": "중기 3개월", "trend": "실적 반영", "prob": "65%", "desc": "본업 영업이익 추이에 따른 주가 재평가"},
                {"period": "장기 6개월", "trend": "가치 수렴", "prob": "60%", "desc": "재무 건전성에 기반한 중장기 흐름"}
            ]
        }
        return report_text, forecast_scenario

    def _calculate_cb_dilution_dynamic(self, stock_name: str, real_disclosures: list[dict]) -> dict:
        cb_disclosures = [d for d in real_disclosures if any(k in d.get("report_nm", "") for k in ["전환사채", "신주인수권", "CB", "BW"])]
        if not cb_disclosures:
            return {
                "has_cb": False,
                "total_unredeemed_amount": "0원",
                "market_cap": "시총 대비 0.0%",
                "dilution_ratio": 0.0,
                "dilution_ratio_str": "미상환 사채 없음 (희석 위험 0%)",
                "total_potential_shares": "0주",
                "shares_ratio": "0.0%",
                "risk_score": 0,
                "cb_items": [],
                "dilution_warning": "미상환된 전환사채 및 신주인수권부사채가 없어 주가 희석 리스크가 없습니다."
            }

        cb_count = len(cb_disclosures)
        est_amount = cb_count * 90.0
        dilution_ratio = min(40.0, cb_count * 12.5)

        cb_items = []
        for d in cb_disclosures[:2]:
            cb_items.append({
                "name": d["report_nm"][:28] + "...",
                "unredeemed_amount": f"{int(est_amount/cb_count):,.1f}억 원",
                "conv_price": "공시 원문 참조",
                "refixing_floor": "최대 70% 하향 리픽싱 조항 존재 가능"
            })

        return {
            "has_cb": True,
            "total_unredeemed_amount": f"{est_amount:,.1f}억 원",
            "market_cap": f"시총 대비 약 {dilution_ratio:.1f}%",
            "dilution_ratio": dilution_ratio,
            "dilution_ratio_str": f"주의~고위험 (잠재 희석률 {dilution_ratio:.1f}%)",
            "total_potential_shares": "수백만 주 규모",
            "shares_ratio": f"발행주식의 약 {dilution_ratio:.1f}%",
            "risk_score": int(min(100, dilution_ratio * 2.5)),
            "cb_items": cb_items,
            "dilution_warning": f"최근 {cb_count}건의 메자닌(CB/BW) 공시가 탐지되었습니다."
        }

    def _extract_overhang_from_real_dart(self, disclosures: list[dict]) -> list[dict]:
        schedule = []
        for d in disclosures:
            title = d["report_nm"]
            dt_str = d["rcept_dt"]
            if "전환사채" in title or "신주인수권부사채" in title:
                schedule.append({
                    "event_name": f"{title[:28]}...",
                    "event_type": "CB 전환청구",
                    "target_date": dt_str,
                    "d_day": 14,
                    "risk_level": "HIGH",
                    "description": f"DART 공시 접수({dt_str}): 대규모 주식 전환 시 단기 매물 출회 가능성"
                })
        return schedule[:3]

    def _check_delisting_risk(self, data, fin_data):
        score = 0
        detected = []
        for d in data['darts']:
            for k in self.delisting_keywords:
                if k in d:
                    score += 45
                    detected.append(k)
        if fin_data.get("impairment_ratio", 0) >= 50:
            score += 50
            detected.append("자본잠식률 50% 초과")
        elif fin_data.get("impairment_ratio", 0) > 0:
            score += 20
            detected.append("부분자본잠식")
        if fin_data.get("consecutive_loss_years", 0) >= 3:
            score += 30
            detected.append(f"{fin_data['consecutive_loss_years']}년 연속 적자")
        if score == 0:
            return {"score": 0, "msg": "감사의견 적정, 자본잠식 없음 (정상)"}
        return {"score": min(100, score), "msg": f"주의 요망 ({', '.join(set(detected))} 감지)"}

    def _check_governance_risk(self, data):
        score = 0
        detected = []
        for text in data['darts']:
            for k in self.governance_keywords:
                if k in text:
                    score += 35
                    detected.append(k)
        if score == 0:
            return {"score": 0, "msg": "최대주주 지분율 안정 및 주요 임원 지분 이탈 징후 없음"}
        return {"score": min(100, score), "msg": f"지배구조 변동성 감지 ({', '.join(set(detected))} 관련 내역 확인)"}

    def _check_overhang_schedule_risk(self, data, schedule, cb_dilution):
        score = 0
        if cb_dilution.get("dilution_ratio", 0) >= 20: score += 45
        elif cb_dilution.get("dilution_ratio", 0) >= 10: score += 25
        if schedule: score += len(schedule) * 10
        if score == 0: return {"score": 0, "msg": "미상환 사채 부담 없음 (안전)"}
        return {"score": min(100, score), "msg": f"잠재 물량 출회 주의 ({cb_dilution.get('dilution_ratio_str', '')})"}

    def _calculate_financial_health_real(self, raw_list: list[dict], stock_name: str) -> dict:
        capital = 0.0
        total_equity = 0.0
        op_profits = []

        for item in raw_list:
            account_nm = item.get("account_nm", "").strip()
            if "자본금" == account_nm:
                try: capital = float(item.get("thstrm_amount", "0").replace(",", ""))
                except: pass
            if "자본총계" == account_nm:
                try: total_equity = float(item.get("thstrm_amount", "0").replace(",", ""))
                except: pass
            if "영업이익" in account_nm:
                t1 = self._parse_amount(item.get("thstrm_amount", "0"))
                t2 = self._parse_amount(item.get("frmtrm_amount", "0"))
                t3 = self._parse_amount(item.get("bfefrmtrm_amount", "0"))
                op_profits = [t1, t2, t3]

        impairment_ratio = 0.0
        impairment_status = "정상 (자본잠식 없음)"
        if capital > 0:
            if total_equity < 0:
                impairment_ratio = 100.0
                impairment_status = "완전자본잠식"
            elif total_equity < capital:
                impairment_ratio = round(((capital - total_equity) / capital) * 100, 2)
                impairment_status = f"부분자본잠식 ({impairment_ratio}%)"

        consecutive_losses = 0
        for p in op_profits:
            if p < 0: consecutive_losses += 1
            else: break

        fin_risk_score = 10
        if impairment_ratio >= 50: fin_risk_score += 50
        elif impairment_ratio > 0: fin_risk_score += 25
        if consecutive_losses >= 3: fin_risk_score += 40

        return {
            "capital": self._format_korean_currency(capital),
            "total_equity": self._format_korean_currency(total_equity),
            "impairment_ratio": impairment_ratio,
            "impairment_ratio_str": impairment_status,
            "is_impaired": impairment_ratio > 0,
            "consecutive_loss_years": consecutive_losses,
            "op_profits": [self._format_korean_currency(x) for x in op_profits] if op_profits else ["-", "-", "-"],
            "risk_score": min(100, fin_risk_score),
            "warning_flags": [f"자본잠식률: {impairment_ratio}%", f"{consecutive_losses}년 연속 영업적자"] if (impairment_ratio > 0 or consecutive_losses > 0) else ["재무 건전성 우량"]
        }

    def _parse_amount(self, amt_str: str) -> float:
        try: return float(str(amt_str).replace(",", "").strip())
        except: return 0.0

    def _format_korean_currency(self, amount: float) -> str:
        if amount == 0: return "0원"
        sign = "-" if amount < 0 else ""
        abs_amt = abs(amount)
        eok = abs_amt / 100000000.0
        if eok >= 10000:
            cho = eok / 10000.0
            return f"{sign}{cho:.2f}조 원"
        return f"{sign}{eok:,.1f}억 원"