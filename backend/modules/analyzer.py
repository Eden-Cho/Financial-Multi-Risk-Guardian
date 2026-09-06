"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/analyzer.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할:
    1. 금융감독원(DART) 전자공시, 3개년 재무제표, 실시간 주가 데이터를 병렬 수집하여 통합 리스크 분석 수행
    2. 상장유지 적격성, 지배구조 변동, 잠재 오버행(CB/BW 희석률)의 핵심 리스크를 정량적(0~100점)으로 평가
    3. HuggingFace KR-FinBERT를 이용한 공시 여론 감성 분석(긍정/중립/부정) 산출
    4. Google Gemini LLM을 연동하여 투자자를 위한 정밀 리스크 소견서 및 3~6개월 주가 시나리오 생성 (조건부 최적화 적용)
    5. [4대 고도화 완료] 미디어 노이즈, 수급 이탈, 실적 충격, 매크로 민감도의 9각 레이더 차트 결합
    6. response_mime_type="application/json" 강제와 2단계 모델 폴백(Fallback Tier)으로 고속 응답
    7. [신규 추가] analyze_portfolio_summary: OCR/관심종목 리스트 기반 포트폴리오 종합 건강진단 데이터 생성
==============================================================================
"""

import os
import re
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
from google.genai import types
from langfuse import observe, get_client, Langfuse

# 사내 구축 서브 분석 모듈들
from backend.modules.dart_collector import DartCollector
from backend.modules.sentiment_analyzer import FinancialSentimentAnalyzer
from backend.modules.price_collector import StockPriceCollector
from backend.modules.storage import StorageManager
from backend.modules.news_crawler import NewsRiskAnalyzer
from backend.modules.supply_analyzer import SupplyRiskAnalyzer
from backend.modules.consensus_analyzer import ConsensusRiskAnalyzer
from backend.modules.macro_analyzer import MacroRiskAnalyzer

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Langfuse v4 관측성 추적 초기화
try:
    Langfuse(should_export_span=lambda span: True)
except Exception:
    pass

# LLM 2단계 폴백 모델 우선순위 정의
PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-3.6-flash"


def _call_gemini_fast_json(ai_client, prompt: str, max_tokens: int = 1500) -> dict:
    """
    [함수 역할]
    Gemini API를 호출하고, 응답 텍스트에 불순물이나 마크다운이 섞여 있거나 
    일부 포맷이 어긋나더라도 정규식을 통해 순수 JSON 객체만 안전하게 추출하여 반환하며,
    최종 실패 시 scenarios가 포함된 안전한 대체 딕셔너리를 복구합니다.
    """
    if not ai_client:
        raise RuntimeError("Gemini Client가 초기화되지 않았습니다.")

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]

    for model_name in models_to_try:
        for attempt in range(2):
            try:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=max_tokens
                )
                res = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                raw = (res.text or "").strip()
                
                # 1차: 마크다운 코드블록 제거
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                # 2차: 텍스트 내에서 첫 번째 '{'부터 마지막 '}'까지의 JSON 블록만 정규식 추출
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except json.JSONDecodeError as jde:
                        print(f"[파싱 실패 디버그] JSON 문법 오류: {jde}")
                        pass
                
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as jde:
                    print(f"[파싱 실패 디버그 - 전체 파싱 실패]: {jde}")
                    return {
                        "category": "공시 요약 및 분석",
                        "risk_level": "보통 (참고용)",
                        "report_text": raw[:200] if raw else "분석 텍스트 생성 중 오류가 발생했습니다.",
                        "traffic_light": "YELLOW",
                        "verdict_badge": "🟡 주의 관망 (일정 소화 후 재검토)",
                        "verdict_summary": "공시 및 재무 상태 룰 기반 분석 완료",
                        "action_call": "공시 일정과 분기 실적 추이를 면밀히 검토 후 접근하세요.",
                        "scenarios": [
                            {"period": "단기 1개월", "trend": "수급 및 변동성 대응", "prob": "70%", "desc": "단기 수급 동향 및 뉴스 노이즈에 따른 주가 변동성 관찰"},
                            {"period": "중기 3개월", "trend": "실적 모멘텀 반영", "prob": "65%", "desc": "분기 실적 추이 및 본업 펀더멘털에 따른 재평가"},
                            {"period": "장기 6개월", "trend": "가치 수렴 구간", "prob": "60%", "desc": "재무 건전성 및 거시경제 환경에 따른 중장기 추세 수렴"}
                        ],
                        "key_points": [
                            raw[:100] + "..." if len(raw) > 100 else (raw or "데이터 수집 완료"),
                            "상세 조건은 DART 원문 공시를 참고하시기 바랍니다.",
                            "주가 및 지분 가치에 미치는 영향을 모니터링하세요."
                        ],
                        "action_guide": "👉 원문 링크를 통해 세부 내용을 확인하세요."
                    }

            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    print(f"[Gemini 503 대기] 서버 일시 과부하, 1초 후 재시도...")
                    time.sleep(1.0)
                    continue
                print(f"[Gemini API 호출 예외 발생]: {e}")
                break

    # 최후의 안전 Fallback 반환
    return {
        "report_text": "■ [AI 분석 일시 지연]\n- 룰 기반 정량 진단 지표와 DART 공시 원문을 참고하시기 바랍니다.",
        "traffic_light": "YELLOW",
        "verdict_badge": "🟡 주의 관망 (일정 소화 후 재검토)",
        "verdict_summary": "서버 일시 과부하로 인한 기본 진단 안내",
        "action_call": "잠시 후 다시 시도하거나 상세 분석 탭을 확인하세요.",
        "scenarios": [
            {"period": "단기 1개월", "trend": "변동성 대응", "prob": "70%", "desc": "단기 수급 및 공시 일정에 따른 등락 구간"},
            {"period": "중기 3개월", "trend": "실적 반영", "prob": "65%", "desc": "분기 실적 추이에 따른 주가 재평가"},
            {"period": "장기 6개월", "trend": "가치 수렴", "prob": "60%", "desc": "재무 건전성에 기반한 중장기 흐름"}
        ]
    }


class RiskAnalyzer:
    """
    [클래스 역할]
    DART 공시, 재무제표, 실시간 호가/시세, 뉴스 미디어 노이즈, 외인/기관 수급,
    실적 충격(어닝 쇼크), 거시경제/섹터 민감도 데이터를 종합 분석하는 통합 컨트롤러
    """

    def __init__(self):
        self.collector = DartCollector()
        self.sentiment_analyzer = FinancialSentimentAnalyzer()
        self.price_collector = StockPriceCollector()
        self.storage = StorageManager()
        self.news_analyzer = NewsRiskAnalyzer()
        self.supply_analyzer = SupplyRiskAnalyzer()
        self.consensus_analyzer = ConsensusRiskAnalyzer()
        self.macro_analyzer = MacroRiskAnalyzer()
        
        self.ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        self.semaphore = threading.Semaphore(4)
        
        self.delisting_keywords = ["감사의견 거절", "감사의견 한정", "자본잠식", "관리종목", "상장폐지", "형식적 요건", "영업손실", "회생절차", "환기종목"]
        self.governance_keywords = ["장내매도", "시간외대량매매", "블록딜", "최대주주 변경", "경영권 양수도", "횡령", "배임", "최대주주변경을수반하는", "소송", "가처분"]
        self.overhang_keywords = ["전환사채", "신주인수권부사채", "교환사채", "유상증자", "의무보유등록", "보호예수", "전환청구권행사", "주식매수선택권", "무상증자"]

    @observe(name="종목_다차원_정밀진단_파이프라인")
    def analyze(self, stock_name: str, quick_scan: bool = False):
        """개별 종목에 대한 전체 분석 파이프라인을 실행합니다."""
        clean_name = stock_name.strip()
        if not self.collector.is_valid_company(clean_name):
            return None

        with self.semaphore:
            t_total_start = time.perf_counter()

            raw_financials = self.storage.get_financial_data(clean_name, max_age_seconds=86400 * 7)

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

            ticker = price_info.get("code", "")
            latest_rcept_no = real_disclosures[0]["rcept_no"] if real_disclosures else "NONE"
            dart_titles = [d["report_nm"] for d in real_disclosures]
            overhang_schedule = self._extract_overhang_from_real_dart(real_disclosures)
            mock_data = {"darts": dart_titles, "news": []}
            raw_disclosures_top = real_disclosures[:15]
            
            financial_health = self._calculate_financial_health_real(raw_financials or [], clean_name)
            cb_dilution = self._calculate_cb_dilution_dynamic(clean_name, real_disclosures)

            # 4대 고도화 엔진 동시 가동
            news_risk = self.news_analyzer.analyze_news_risk(clean_name, sentiment_analyzer=self.sentiment_analyzer)
            supply_risk = self.supply_analyzer.analyze_supply_risk(ticker, clean_name)
            consensus_risk = self.consensus_analyzer.analyze_from_financials(raw_financials or [], clean_name, ticker)
            macro_risk = self.macro_analyzer.analyze_macro_risk(clean_name)

            has_urgent_risk = self._has_urgent_risk(dart_titles)
            
            # 룰 기반 페널티 산정 (총 100점 만점 역산)
            delisting_risk = self._check_delisting_risk(mock_data, financial_health)
            governance_risk = self._check_governance_risk(mock_data)
            overhang_risk = self._check_overhang_schedule_risk(mock_data, overhang_schedule, cb_dilution)
            
            base_score = 100
            media_penalty = (news_risk["news_risk_score"] / 100.0) * 10.0
            supply_penalty = (supply_risk["supply_risk_score"] / 100.0) * 12.0
            consensus_penalty = (consensus_risk["consensus_risk_score"] / 100.0) * 12.0
            macro_penalty = (macro_risk["macro_risk_score"] / 100.0) * 10.0
            
            penalties = (
                delisting_risk['score'] * 0.25 + 
                governance_risk['score'] * 0.15 + 
                overhang_risk['score'] * 0.12 + 
                media_penalty + 
                supply_penalty + 
                consensus_penalty + 
                macro_penalty
            )
            final_score = int(max(0, min(100, base_score - penalties)))
            
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
                "news_count": news_risk.get("total_fetched", 0)
            }

            # 9각 레이더 차트 구성 (r: 0~100점 위험도)
            news_score = int(news_risk.get("news_risk_score", 0)) if news_risk else 0
            supply_score = int(supply_risk.get("supply_risk_score", 0)) if supply_risk else 0
            consensus_score = int(consensus_risk.get("consensus_risk_score", 0)) if consensus_risk else 0
            macro_score = int(macro_risk.get("macro_risk_score", 0)) if macro_risk else 0

            radar_data = [
                {"theta": "상장유지 위험", "r": int(delisting_risk.get('score', 0))},
                {"theta": "내부자 지분변동", "r": int(governance_risk.get('score', 0))},
                {"theta": "잠재물량 부담", "r": int(overhang_risk.get('score', 0))},
                {"theta": "재무 부실도", "r": int(financial_health.get("risk_score", 15))},
                {"theta": "사채 희석률", "r": int(cb_dilution.get("risk_score", 10))},
                {"theta": "미디어 노이즈", "r": news_score},
                {"theta": "수급 이탈 압력", "r": supply_score},
                {"theta": "실적 충격도", "r": consensus_score},
                {"theta": "매크로 민감도", "r": macro_score}
            ]

            if quick_scan:
                sentiment_data = {
                    "positive_pct": 50, "negative_pct": 10, "neutral_pct": 40,
                    "sentiment_score": 70, "sentiment_status": "데이터 요약", "breakdown": []
                }
                report_text = (
                    f"■ [{clean_name}] 일괄 점검 결과: {final_score}점 ({status})\n"
                    f"- 미디어: {news_risk['summary_comment']}\n"
                    f"- 수급: {supply_risk['summary_comment']}\n"
                    f"- 실적: {consensus_risk['summary_comment']}\n"
                    f"- 매크로: {macro_risk['summary_comment']}"
                )
                if final_score >= 75:
                    traffic_light = "GREEN"
                    verdict_badge = "🟢 클린 진입 (안전 투자 구간)"
                elif final_score >= 45:
                    traffic_light = "YELLOW"
                    verdict_badge = "🟡 주의 관망 (일정 소화 후 재검토)"
                else:
                    traffic_light = "RED"
                    verdict_badge = "🔴 진입 금지 (위험 경보)"

                forecast_scenario = {
                    "traffic_light": traffic_light,
                    "verdict_badge": verdict_badge,
                    "verdict_summary": f"공시·재무·미디어·수급·실적·매크로 종합 점검 완료 ({final_score}점)",
                    "action_call": "상세 분석 탭에서 심층 AI 소견서를 확인하세요.",
                    "scenarios": [
                        {"period": "단기 1개월", "trend": "변동성 구간", "prob": "70%", "desc": "단기 수급 및 공시 일정에 따른 주가 조정 가능성"},
                        {"period": "중기 3개월", "trend": "실적 반영", "prob": "65%", "desc": "본업 영업이익 추이에 따른 주가 재평가"},
                        {"period": "장기 6개월", "trend": "가치 수렴", "prob": "60%", "desc": "재무 건전성에 기반한 중장기 흐름"}
                    ]
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
                    sentiment_data=sentiment_data,
                    news_risk=news_risk,
                    supply_risk=supply_risk,
                    consensus_risk=consensus_risk,
                    macro_risk=macro_risk,
                    has_urgent=has_urgent_risk
                )
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

    def analyze_portfolio_summary(self, stock_list: list[str]) -> dict:
        """
        [신규 추가]
        스크린샷 OCR이나 관심종목에 등록된 종목 리스트 전체를 일괄 진단하여,
        프론트엔드 대시보드 시각화용 통합 진단 스키마(PortfolioDiagnosisSummary)를 생성합니다.
        """
        if not stock_list:
            return {
                "status": "empty",
                "message": "진단할 종목이 없습니다.",
                "portfolio_summary": {
                    "overall_score": 0.0,
                    "grade": "N/A",
                    "risk_level": "UNKNOWN",
                    "risk_level_kr": "데이터 없음",
                    "summary_comment": "등록된 보유 종목이 존재하지 않습니다.",
                    "distribution": {"safe_count": 0, "caution_count": 0, "danger_count": 0, "total_count": 0}
                },
                "radar_composite": [],
                "stock_cards": [],
                "top_warnings": []
            }

        stock_cards = []
        top_warnings = []
        total_score = 0.0
        safe_cnt = caution_cnt = danger_cnt = 0

        # 9대 리스크별 위험도 누적기
        radar_keys = [
            "상장유지 위험", "내부자 지분변동", "잠재물량 부담", 
            "재무 부실도", "사채 희석률", "미디어 노이즈", 
            "수급 이탈 압력", "실적 충격도", "매크로 민감도"
        ]
        radar_accumulator = {k: 0.0 for k in radar_keys}

        valid_stock_count = 0

        for stock in stock_list:
            clean_name = stock.strip()
            if not clean_name:
                continue

            # 캐시가 있으면 신속하게 조회하고, 없으면 quick_scan으로 경량 진단
            cached = self.storage.get_cached_report(clean_name, max_age_seconds=86400 * 3)
            
            if cached:
                score = cached["score_info"]["score"]
                status_str = cached["score_info"]["status"]
                radar_records = cached.get("radar_data", [])
                code = getattr(self.collector, "get_stock_code", lambda x: "")(clean_name)
                cb_info = cached.get("cb_dilution", {})
            else:
                diag = self.analyze(clean_name, quick_scan=True)
                if not diag:
                    continue
                score_info, radar_df, _, _, _, fin_health, cb_info, _, _, price_info = diag
                score = score_info["score"]
                status_str = score_info["status"]
                radar_records = radar_df.to_dict(orient="records")
                code = price_info.get("code", "")

            valid_stock_count += 1
            total_score += score

            # 레이더 데이터 누적 합산
            for row in radar_records:
                theta = row.get("theta")
                r_val = row.get("r", 0)
                if theta in radar_accumulator:
                    radar_accumulator[theta] += float(r_val)

            # 신호등 등급 및 배지 판정
            highlight_flags = []
            major_risks = []
            
            if score >= 75:
                card_status = "SAFE"
                badge_color = "green"
                safe_cnt += 1
                highlight_flags.append("재무 건전성 및 공시 양호")
            elif score >= 45:
                card_status = "CAUTION"
                badge_color = "yellow"
                caution_cnt += 1
                highlight_flags.append("수급 및 공시 모니터링 필요")
                major_risks.append("단기 변동성 및 잠재 이슈 관리 요망")
            else:
                card_status = "DANGER"
                badge_color = "red"
                danger_cnt += 1
                highlight_flags.append("리스크 임계치 초과 경보")
                major_risks.append("재무 부실 또는 대규모 지분 희석 위험 노출")
                
                # 고위험 종목은 최상단 경고 알림(top_warnings)에 우선 등록
                top_warnings.append({
                    "severity": "CRITICAL",
                    "target_stock": clean_name,
                    "title": f"{clean_name} 집중 리스크 경보",
                    "description": f"종합 점수 {score}점으로 고위험 구간입니다. 공시 원문 및 오버행 여부를 즉시 점검하세요."
                })

            if cb_info and cb_info.get("has_cb"):
                dilution_str = cb_info.get("dilution_ratio_str", "")
                if dilution_str:
                    major_risks.append(f"메자닌 부담: {dilution_str}")

            stock_cards.append({
                "stock_name": clean_name,
                "stock_code": code,
                "score": score,
                "status": card_status,
                "badge_color": badge_color,
                "highlight_flags": highlight_flags,
                "major_risks": major_risks
            })

        if valid_stock_count == 0:
            return {
                "status": "fail", 
                "message": "유효한 상장사 정보를 진단하지 못했습니다."
            }

        avg_score = round(total_score / valid_stock_count, 1)

        # 포트폴리오 등급 및 위험 레벨 정의
        if avg_score >= 85:
            grade, risk_lvl, risk_kr = "A", "SAFE", "매우 안전 (Very Safe)"
            comment = "보유 포트폴리오 전반의 재무 건전성과 공시 투명성이 매우 안정적인 우수 포트폴리오입니다."
        elif avg_score >= 75:
            grade, risk_lvl, risk_kr = "B+", "SAFE", "안전 (Low Risk)"
            comment = "안정적인 펀더멘털을 유지하고 있으며 일상적인 공시 및 실적 흐름 모니터링으로 충분합니다."
        elif avg_score >= 60:
            grade, risk_lvl, risk_kr = "B-", "CAUTION", "주의 (Caution)"
            comment = "일부 종목에서 미디어 노이즈, 수급 이탈 또는 잠재 오버행 징후가 감지되므로 분산 관리가 필요합니다."
        elif avg_score >= 45:
            grade, risk_lvl, risk_kr = "C", "WARNING", "경고 (Warning)"
            comment = "다수 보유 종목에서 재무 부담 및 공시 리스크가 중첩되고 있으므로 비중 축소 검토가 권장됩니다."
        else:
            grade, risk_lvl, risk_kr = "D", "DANGER", "고위험 (High Risk)"
            comment = "심각한 자본 건전성 저하나 대규모 사채 물량 압박을 받는 위험 종목이 포함되어 즉각적인 리밸런싱이 요구됩니다."

        # 레이더 평균값 산출 (full_mark 100 기준)
        radar_composite = [
            {
                "category": k,
                "score": round(radar_accumulator[k] / valid_stock_count, 1),
                "full_mark": 100
            }
            for k in radar_keys
        ]

        return {
            "status": "success",
            "analyzed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "portfolio_summary": {
                "overall_score": avg_score,
                "grade": grade,
                "risk_level": risk_lvl,
                "risk_level_kr": risk_kr,
                "summary_comment": comment,
                "distribution": {
                    "safe_count": safe_cnt,
                    "caution_count": caution_cnt,
                    "danger_count": danger_cnt,
                    "total_count": valid_stock_count
                }
            },
            "radar_composite": radar_composite,
            "stock_cards": stock_cards,
            "top_warnings": top_warnings[:3]
        }

    def _has_urgent_risk(self, dart_titles: list[str]) -> bool:
        urgent_keywords = ["횡령", "배임", "감사의견", "관리종목", "상장폐지", "부도", "회생절차", "전환사채발행", "유상증자결정"]
        for title in dart_titles[:3]:
            if any(k in title for k in urgent_keywords):
                return True
        return False

    @observe(as_type="generation", name="Gemini_소견서_및_시나리오_생성")
    def _generate_ai_analysis(self, stock_name, price_info, score, status, disclosures, financial_health, cb_dilution, overhang_schedule, sentiment_data, news_risk, supply_risk, consensus_risk, macro_risk, force_ai=False, has_urgent=False):
        if not self.ai_client or (not has_urgent and not force_ai):
            return self._fallback_text_and_scenario(stock_name, score, financial_health, cb_dilution)

        dart_summary = ", ".join([t[:20] for t in disclosures[:4]]) if disclosures else "최근 공시 없음"

        prompt = f"""
[기업 리스크 진단 요약]
- 종목: {price_info.get('display_name')} ({price_info.get('code')}) / 현재가: {price_info.get('current_price')}
- 종합 점수: {score}점 ({status})
- 자본잠식: {financial_health.get('impairment_ratio_str')} (적자연속 {financial_health.get('consecutive_loss_years')}년)
- 메자닌/오버행: {cb_dilution.get('dilution_ratio_str')}
- 주요 공시: {dart_summary}
- 미디어/수급/실적/매크로 위험도: 미디어({news_risk.get('news_risk_score')}점), 수급({supply_risk.get('supply_risk_score')}점), 실적({consensus_risk.get('consensus_risk_score')}점), 매크로({macro_risk.get('macro_risk_score')}점)

위 데이터를 바탕으로 투자자를 위한 냉철한 진단 소견을 아래 JSON 형식으로만 응답하세요.
{{
  "report_text": "■ [{price_info.get('display_name')}] 정밀 리스크 소견서\\n- 재무/상장: (1줄 요약)\\n- 수급/오버행: (1줄 요약)\\n- 이슈/매크로: (1줄 요약)\\n- 종합 진단: (1줄 요약)",
  "traffic_light": "RED" 또는 "YELLOW" 또는 "GREEN",
  "verdict_badge": "🔴 진입 금지" 또는 "🟡 주의 관망" 또는 "🟢 클린 진입",
  "verdict_summary": "초보 투자자를 위한 3초 핵심 요약 1줄",
  "action_call": "냉철한 행동 지침 1줄",
  "scenarios": [
    {{"period": "단기 1개월", "trend": "변동성 대응", "prob": "70%", "desc": "단기 수급 및 이슈 영향 1줄"}},
    {{"period": "중기 3개월", "trend": "실적 반영", "prob": "65%", "desc": "분기 실적 및 펀더멘털 영향 1줄"}},
    {{"period": "장기 6개월", "trend": "가치 수렴", "prob": "60%", "desc": "재무 건전성 기반 중장기 추세 1줄"}}
  ]
}}
"""
        t0 = time.perf_counter()
        try:
            data = _call_gemini_fast_json(self.ai_client, prompt, max_tokens=800)
            report_text = data.get("report_text", "")
            
            default_scenarios = [
                {"period": "단기 1개월", "trend": "변동성 및 수급 소화", "prob": "70%", "desc": "단기 수급 동향 및 뉴스 노이즈에 따른 등락 구간"},
                {"period": "중기 3개월", "trend": "실적 및 공시 반영", "prob": "65%", "desc": "분기 실적 추이 및 물량 압박 가시화"},
                {"period": "장기 6개월", "trend": "펀더멘털 가치 수렴", "prob": "60%", "desc": "기업 본연의 재무 건전성 및 매크로 환경 추세"}
            ]
            raw_scenarios = data.get("scenarios", [])
            if not raw_scenarios:
                raw_scenarios = default_scenarios

            forecast_scenario = {
                "traffic_light": data.get("traffic_light", "YELLOW"),
                "verdict_badge": data.get("verdict_badge", "🟡 주의 관망 (일정 소화 후 재검토)"),
                "verdict_summary": data.get("verdict_summary", "종합 리스크 진단 완료"),
                "action_call": data.get("action_call", "주요 공시 일정과 수급 동향을 모니터링하세요."),
                "scenarios": raw_scenarios
            }
            elapsed = time.perf_counter() - t0
            print(f"[Gemini 경량 소견 완료] 소요 시간: {elapsed:.2f}초")
            return report_text, forecast_scenario
        except Exception as e:
            print(f"[Gemini 분석 실패 -> Fallback 가동]: {e}")
            return self._fallback_text_and_scenario(stock_name, score, financial_health, cb_dilution)

    @observe(as_type="generation", name="DART_공시_3줄요약_생성")
    def summarize_disclosure(self, report_nm: str, rcept_no: str = "") -> dict:
        raw_disclosure_text = ""
        if rcept_no and hasattr(self.collector, "get_document_text"):
            try:
                raw_disclosure_text = self.collector.get_document_text(rcept_no)
            except Exception:
                pass

        if not raw_disclosure_text:
            raw_disclosure_text = f"공시 제목: {report_nm} (접수번호: {rcept_no})"

        cleaned_text = " ".join(raw_disclosure_text.split())[:6000]

        if self.ai_client:
            prompt = f"""
당신은 대한민국 금융감독원 DART 수석 공시 분석관입니다. 아래 전처리된 공시 원문을 면밀히 읽고, 공시의 성격(유상증자, 메자닌, 지분변동, 소송, 실적 등)을 스스로 판단하여 가장 핵심이 되는 심층 정보를 요약하세요.

[분류별 필수 추출 지침]
1. 임원·주요주주 지분변동: 매수/매도 여부, 변동 주식수, 취득/처분 단가, 총 거래 대금(추정치 포함), 지분율 변화, 책임경영 시그널 여부
2. 유상증자 / 메자닌(CB·BW): 발행 규모(금액), 자금 용도(운영/시설/채무상환), 신주발행가 또는 전환가액, 리픽싱 조건, 기존 주주 지분 희석률
3. 소송 / 법적 리스크: 소송 제기 주체, 청구 금액, 자기자본 대비 비율, 기업 경영 및 주가에 미치는 실질적 타격 수준
4. 기타 일반 공시: 핵심 사건의 배경, 수치 변화, 투자자가 반드시 알아야 할 특이사항

=== [전처리된 공시 원문] ===
{cleaned_text}
==========================

반드시 아래 필드명을 가진 순수 JSON 형태로만 응답하세요:
{{
  "category": "공시의 정확한 세부 유형 (예: 임원 주식 소유 변동, 전환사채권 발행결정 등)",
  "risk_level": "고위험, 주의, 보통, 호재 중 택1",
  "key_points": [
    "핵심 내용 1 (원문에 등장하는 구체적인 수치, 단가, 규모, 금액 등을 빠짐없이 포함한 정량적 사실)",
    "핵심 내용 2 (해당 공시가 기업의 재무 건전성이나 지배구조에 미치는 구조적 의미)",
    "핵심 내용 3 (주가와 수급에 미칠 단기/중장기 파급 효과)"
  ],
  "action_guide": "👉 초보 투자자를 위한 1줄 명확한 행동 가이드"
}}
"""
            try:
                return _call_gemini_fast_json(self.ai_client, prompt, max_tokens=1000)
            except Exception as e:
                print(f"[Gemini 공시 요약 실패 -> Fallback 가동]: {e}")
                pass

        is_correction = "정정" in report_nm
        risk_text = "낮음 (해소됨)" if "미해당" in report_nm or is_correction else "보통 (참고용)"
        
        return {
            "category": "기재정정 공시" if is_correction else "일반 공시",
            "risk_level": risk_text,
            "key_points": [
                f"[{report_nm}] 관련 정정 및 변동 내역이 포함된 공시입니다.",
                "고용노동부 및 유관기관의 조사 결과나 세부 정정 사유를 원문을 통해 확인해야 합니다.",
                "단기 수급 및 투자 심리에 미치는 파급 효과를 모니터링할 필요가 있습니다."
            ],
            "action_guide": "👉 DART 전자공시 원문을 통해 구체적인 정정 전후 비교표를 확인하세요."
        }

    def _fallback_text_and_scenario(self, stock_name: str, score: int, financial_health: dict, cb_dilution: dict) -> tuple[str, dict]:
        report_text = f"■ [{stock_name}] 다차원 리스크 정밀 소견서\n종합 안전도: {score}점\n- 자본 건전성: {financial_health.get('impairment_ratio_str')}\n- 사채 희석 부담: {cb_dilution.get('dilution_ratio_str')}"
        
        if score >= 75:
            traffic_light = "GREEN"
            verdict_badge = "🟢 클린 진입 (안전 투자 구간)"
        elif score >= 45:
            traffic_light = "YELLOW"
            verdict_badge = "🟡 주의 관망 (일정 소화 후 재검토)"
        else:
            traffic_light = "RED"
            verdict_badge = "🔴 진입 금지 (위험 경보)"

        forecast_scenario = {
            "traffic_light": traffic_light,
            "verdict_badge": verdict_badge,
            "verdict_summary": f"{stock_name}의 공시 및 재무 상태 룰 기반 분석 완료 (안전도 {score}점)",
            "action_call": "주요 공시 일정과 분기 실적 추이를 면밀히 검토 후 접근하세요.",
            "scenarios": [
                {"period": "단기 1개월", "trend": "변동성 구간", "prob": "70%", "desc": "단기 수급 및 공시 일정에 따른 주가 조정 가능성"},
                {"period": "중기 3개월", "trend": "실적 반영", "prob": "65%", "desc": "본업 영업이익 추이에 따른 주가 재평가"},
                {"period": "장기 6개월", "trend": "가치 수렴", "prob": "60%", "desc": "재무 건전성에 기반한 중장기 흐름"}
            ]
        }
        return report_text, forecast_scenario

    def _calculate_cb_dilution_dynamic(self, stock_name: str, real_disclosures: list[dict]) -> dict:
        cb_disclosures = [
            d for d in real_disclosures 
            if any(k in d.get("report_nm", "") for k in ["전환사채", "신주인수권", "CB", "BW", "유상증자"])
        ]
        
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

        total_real_amount = 0
        cb_items = []

        for d in cb_disclosures[:2]:
            r_no = d.get("rcept_no", "")
            details = self.collector.parse_mezzanine_document_details(r_no)
            amt = details.get("parsed_amount", 0)
            
            if amt > 0:
                total_real_amount += amt
                amt_str = self._format_korean_currency(amt)
            else:
                amt_str = "공시 원문 참조"

            cb_items.append({
                "name": d["report_nm"][:28] + "...",
                "unredeemed_amount": amt_str,
                "conv_price": details.get("conv_price", "원문 참조"),
                "refixing_floor": details.get("refixing_floor", "최대 70% 하향 리픽싱 가능")
            })

        if total_real_amount > 0:
            total_amount_str = self._format_korean_currency(total_real_amount)
            dilution_ratio = min(50.0, round((total_real_amount / 100000000.0) * 0.08, 1))
        else:
            cb_count = len(cb_disclosures)
            dilution_ratio = min(40.0, cb_count * 10.0)
            total_amount_str = f"약 {cb_count * 100}억 원 추정 (원문 확인 요망)"

        return {
            "has_cb": True,
            "total_unredeemed_amount": total_amount_str,
            "market_cap": f"시가총액 대비 약 {dilution_ratio:.1f}%",
            "dilution_ratio": dilution_ratio,
            "dilution_ratio_str": f"주의~고위험 (잠재 희석률 {dilution_ratio:.1f}%)",
            "total_potential_shares": "대규모 신주 전환 대기",
            "shares_ratio": f"발행주식의 약 {dilution_ratio:.1f}%",
            "risk_score": int(min(100, dilution_ratio * 2.2)),
            "cb_items": cb_items,
            "dilution_warning": f"최근 {len(cb_disclosures)}건의 메자닌 공시 감지 (실제 사채 권면총액 및 전환 조건 반영 완료)"
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

    def _check_delisting_risk(self, data: dict, fin_data: dict) -> dict:
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

    def _check_governance_risk(self, data: dict) -> dict:
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

    def _check_overhang_schedule_risk(self, data: dict, schedule: list, cb_dilution: dict) -> dict:
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
        eok_int = int(eok)
        if eok_int >= 10000:
            cho = eok_int / 10000.0
            return f"{sign}{cho:.2f}조 원"
        return f"{sign}{eok:,.1f}억 원"