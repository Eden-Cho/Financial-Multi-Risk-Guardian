"""
==============================================================================
[Module Overview]
- 파일명: backend/app.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할:
    1. FastAPI 메인 웹 서버 및 REST API 엔드포인트 라우팅
    2. [2순위 고도화] APScheduler 기반 백그라운드 데몬 가동
       (15분 주기 관심종목 고유 합집합 DART 신규 공시 자동 폴링)
    3. [3순위 고도화] JWT (JSON Web Token) 및 비밀번호 해싱 기반 인증 인가 체계
       (BOLA 취약점 차단 및 세션 보안 보장)
    4. 종목 정밀 진단, 관심 종목 관리, DART 3줄 요약, OCR 스크린샷 일괄 등록 지원
==============================================================================
"""

import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import jwt

from backend.modules.analyzer import RiskAnalyzer
from backend.modules.storage import StorageManager

# ==================== 보안 환경 변수 ====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "guardian-risk-secret-key-production-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일 유효

app = FastAPI(title="Financial Multi-Risk Guardian API", version="2.5.0")

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
    """
    [함수 역할 - 3순위 보안 핵심]
    Request Header의 'Authorization: Bearer <Token>'을 파싱하여
    변조되지 않은 유효한 로그인 사용자인지 검증합니다.
    """
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


# ==================== 2순위: 백그라운드 폴링 데몬 ====================
def background_watchlist_risk_monitor():
    """
    [함수 역할 - 2순위 핵심]
    15분마다 전체 유저의 고유 관심 종목 목록을 조회하여,
    신규 접수된 DART 공시가 있는지 백그라운드 점검하고 캐시를 최신 상태로 유지합니다.
    """
    try:
        unique_stocks = storage.get_all_unique_watchlist_stocks()
        if not unique_stocks:
            return

        print(f"[백그라운드 데몬] 관심 종목 {len(unique_stocks)}개 DART 신규 공시 스캔 시작...")
        for stock in unique_stocks:
            try:
                # quick_scan=False로 최신 공시 번호 검증 및 악재 발생 시 자동 갱신
                analyzer.analyze(stock, quick_scan=False)
                time.sleep(1.0)  # DART API 부하 방지용 안전 딜레이
            except Exception as e:
                print(f"[백그라운드 데몬 오류] '{stock}': {e}")
        print("[백그라운드 데몬] 관심 종목 배치 점검 완료.")
    except Exception as e:
        print(f"[백그라운드 데몬 치명적 에러]: {e}")

# APScheduler 기동
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

class WatchlistAddRequest(BaseModel):
    stock_name: str
    memo: Optional[str] = ""

class WatchlistRemoveRequest(BaseModel):
    stock_name: str

class FindIdRequest(BaseModel):
    email: str

class ResetPwRequest(BaseModel):
    username: str
    email: str
    new_password: str


# ==================== API 라우트 ====================

@app.get("/api/analyze/{stock_name}")
def analyze_stock(stock_name: str):
    """단일 종목 다차원 정밀 진단 (비로그인 사용자도 공개 조회 가능)"""
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
    """일반 회원가입 (비밀번호 해시 저장)"""
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

        # 기존 테스트 계정 호환 및 해시 검증
        if not user or (user["password_hash"] != pw_hash and user["password_hash"] != req.password.strip()):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

        role = user["role"]
        nickname = user["nickname"]

    token = create_access_token(uid, role)
    return {"success": True, "token": token, "nickname": nickname, "user_id": uid, "role": role}


@app.get("/api/watchlist")
def get_watchlist(current_user: Dict[str, Any] = Depends(get_current_user)):
    """[보안 적용] JWT 검증된 본인의 관심 종목 및 실시간 가격/안전도 조회"""
    user_id = current_user["user_id"]
    stocks = storage.get_user_watchlist(user_id)
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

    return {"user_id": user_id, "items": items}


@app.post("/api/watchlist/add")
def add_watchlist(req: WatchlistAddRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """[보안 적용] 로그인된 본인 계정에 관심 종목 추가"""
    user_id = current_user["user_id"]
    clean_stock = req.stock_name.strip()
    if not clean_stock:
        raise HTTPException(status_code=400, detail="종목명을 입력해주세요.")

    storage.add_watchlist_item(user_id, clean_stock, req.memo)
    return {"success": True, "message": f"'{clean_stock}' 등록 완료"}


@app.post("/api/watchlist/remove")
def remove_watchlist(req: WatchlistRemoveRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """[보안 적용] 본인 계정의 관심 종목 삭제"""
    user_id = current_user["user_id"]
    storage.remove_watchlist_item(user_id, req.stock_name.strip())
    return {"success": True, "message": f"'{req.stock_name}' 삭제 완료"}


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