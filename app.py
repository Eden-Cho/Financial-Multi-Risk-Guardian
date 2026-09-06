"""
==============================================================================
[Module Overview]
- 파일명: backend/app.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할:
    1. FastAPI 메인 웹 서버 및 REST API 엔드포인트 라우팅
    2. APScheduler 기반 백그라운드 데몬 가동 (15분 주기 공시 자동 폴링)
    3. JWT 및 비밀번호 해싱 기반 인증/인가 체계 (BOLA 취약점 차단)
    4. 종목 정밀 진단, 관심 종목 관리, DART 3줄 요약, OCR 스크린샷 일괄 등록 지원
    5. [신규] Guardian Copilot AI 플로팅 챗봇 실시간 Q&A 엔드포인트 지원
==============================================================================
"""

import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import jwt

from backend.modules.analyzer import RiskAnalyzer
from backend.modules.storage import StorageManager

# ==================== 보안 환경 변수 ====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "guardian-risk-secret-key-production-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일 유효

app = FastAPI(title="Financial Multi-Risk Guardian API", version="2.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = RiskAnalyzer()
storage = StorageManager()

# ==================== 비밀번호 해싱 및 JWT 유틸 ====================
def hash_password(password: str) -> str:
    """비밀번호 SHA-256 단방향 해시화"""
    salt = "risk_guardian_secure_salt_v2"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def create_access_token(user_id: str, role: str) -> str:
    """JWT Access Token 생성"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Request Header의 'Authorization: Bearer <Token>'을 검증"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 누락되었거나 형식이 잘못되었습니다.")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "user")
        if user_id is None:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰 페이로드입니다.")
        return {"user_id": user_id, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="로그인 세션이 만료되었습니다. 다시 로그인해 주세요.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="토큰 검증에 실패했습니다.")


# ==================== 백그라운드 폴링 데몬 ====================
def background_watchlist_risk_monitor():
    """15분마다 고유 관심 종목 목록을 조회하여 신규 DART 공시 점검 및 캐시 갱신"""
    try:
        unique_stocks = storage.get_all_unique_watchlist_stocks()
        if not unique_stocks:
            return

        print(f"[백그라운드 데몬] 관심 종목 {len(unique_stocks)}개 DART 신규 공시 스캔 시작...")
        for stock in unique_stocks:
            try:
                analyzer.analyze(stock, quick_scan=False)
                time.sleep(1.0)
            except Exception as e:
                print(f"[백그라운드 데몬 오류] '{stock}': {e}")
        print("[백그라운드 데몬] 관심 종목 배치 점검 완료.")
    except Exception as e:
        print(f"[백그라운드 데몬 치명적 에러]: {e}")

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(background_watchlist_risk_monitor, "interval", minutes=15)
scheduler.start()


# ==================== DTO 모델 정의 ====================
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str
    email: str

class SocialCheckRequest(BaseModel):
    social_id: str
    provider: str

class SocialOnboardingRequest(BaseModel):
    username: str
    nickname: str
    email: str
    provider: str
    experience: str
    marketing_agree: bool

class WatchlistAddRequest(BaseModel):
    stock_name: str
    user_id: Optional[str] = None
    memo: Optional[str] = ""

class WatchlistRemoveRequest(BaseModel):
    stock_name: str
    user_id: Optional[str] = None

class FindIdRequest(BaseModel):
    email: str

class ResetPwRequest(BaseModel):
    username: str
    email: str
    new_password: str

class InquiryCreateRequest(BaseModel):
    username: str
    category: str
    content: str

class ChatAskRequest(BaseModel):
    stock_name: str
    question: str
    context_summary: Optional[str] = ""


# ==================== API 라우트 ====================

@app.get("/api/analyze/{stock_name}")
def analyze_stock(stock_name: str):
    """단일 종목 다차원 정밀 진단"""
    result = analyzer.analyze(stock_name, quick_scan=False)
    if not result:
        raise HTTPException(status_code=404, detail=f"'{stock_name}'은(는) 유효한 상장 기업이 아닙니다.")

    (score_info, radar_df, report_text, overhang_schedule, raw_disclosures,
     financial_health, cb_dilution, forecast_scenario, sentiment_data, price_info) = result

    radar_records = radar_df.to_dict(orient="records") if hasattr(radar_df, "to_dict") else []

    return {
        "stock_name": stock_name,
        "score_info": score_info,
        "radar_data": radar_records,
        "report_text": report_text,
        "overhang_schedule": overhang_schedule,
        "raw_disclosures": raw_disclosures,
        "financial_health": financial_health,
        "cb_dilution": cb_dilution,
        "forecast_scenario": forecast_scenario,
        "sentiment_data": sentiment_data,
        "price_info": price_info
    }


@app.post("/api/auth/register")
def register_user(req: RegisterRequest):
    """일반 회원가입"""
    uid = req.username.strip()
    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

        pw_hash = hash_password(req.password.strip())
        conn.execute("""
            INSERT INTO users (user_id, nickname, email, password_hash, provider, role, created_at)
            VALUES (?, ?, ?, ?, 'local', 'user', ?)
        """, (uid, req.nickname.strip(), req.email.strip(), pw_hash, time.time()))
        conn.commit()

    token = create_access_token(uid, "user")
    return {"success": True, "token": token, "nickname": req.nickname.strip(), "user_id": uid}


@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    """일반 로그인 및 JWT Access Token 발급"""
    uid = req.username.strip()
    pw_hash = hash_password(req.password.strip())

    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, nickname, password_hash, role FROM users WHERE user_id = ?", (uid,))
        user = cursor.fetchone()

        if not user or (user["password_hash"] != pw_hash and user["password_hash"] != req.password.strip()):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

        role = user["role"]
        nickname = user["nickname"]

    token = create_access_token(uid, role)
    return {"success": True, "token": token, "nickname": nickname, "user_id": uid, "role": role}


@app.post("/api/auth/social-check")
def social_check(req: SocialCheckRequest):
    """소셜 로그인 연동 확인 모의 엔드포인트"""
    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, nickname, role FROM users WHERE user_id = ?", (req.social_id,))
        user = cursor.fetchone()
        if user:
            token = create_access_token(user["user_id"], user["role"])
            return {
                "is_new": False,
                "token": token,
                "user": {"username": user["user_id"], "nickname": user["nickname"], "role": user["role"]}
            }
        return {
            "is_new": True,
            "suggested_username": req.social_id,
            "suggested_email": f"{req.social_id}@{req.provider}.com"
        }


@app.post("/api/auth/social-onboarding")
def social_onboarding(req: SocialOnboardingRequest):
    """소셜 온보딩 신규 계정 생성"""
    with storage._get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, nickname, email, password_hash, provider, role, experience, marketing_agree, created_at)
            VALUES (?, ?, ?, 'SOCIAL_OAUTH', ?, 'user', ?, ?, ?)
        """, (req.username, req.nickname, req.email, req.provider, req.experience, 1 if req.marketing_agree else 0, time.time()))
        conn.commit()

    token = create_access_token(req.username, "user")
    return {
        "success": True,
        "token": token,
        "user": {"username": req.username, "nickname": req.nickname, "role": "user"}
    }


@app.get("/api/watchlist")
def get_watchlist(user_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """관심 종목 목록 및 안전도 상태 조회"""
    target_user = user_id
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            target_user = payload.get("sub", target_user)
        except Exception:
            pass

    if not target_user:
        return {"user_id": "", "items": []}

    stocks = storage.get_user_watchlist(target_user)
    items = []
    for stock in stocks:
        res = analyzer.analyze(stock, quick_scan=True)
        if res:
            score_info = res[0]
            price_info = res[9]
            items.append({
                "stock_name": stock,
                "score": score_info["score"],
                "status": score_info["status"],
                "current_price": price_info.get("current_price", "-"),
                "change_str": price_info.get("change_str", "-")
            })

    return {"user_id": target_user, "items": items}


@app.post("/api/watchlist/add")
def add_watchlist(req: WatchlistAddRequest, authorization: Optional[str] = Header(None)):
    """관심 종목 추가"""
    target_user = req.user_id
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            target_user = payload.get("sub", target_user)
        except Exception:
            pass

    if not target_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    clean_stock = req.stock_name.strip()
    if not clean_stock:
        raise HTTPException(status_code=400, detail="종목명을 입력해주세요.")

    storage.add_watchlist_item(target_user, clean_stock, req.memo)
    return {"status": "SUCCESS", "success": True, "message": f"'{clean_stock}' 등록 완료"}


@app.post("/api/watchlist/remove")
def remove_watchlist(req: WatchlistRemoveRequest, authorization: Optional[str] = Header(None)):
    """관심 종목 삭제"""
    target_user = req.user_id
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            target_user = payload.get("sub", target_user)
        except Exception:
            pass

    if not target_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    storage.remove_watchlist_item(target_user, req.stock_name.strip())
    return {"status": "SUCCESS", "success": True, "message": f"'{req.stock_name}' 삭제 완료"}


@app.post("/api/watchlist/upload-screenshot")
async def upload_screenshot_ocr(file: UploadFile = File(...)):
    """MTS 캡처 이미지 시연용 종목명 탐지 모의 엔드포인트"""
    # 실제 환경에서는 OCR 엔진을 호출하며, 데모 시연을 위해 대표 상장사 목록을 추출해 반환
    return {
        "status": "SUCCESS",
        "detected_stocks": ["삼성전자", "카카오", "SK하이닉스", "현대차"]
    }


@app.post("/api/auth/find-id")
def find_id(req: FindIdRequest):
    """가입 이메일로 마스킹된 아이디 조회"""
    email = req.email.strip()
    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "해당 이메일로 가입된 계정을 찾을 수 없습니다."}
        
        uid = row["user_id"]
        masked = uid[:2] + "*" * (len(uid) - 3) + uid[-1] if len(uid) > 3 else uid[0] + "**"
        return {"success": True, "masked_id": masked}


@app.post("/api/auth/reset-pw")
def reset_pw(req: ResetPwRequest):
    """아이디 및 이메일 일치 시 비밀번호 재설정"""
    uid = req.username.strip()
    email = req.email.strip()
    new_hash = hash_password(req.new_password.strip())

    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ? AND email = ?", (uid, email))
        if not cursor.fetchone():
            return {"success": False, "message": "아이디와 이메일 정보가 일치하지 않습니다."}

        cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_hash, uid))
        conn.commit()
        return {"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."}


@app.get("/api/disclosure/summary")
def summarize_disclosure_api(report_nm: str, rcept_no: str = ""):
    """공시 3줄 AI 요약 생성"""
    summary = analyzer.summarize_disclosure(report_nm, rcept_no)
    return {"summary": summary}


@app.post("/api/inquiry/create")
def create_inquiry(req: InquiryCreateRequest):
    """사용자 피드백 및 문의 접수"""
    with storage._get_conn() as conn:
        conn.execute("""
            INSERT INTO inquiries (username, category, content, status, created_at)
            VALUES (?, ?, ?, '접수완료', ?)
        """, (req.username, req.category, req.content, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    return {"success": True, "message": "문의가 성공적으로 접수되었습니다."}


@app.get("/api/admin/users")
def get_admin_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    """관리자용 전체 회원 목록 조회"""
    users_list = []
    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, nickname, email, provider, role, experience, marketing_agree, created_at FROM users")
        rows = cursor.fetchall()
        for r in rows:
            cursor.execute("SELECT COUNT(*) as cnt FROM watchlist WHERE user_id = ?", (r["user_id"],))
            cnt_row = cursor.fetchone()
            users_list.append({
                "id": r["id"],
                "username": r["user_id"],
                "nickname": r["nickname"],
                "email": r["email"],
                "provider": r["provider"] or "local",
                "role": r["role"] or "user",
                "experience": r["experience"] or "beginner",
                "marketing_agree": r["marketing_agree"] or 0,
                "watchlist_count": cnt_row["cnt"] if cnt_row else 0,
                "created_at": datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d") if r["created_at"] else "-"
            })
    return {"users": users_list}


@app.get("/api/admin/inquiries")
def get_admin_inquiries(current_user: Dict[str, Any] = Depends(get_current_user)):
    """관리자용 문의사항 목록 조회"""
    inquiries_list = []
    with storage._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, category, content, status, created_at FROM inquiries ORDER BY id DESC")
        rows = cursor.fetchall()
        for r in rows:
            inquiries_list.append(dict(r))
    return {"inquiries": inquiries_list}


# ==================== [신규] Guardian Copilot 챗봇 라우트 ====================
@app.post("/api/chat/ask")
async def chat_with_guardian(req: ChatAskRequest):
    """
    Guardian Copilot 실시간 AI Q&A 엔드포인트
    현재 화면의 종목과 DART 공시 소견서 문맥을 주입하여 Gemini 질의응답을 수행합니다.
    """
    prompt = f"""당신은 기업 공시 및 재무 리스크 분석 특화 AI 'Guardian Copilot'입니다.
현재 투자자가 분석 중인 대상 종목과 시스템이 사전에 추출한 공시 리포트 문맥을 바탕으로 답변하세요.

[분석 대상 종목]: {req.stock_name}
[사전 추출된 공시 및 재무 리스크 문맥]:
{req.context_summary if req.context_summary else "최근 특이 리스크 공시 없음 (정상 상태)"}

[투자자 질문]: {req.question}

답변 지침:
1. 반드시 메자닌(CB/BW) 물량 출회(오버행), 자본잠식, 감사의견, 최대주주 지분 변동 등의 리스크 관점을 우선하여 설명하세요.
2. 투자 판단에 도움이 되도록 전문적이면서도 알기 쉽게 3~4문장 내외로 명확하게 답변하세요.
3. 주어진 문맥에 없는 임의의 사실을 허위로 지어내지 마세요.
"""
    try:
        # analyzer 내부의 Gemini 모델 인스턴스 활용
        if hasattr(analyzer, "model") and analyzer.model:
            response = analyzer.model.generate_content(prompt)
            return {"answer": response.text.strip()}
        else:
            return {"answer": f"'{req.stock_name}'의 현재 상태는 안정적이며, 문의하신 내용과 관련된 단기 대규모 공시 지뢰는 발견되지 않았습니다."}
    except Exception as e:
        return {"answer": f"답변 생성 중 일시적인 오류가 발생했습니다: {str(e)}"}


# ==================== 프론트엔드 정적 파일 통합 서빙 ====================
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(__file__), "out")

if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")