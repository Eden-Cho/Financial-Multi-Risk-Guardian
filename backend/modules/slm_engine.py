import os
import sys
import json
import requests
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()


class SLMEngine:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate_risk_report(self, stock_name: str, safety_score: int, risk_dim: dict, dart_items: list[dict], news_items: list[dict]) -> str:
        """
        수집/비식별화된 데이터를 종합하여 전문가 수준의 금융 리스크 진단 보고서 텍스트를 생성합니다.
        """
        # 프롬프트 입력용 컨텍스트 정리
        dart_summary = "\n".join([f"- [{d.get('rcept_dt', '')}] {d.get('report_nm', '')} (제출인: {d.get('flr_nm', '')})" for d in dart_items[:8]]) or "특이 공시 없음"
        news_summary = "\n".join([f"- [{n.get('press', '')}] {n.get('title', '')}" for n in news_items[:5]]) or "특이 뉴스 없음"
        
        prompt = f"""당신은 기업 금융 리스크 및 공시 분석 전문 수석 애널리스트입니다.
아래 제공된 기업의 실시간 DART 전자공시 및 언론 뉴스 분석 데이터를 바탕으로 투자자를 위한 정밀 리스크 진단 보고서를 작성하세요.

[분석 기업]: {stock_name}
[종합 안전 점수]: {safety_score}/100 점
[5대 리스크 축 평가 점수 (100점 만점, 높을수록 위험)]:
- 공시/오버행(CB·BW): {risk_dim.get('공시/오버행(CB·BW)', 0)}점
- 언론 뉴스 악재: {risk_dim.get('언론 뉴스 악재', 0)}점
- 지배구조/오너리스크: {risk_dim.get('지배구조/오너리스크', 0)}점
- 관리종목/상폐우려: {risk_dim.get('관리종목/상폐우려', 0)}점
- 자본변동/유상증자: {risk_dim.get('자본변동/유상증자', 0)}점

[DART 전자공시 내역 (최근)]:
{dart_summary}

[실시간 주요 뉴스]:
{news_summary}

[작성 가이드라인]:
1. 마크다운 형식으로 가독성 있게 작성하세요.
2. 다음 3개 섹션을 반드시 포함하세요:
   - 🚨 **1. 핵심 리스크 요인 정밀 진단** (CB/BW 오버행, 유상증자, 주식병합, 관리종목 우려 등 실제 감지된 항목 구체적 서술)
   - 📉 **2. 주가 및 지분 가치 희석 영향도** (자본 변동에 따른 기존 주주 가치 희석 가능성 분석)
   - 💡 **3. 투자자 대응 및 모니터링 가이드** (단기 변동성 주의점 및 향후 확인해야 할 핵심 공시 일정)
"""
        # 1. OpenAI API 호출 시도 (키가 있을 경우)
        if self.openai_key:
            try:
                res = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a professional financial risk analyst."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3
                    },
                    timeout=15
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                pass

        # 2. 키가 없거나 실패 시: 규칙 기반 정밀 금융 리포트 자동 생성 (Fallback Engine)
        return self._generate_rule_based_report(stock_name, safety_score, risk_dim, dart_items, news_items)

    def _generate_rule_based_report(self, stock_name: str, safety_score: int, risk_dim: dict, dart_items: list[dict], news_items: list[dict]) -> str:
        """SLM/LLM API 미연결 시 즉시 가동되는 전문가 룰 기반 리포트 생성기"""
        status_label = "위험 (투자유의)" if safety_score < 40 else ("경고" if safety_score < 60 else "주의" if safety_score < 80 else "안전")
        
        report = f"""### 🛡️ [{stock_name}] AI 다차원 리스크 정밀 진단 리포트

**종합 안전 평가:** `{status_label}` (Safety Score: **{safety_score}점** / 100점)

---

#### 🚨 1. 핵심 리스크 요인 정밀 진단
"""
        risk_found = False
        if risk_dim.get("공시/오버행(CB·BW)", 0) >= 50:
            report += "• **전환사채(CB) 및 파생 증권 오버행 리스크:** 자기전환사채 취득/매도 및 전환청구권 행사 가능성으로 인해 잠재적 매도 물량 출회 압박이 매우 높습니다.\n"
            risk_found = True
        if risk_dim.get("자본변동/유상증자", 0) >= 50:
            report += "• **빈번한 자본 변동(유상증자·주식병합):** 소액공모 및 유상증자 결정, 주식병합 공시가 연속 발생하여 유통 주식수 및 자본금 구조의 급격한 변동이 진행 중입니다.\n"
            risk_found = True
        if risk_dim.get("관리종목/상폐우려", 0) >= 50:
            report += "• **시장 조치 및 관리종목 지정 우려:** 주가 기준 미달 등으로 인한 관리종목 지정 우려 공시가 확인되어 상장 유지 요건 충족 여부를 상시 감시해야 합니다.\n"
            risk_found = True
        if risk_dim.get("지배구조/오너리스크", 0) >= 40:
            report += "• **최대주주 주식담보대출 및 지분 변동:** 최대주주 변경을 수반하는 주식 담보 제공 계약이 체결되어 있어 반대매매로 인한 경영권 불안정 위험이 상존합니다.\n"
            risk_found = True
        if not risk_found:
            report += "• 최근 6개월간 자본 잠식, 오버행, 횡령/배임 등 치명적인 비정형 공시 악재는 식별되지 않았습니다.\n"

        report += """
#### 📉 2. 주가 및 지분 가치 희석 영향도
"""
        if safety_score < 50:
            report += "• 대규모 신주 발행(유상증자) 및 CB 전환 물량이 유입될 경우 **기존 주주의 지분 가치 희석(Dilution)**과 함께 주가 하방 압력이 가중될 수 있습니다.\n"
            report += "• 주식병합 및 신주 상장 일정 전후로 거래량 왜곡 및 이상 변동성 발생 가능성이 높으므로 뇌동매매를 지양해야 합니다.\n"
        else:
            report += "• 주요 재무 및 공시 지표가 양호한 상태를 유지하고 있어 단기적인 지분 가치 훼손 위험은 제한적입니다.\n"

        report += """
#### 💡 3. 투자자 대응 및 모니터링 가이드
"""
        if safety_score < 60:
            report += "• **필수 확인 일정:** 신주 상장 예정일, 주식병합 효력발생일, 관리종목 해제 요건 충족 여부 공시를 실시간 체크하세요.\n"
            report += "• **투자 전략:** 변동성이 큰 구간이므로 분할 매수 또는 공시 불확실성이 해소되는 시점까지 보수적 관망을 권고합니다.\n"
        else:
            report += "• 중장기 펀더멘털과 실적 공시 추이를 중심으로 안정적인 포트폴리오를 유지하는 것을 권장합니다.\n"

        return report


if __name__ == "__main__":
    engine = SLMEngine()
    dummy_dim = {
        "공시/오버행(CB·BW)": 100,
        "언론 뉴스 악재": 35,
        "지배구조/오너리스크": 50,
        "관리종목/상폐우려": 60,
        "자본변동/유상증자": 100
    }
    dummy_dart = [{"rcept_dt": "20260814", "report_nm": "주요사항보고서(유상증자결정)", "flr_nm": "모아데이타"}]
    res = engine.generate_risk_report("모아데이타", 31, dummy_dim, dummy_dart, [])
    print(res)