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

```
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
```

---

## ⚡ 3. 핵심 기능 (Key Features)

### 🔍 1) 단일 종목 다차원 지뢰 진단
* **Safety Score (0~100점):** 공시 및 뉴스 리스크 키워드 가중치 기반 안전 점수 산출
* **다차원 리스크 지형도 (Radar Chart):** 전환사채(CB), 유상증자, 지배구조 리스크 등을 다각도로 가시화
* **AI 진단 소견서:** 초보자도 이해하기 쉬운 요약형 리스크 브리핑 리포트 자동 생성

### ⭐ 2) 관심 종목 가디언 (Watchlist) & 일괄 스캔
* 매수를 고민 중인 종목들을 장바구니처럼 담아두고 투자 메모 관리
* **원클릭 일괄 지뢰 탐지:** 담아둔 모든 종목의 공시 악재를 백엔드에서 병렬 분석하여 안전도 카드 제공

### 🔐 3) 상용 앱 수준의 인증 & 온보딩 플로우
* **소셜 간편로그인(카카오/네이버/구글) & 온보딩:** 최초 소셜 가입 시 닉네임, 알림용 이메일, 투자 경험을 받는 2단계 온보딩 지원
* **법적 동의 체계 준수:** 개인정보 보호법 및 정보통신망법에 맞춘 이용약관(AI 면책 조항) 및 긴급 공시 알림 동의 팝업 제공

### ⚙️ 4) 관리자 센터 (Admin / Master)
* `master` / `admin` 전용 권한 분기
* 전체 회원 현황(가입 경로, 투자 경험, 관심종목 수, 마케팅 동의 여부) 및 사용자 문의/피드백 실시간 모니터링

---

## 🛠️ 4. 기술 스택 (Tech Stack)

### Backend
* **Language / Framework:** Python 3.11+, FastAPI, Uvicorn
* **Database:** SQLite (Native connection)
* **Data & AI Engine:** DART Open API, Pandas, Regex Anonymizer, Scikit-learn

### Frontend
* **Framework:** Next.js 16 (App Router), TypeScript
* **Styling:** Tailwind CSS, Lucide React (Icons)
* **Data Visualization:** Recharts (Radar / Responsive Chart)
* **HTTP Client:** Axios

---

## 🚀 5. 시작 가이드 (Getting Started)

### 1) 저장소 클론 및 가상환경 설정
```powershell
git clone [https://github.com/your-repo/Financial-Multi-Risk-Guardian.git](https://github.com/your-repo/Financial-Multi-Risk-Guardian.git)
cd Financial-Multi-Risk-Guardian

# Python 가상환경 생성 및 패키지 설치
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

### 2) 백엔드(FastAPI) 실행
```powershell
# 프로젝트 루트 디렉토리에서 실행
python app.py
```
> 백엔드 서버: `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)

### 3) 프론트엔드(Next.js) 실행
```powershell
# 새 터미널 창에서 실행
cd frontend-web
npm install
npm run dev
```
> 웹 대시보드: `http://localhost:3000`

---

## 🧪 6. 테스트 계정 안내 (Demo Accounts)

| 권한 | 아이디 | 비밀번호 | 닉네임 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **Master** | `master` | `master1234` | 총괄마스터 | 관리자 센터 전체 권한 |
| **Admin** | `admin` | `admin1234` | 운영관리자 | 회원/문의 모니터링 |
| **User** | `tester1` | `tester1234` | 성투하는라이언 | 샘플 관심종목(모아데이타, 카카오) 탑재 |
| **User** | `tester2` | `tester1234` | 주식꿈나무 | 샘플 관심종목(삼성전자) 탑재 |

---

## 📜 7. 법적 고지 (Disclaimer)

본 서비스가 제공하는 모든 점수(Safety Score), 지표 및 AI 리포트는 투자 판단을 돕기 위한 **단순 참고용 자료**이며, 특정 금융투자상품의 매수/매도를 추천하거나 원금을 보장하지 않습니다. 최종 투자 결정과 손익에 대한 모든 책임은 투자자 본인에게 있습니다.