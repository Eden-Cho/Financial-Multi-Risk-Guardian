# 🛡️ Financial Multi-Risk Guardian (금융 다차원 리스크 가디언)
> **"주린이를 위한 DART 공시 기반 다차원 지뢰 탐지 & 뇌동매매 방지 비서"**

---

## 📌 1. 프로젝트 개요 (Overview)

개인 투자자(주린이)가 유튜브, SNS, 급등 뉴스에 현혹되어 **매수 버튼을 누르기 직전**, 해당 기업의 잠재적 리스크(전환사채 오버행, 유상증자, 감자, 관리종목 지정 징후 등)를 실시간으로 탐지하고 AI 진단 소견서를 제공하여 **뇌동매매를 방지하고 투자자를 보호하는 풀스택 핀테크 솔루션**입니다.

* **타깃 사용자:** 공시 해석이 어려운 개인 초보 투자자
* **핵심 가치:** 
  1. **정보 비대칭 해소:** 복잡한 DART 전자공시 데이터의 직관적 시각화
  2. **Security-First:** 금융 및 개인정보 비식별화(Anonymizer) 파이프라인 탑재
  3. **실시간 리스크 감시:** 관심 종목 일괄 지뢰 스캔 및 긴급 공시 이메일 알림 연동 체계 구축

---

## 🏗️ 2. 시스템 아키텍처 (System Architecture)

```text
[ DART Open API ] ──┐
                     ├──▶ [ Data Pipeline ] ──▶ [ Security Anonymizer ]
[ Naver News API ] ──┘                              │ (개인정보/식별자 마스킹)
                                                    ▼
                                         [ Multi-Risk Analyzer ]
                                          - CB/BW 오버행 분석
                                          - 재무/공시 건전성 진단
                                          - Safety Score & 레이더 차트 산출
                                                    │
                                                    ▼
                                          [ FastAPI REST Backend ]
                                          - 사용자 인증 & 소셜 온보딩
                                          - 포트폴리오(Watchlist) 관리
                                          - 피드백/문의 및 관리자 센터
                                                    │
                                                    ▼
                                      [ Next.js Modern Frontend ]
                                      - 반응형 대시보드 & 레이더 차트
                                      - 상용 앱 스타일 온보딩 & 약관 모달