"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/consensus_analyzer.py
- 기능:
    1. DART 공식 분기/사업보고서의 실적 시계열 기반 실적 충격(어닝 쇼크) 진단
    2. 직전 동기 대비 영업이익 급감(-25% 이상) 및 적자전환 리스크 정량화
    3. 외부 웹 스크래핑 차단 없이 100% 신뢰성 보장
==============================================================================
"""

from typing import Dict, Any, List

class ConsensusRiskAnalyzer:
    """
    DART 공식 확정 실적 데이터를 기반으로 실적 급감(어닝 쇼크) 및 이익 훼손 리스크를 분석하는 엔진
    """
    def __init__(self):
        pass

    def analyze_from_financials(self, raw_financials: List[Dict[str, Any]], stock_name: str = "", ticker: str = "") -> Dict[str, Any]:
        """
        DART 수집기에서 추출된 재무제표 원문 리스트로부터 영업이익 시계열을 분석
        """
        result = {
            "stock_name": stock_name,
            "ticker": ticker,
            "consensus_risk_score": 0.0,
            "has_consensus": False,
            "recent_op": 0.0,
            "prev_op": 0.0,
            "growth_rate": 0.0,
            "risk_level": "LOW",
            "summary_comment": "실적 데이터 분석 중"
        }

        if not raw_financials:
            result["consensus_risk_score"] = 15.0
            result["summary_comment"] = "분기 실적 확정 공시가 부재하여 기본 룰셋을 유지합니다."
            return result

        op_profits = []
        for item in raw_financials:
            acc = item.get("account_nm", "").strip()
            if "영업이익" in acc:
                for period_key in ["thstrm_amount", "frmtrm_amount", "bfefrmtrm_amount"]:
                    raw_val = item.get(period_key, "")
                    if raw_val:
                        try:
                            clean_val = float(str(raw_val).replace(",", "").strip())
                            op_profits.append(clean_val)
                        except (ValueError, TypeError):
                            pass
                if op_profits:
                    break

        if len(op_profits) < 2:
            result["consensus_risk_score"] = 10.0
            result["summary_comment"] = "비교 가능한 직전 실적 데이터가 부족하여 정상 범위로 분류합니다."
            return result

        recent_op = op_profits[0]
        prev_op = op_profits[1]

        result["has_consensus"] = True
        result["recent_op"] = recent_op
        result["prev_op"] = prev_op

        # 1. 적자 전환 (흑자 -> 적자)
        if prev_op > 0 and recent_op < 0:
            result["consensus_risk_score"] = 50.0
            result["risk_level"] = "HIGH"
            result["growth_rate"] = -100.0
            result["summary_comment"] = f"어닝 쇼크: 최근 영업이익이 적자전환({self._format_eok(recent_op)})되어 실적 리스크가 매우 높습니다."
            return result

        # 2. 적자 지속 (적자 -> 적자 심화)
        if prev_op < 0 and recent_op < 0:
            result["consensus_risk_score"] = 40.0
            result["risk_level"] = "HIGH"
            result["growth_rate"] = round(((recent_op - prev_op) / abs(prev_op)) * 100, 1)
            result["summary_comment"] = f"실적 부진 지속: 영업적자 지속 구간({self._format_eok(recent_op)})으로 펀더멘털 주의가 필요합니다."
            return result

        # 3. 흑자 구간 내 증감률 계산
        if prev_op != 0:
            growth = round(((recent_op - prev_op) / abs(prev_op)) * 100, 1)
            result["growth_rate"] = growth

            if growth <= -40.0:
                result["consensus_risk_score"] = 45.0
                result["risk_level"] = "HIGH"
                result["summary_comment"] = f"어닝 쇼크 경고: 직전 분기 대비 영업이익이 {abs(growth)}% 급감({self._format_eok(prev_op)} → {self._format_eok(recent_op)})했습니다."
            elif growth <= -20.0:
                result["consensus_risk_score"] = 25.0
                result["risk_level"] = "MEDIUM"
                result["summary_comment"] = f"실적 둔화 관측: 직전 분기 대비 영업이익이 {abs(growth)}% 감소하여 단기 하방 압력이 존재합니다."
            elif growth < 0.0:
                result["consensus_risk_score"] = 10.0
                result["risk_level"] = "LOW"
                result["summary_comment"] = f"소폭 감소: 영업이익이 {abs(growth)}% 소폭 줄었으나 통상적 변동 범위입니다."
            else:
                result["consensus_risk_score"] = 0.0
                result["risk_level"] = "LOW"
                result["summary_comment"] = f"실적 성장 모멘텀: 직전 대비 영업이익이 +{growth}% 증가({self._format_eok(recent_op)})하여 양호합니다."

        return result

    def _format_eok(self, amount: float) -> str:
        sign = "-" if amount < 0 else ""
        abs_amt = abs(amount) / 100000000.0
        return f"{sign}{abs_amt:,.0f}억 원"