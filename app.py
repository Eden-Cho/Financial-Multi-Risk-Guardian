import os
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.modules.analyzer import RiskAnalyzer
from backend.modules.db_manager import DBManager

app = FastAPI(
    title="Financial Multi-Risk Guardian API",
    description="주린이를 위한 주식 다차원 지뢰 진단 백엔드 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

risk_analyzer = RiskAnalyzer()
db_manager = DBManager()

# --- Pydantic 요청 스키마 ---
class RegisterRequest(BaseModel):
    username: str
    nickname: str
    email: str
    password: str
    experience: Optional[str] = "beginner"
    marketing_agree: Optional[bool] = False

class LoginRequest(BaseModel):
    username: str
    password: str

class SocialAuthRequest(BaseModel):
    social_id: str
    provider: str

class SocialOnboardingRequest(BaseModel):
    username: str
    nickname: str
    email: str
    provider: str
    experience: str
    marketing_agree: Optional[bool] = False

class WatchlistAddRequest(BaseModel):
    username: str
    stock_name: str
    memo: Optional[str] = "관심 종목"

class WatchlistDeleteRequest(BaseModel):
    username: str
    stock_name: str

class InquiryRequest(BaseModel):
    username: str
    category: str
    content: str

# --- 1. 상태 체크 ---
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Financial Multi-Risk Guardian API"}

# --- 2. 인증 & 소셜 온보딩 엔드포인트 ---
@app.post("/api/auth/register")
def register(req: RegisterRequest):
    ok, msg = db_manager.register_user(
        username=req.username,
        nickname=req.nickname,
        email=req.email,
        password=req.password,
        role="user",
        provider="local",
        experience=req.experience,
        marketing_agree=req.marketing_agree
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = db_manager.verify_user(req.username, req.password)
    if user:
        return {
            "success": True, 
            "username": user["username"], 
            "nickname": user["nickname"],
            "email": user["email"],
            "role": user["role"],
            "experience": user["experience"],
            "message": "로그인 성공"
        }
    raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

@app.post("/api/auth/social-check")
def social_auth_check(req: SocialAuthRequest):
    result = db_manager.social_login_or_check(req.social_id, req.provider)
    return result

@app.post("/api/auth/social-onboarding")
def social_onboarding_complete(req: SocialOnboardingRequest):
    ok, result = db_manager.complete_social_onboarding(
        username=req.username,
        nickname=req.nickname,
        email=req.email,
        provider=req.provider,
        experience=req.experience,
        marketing_agree=req.marketing_agree
    )
    if not ok:
        raise HTTPException(status_code=400, detail=str(result))
    return {"success": True, "user": result}

# --- 3. 종목 정밀 진단 ---
@app.get("/api/analyze/{stock_name}")
def analyze_stock(stock_name: str):
    score_info, radar_df, report_text = risk_analyzer.analyze(stock_name)
    radar_data = radar_df.to_dict(orient="records")
    return {
        "stock_name": stock_name,
        "score_info": score_info,
        "radar_data": radar_data,
        "report_text": report_text
    }

# --- 4. 관심 종목 ---
@app.get("/api/watchlist/{username}")
def get_watchlist(username: str):
    items = db_manager.get_user_portfolio(username)
    return {"watchlist": items}

@app.post("/api/watchlist/add")
def add_watchlist(req: WatchlistAddRequest):
    ok, msg = db_manager.add_portfolio_item(req.username, req.stock_name, memo=req.memo)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.delete("/api/watchlist/delete")
def delete_watchlist(req: WatchlistDeleteRequest):
    ok, msg = db_manager.remove_portfolio_item(req.username, req.stock_name)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

# --- 5. 관리자 & 문의사항 엔드포인트 ---
@app.post("/api/inquiry/create")
def create_inquiry(req: InquiryRequest):
    ok, msg = db_manager.create_inquiry(req.username, req.category, req.content)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/admin/users")
def get_admin_users():
    users = db_manager.get_all_users_for_admin()
    return {"users": users}

@app.get("/api/admin/inquiries")
def get_admin_inquiries():
    inquiries = db_manager.get_all_inquiries()
    return {"inquiries": inquiries}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)