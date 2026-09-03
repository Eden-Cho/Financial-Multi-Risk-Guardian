# 🛡️ Financial Risk Guardian (K-Stock Risk Radar)

> **DART 전자공시 & 재무 데이터 기반 상장유지/오버행 리스크 조기 감지 및 초개인화 AI 포트폴리오 관제 솔루션**

대한민국 주식 시장(코스피/코스닥)의 상장폐지 요건(자본잠식, 연속적자), 메자닌 채권(CB/BW) 희석 리스크, 지배구조 이상 징후를 실시간으로 탐지하고, **Gemini AI 정밀 소견서**와 **KR-FinBERT 공시 감성 지표**를 제공합니다.

---

## 🌟 핵심 기능 (Key Features)

1. **하이브리드 캐시 & 스마트 무효화 (Smart Invalidation)**
   * **초고속 응답 (0.01s ~ 0.2s)**: 기존 분석 결과와 기초 재무는 SQLite 로컬 공유 DB를 통해 즉각 반환.
   * **돌발 악재 실시간 감지**: DART 최신 접수번호(rcept_no) 및 긴급 위험 공시(횡령/배임, 감사의견, CB 발행 등)를 실시간 대조하여 악재 발생 시에만 즉각 Gemini 재호출 & DB 자동 갱신.

2. **합집합(Union) 배치 동기화 & 공유 저장소**
   * 사용자별 관심 종목(Watchlist)을 취합하여 **고유 종목의 합집합(Deduplication)**을 자동 도출.
   * DART API 호출 제한(Rate Limit)을 극대화하여 절약하면서, 여러 사용자가 동일 종목을 공유 캐시로 즉시 조회.

3. **다차원 리스크 정량 진단 (5-Axis Radar)**
   * 상장유지 리스크 (자본잠식률, 영업손실 연속성)
   * 잠재물량 부담 (CB/BW/유상증자 오버행 일정)
   * 지배구조 변동성 (최대주주 변경, 임원 블록딜)
   * 재무 부실도 & 사채 희석률

4. **생성형 AI & 특화 NLP 심층 리포트**
   * **Gemini Flash 기반 정밀 분석**: 초보 투자자 관점의 1줄 액션 가이드, 3~6개월 시나리오 예측.
   * **KR-FinBERT 금융 감성 분석**: 금융감독원 공시 문장의 긍정/부정/중립 여론 지수화.
   * **Langfuse 관제**: LLM 레이턴시, 토큰 소모량, 파이프라인 전체 추적(Observability).

---

## 🏗️ 시스템 아키텍처 (System Architecture)

[사용자 검색 / 관심 종목 요청]
          │
          ├── 1. [로컬 SQLite 공유 DB] 기초 재무 및 이전 분석 캐시 확인 (0.001s)
          │
          ├── 2. [DART API] 실시간 최신 공시 접수번호 및 긴급 악재 키워드 검사 (0.2s)
          │
          └── 3. [조건부 파이프라인 분기]
                  ├─ [안전 / 캐시 유효] ──► 실시간 시세 결합 후 즉시 반환 (0.01s)
                  └─ [돌발 악재 / 신규] ──► Gemini 분석 ──► DB 스냅샷 갱신 ──► 결과 반환

---

## 📁 프로젝트 구조 (Project Structure)

├── backend/
│   ├── modules/
│   │   ├── analyzer.py           # 스마트 캐시 분기 & 다차원 리스크 판정 엔진
│   │   ├── batch_sync.py         # 관심종목 합집합 도출 및 DART 배치 동기화
│   │   ├── storage.py            # SQLite 기반 재무/리포트/관심종목 공유 DB 관리자
│   │   ├── dart_collector.py     # DART Open API 연동 및 고유번호/공시 수집기
│   │   ├── price_collector.py    # 네이버 금융 실시간 시세 및 우선주 괴리율 파서
│   │   └── sentiment_analyzer.py # snunlp/KR-FinBert-SC 기반 감성 분석기
├── frontend/                     # Next.js 14 기반 대시보드 UI
├── app.py                        # FastAPI 백엔드 서버 & RESTful API
├── .env.example                  # 환경 변수 템플릿
├── requirements.txt              # 백엔드 의존성 패키지 목록
└── README.md

---

## 🚀 빠른 시작 가이드 (Getting Started)

### 1. 환경 변수 설정
프로젝트 루트에 .env 파일을 생성하고 발급받은 API 키를 입력합니다.

DART_API_KEY=your_dart_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Langfuse LLM 관제 (선택 사항)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=[https://cloud.langfuse.com](https://cloud.langfuse.com)

### 2. 백엔드(FastAPI) 실행
# 가상환경 활성화 후 의존성 설치
pip install -r requirements.txt

# 서버 실행 (포트: 8000)
python app.py

### 3. 프론트엔드(Next.js) 실행
cd frontend
npm install
npm run dev
# http://localhost:3000 접속

---

## 🔌 주요 API 명세 (API Endpoints)

| Method | Endpoint | 설명 |
|---|---|---|
| GET | /api/analyze?company={name} | 특정 종목 다차원 심층 분석 (스마트 캐시 적용) |
| GET | /api/quick_scan?company={name} | 일괄 진단용 경량 스캔 |
| GET | /api/watchlist?user_id={id} | 사용자 등록 관심 종목 리스트 및 일괄 안전도 조회 |
| POST | /api/watchlist/add | 관심 종목 등록 (백그라운드 동기화 큐 적재) |
| POST | /api/watchlist/remove | 관심 종목 해제 |
| GET | /api/disclosure/summary | 개별 공시 보고서 3줄 AI 요약 및 행동 가이드 |
| POST | /api/admin/sync_financials | 관심 종목 합집합 재무제표 수동 배치 동기화 트리거 |

---

## 🛡️ 라이선스 (License)
This project is licensed under the MIT License.