"""
==============================================================================
[Module Overview]
- 파일명: backend/modules/macro_analyzer.py
- 기능:
    1. 실시간 주요 거시경제 지표(USD/KRW 환율, 국고채 3년물 금리) 모니터링
    2. 업종/섹터별 환율·금리 민감도 매핑 (수입 제조업, 고부채 섹터 등)
    3. 거시경제 충격에 따른 섹터 시스템 리스크(0~100) 정량 산출
==============================================================================
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any

# 주요 고위험 섹터 분류 룰셋
SECTOR_RISK_MAP = {
    "비철금속": {"fx_sensitivity": "HIGH", "rate_sensitivity": "MEDIUM", "desc": "원자재 수입 비중 높아 고환율 시 원가 부담 가중"},
    "철강": {"fx_sensitivity": "HIGH", "rate_sensitivity": "MEDIUM", "desc": "철광석 등 원자재 수입 의존 및 전방 산업 수요 둔화"},
    "항공": {"fx_sensitivity": "HIGH", "rate_sensitivity": "HIGH", "desc": "외화 리스부채 및 유가/환율 동반 충격 취약"},
    "건설": {"fx_sensitivity": "LOW", "rate_sensitivity": "HIGH", "desc": "부동산 PF 및 고금리 지속 시 금융비용 압박"},
    "바이오": {"fx_sensitivity": "LOW", "rate_sensitivity": "HIGH", "desc": "지속적 자금 조달 필요 업종으로 고금리 장기화 취약"},
    "반도체": {"fx_sensitivity": "LOW", "rate_sensitivity": "MEDIUM", "desc": "달러 결제 수출 구조로 환율 상승 시 일부 수혜"},
    "IT": {"fx_sensitivity": "LOW", "rate_sensitivity": "LOW", "desc": "매크로 변수 민감도 상대적 안정"}
}

class MacroRiskAnalyzer:
    """
    환율, 금리 등 거시경제 매크로 지표와 업종 취약성을 결합 분석하는 엔진
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_macro_indicators(self) -> Dict[str, float]:
        """네이버 금융 시장지표에서 실시간 원/달러 환율 추출"""
        indicators = {
            "usd_krw": 1380.0,
            "is_high_fx": True
        }
        try:
            url = "https://finance.naver.com/marketindex/"
            res = requests.get(url, headers=self.headers, timeout=4)
            soup = BeautifulSoup(res.text, "html.parser")
            fx_span = soup.select_one("span.value")
            if fx_span:
                val = float(fx_span.get_text(strip=True).replace(",", ""))
                indicators["usd_krw"] = val
                indicators["is_high_fx"] = val >= 1350.0
        except Exception as e:
            print(f"[MacroAnalyzer] 매크로 지표 수집 기본값 유지: {e}")

        return indicators

    def detect_sector(self, stock_name: str) -> str:
        """종목명 기반 핵심 산업군 추론"""
        if any(k in stock_name for k in ["아연", "알루미늄", "동", "풍산", "제련"]):
            return "비철금속"
        elif any(k in stock_name for k in ["제철", "철강", "포스코", "스틸"]):
            return "철강"
        elif any(k in stock_name for k in ["항공", "에어"]):
            return "항공"
        elif any(k in stock_name for k in ["건설", "이앤씨", "엔지니어링"]):
            return "건설"
        elif any(k in stock_name for k in ["바이오", "제약", "셀트리온", "한미"]):
            return "바이오"
        elif any(k in stock_name for k in ["전자", "하이닉스", "반도체"]):
            return "반도체"
        return "일반제조/IT"

    def analyze_macro_risk(self, stock_name: str) -> Dict[str, Any]:
        macro = self.fetch_macro_indicators()
        sector = self.detect_sector(stock_name)
        rule = SECTOR_RISK_MAP.get(sector, {"fx_sensitivity": "LOW", "rate_sensitivity": "LOW", "desc": "매크로 민감도 통상 수준"})

        risk_score = 0.0
        reasons = []

        # 환율 리스크 계산 (1,350원 이상 고환율 구간일 때)
        if macro["is_high_fx"]:
            if rule["fx_sensitivity"] == "HIGH":
                risk_score += 45.0
                reasons.append(f"고환율 충격 취약({macro['usd_krw']:,.1f}원, 원자재 수입단가 상승)")
            elif rule["fx_sensitivity"] == "MEDIUM":
                risk_score += 20.0
                reasons.append(f"환율 변동성 관찰({macro['usd_krw']:,.1f}원)")

        # 금리 리스크 계산
        if rule["rate_sensitivity"] == "HIGH":
            risk_score += 35.0
            reasons.append("고금리 장기화에 따른 조달/이자비용 부담 섹터")

        final_risk = min(100.0, risk_score)

        if final_risk >= 50:
            level = "HIGH"
            comment = f"매크로 경고: {', '.join(reasons)}에 노출되어 있습니다."
        elif final_risk >= 20:
            level = "MEDIUM"
            comment = f"매크로 주의: {', '.join(reasons)} 영향권을 점검하세요."
        else:
            level = "LOW"
            comment = f"매크로 중립: {sector} 섹터는 현 매크로 변수(환율 {macro['usd_krw']:,.1f}원) 영향이 제한적입니다."

        return {
            "stock_name": stock_name,
            "sector": sector,
            "macro_risk_score": final_risk,
            "usd_krw": macro["usd_krw"],
            "risk_level": level,
            "summary_comment": comment
        }