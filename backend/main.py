"""
==============================================================================
[Module Overview]
- 파일명: backend/main.py
- 프로젝트: Financial Multi-Risk Guardian
- 주요 역할: FastAPI 백엔드 메인 앱 서버 및 API 라우터 정의
==============================================================================
"""

import os
import time
import hashlib
import sqlite3
from typing import Optional, List
from google.genai import types

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from backend.modules.analyzer import RiskAnalyzer
from backend.modules.dart_collector import DartCollector
from backend.modules.ocr_extractor import StockOcrExtractor

app = FastAPI(
    title="Financial Multi-Risk Guardian API",
    version="2.0.0",
    description="DART 공시, KR-FinBERT 감성 분석, Gemini LLM 소견서 및 스마트 캐시 기반 다차원 리스크 관제 시스템"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = RiskAnalyzer()
dart_collector = DartCollector()
ocr_extractor = StockOcrExtractor()

# 간단한 비밀번호 해시 유틸리티
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# --- Pydantic 모델 정의 ---
class LoginRequest(BaseModel):
    username: str
    password: str

class SocialCheckRequest(BaseModel):
    social_id: str
    provider: str

class SocialOnboardingRequest(BaseModel):
    username: str
    nickname: str
    email: str
    provider: str
    experience: str
    marketing_agree: int

class FindIdRequest(BaseModel):
    email: EmailStr

class ResetPwRequest(BaseModel):
    username: str
    email: EmailStr
    new_password: str

class WatchlistAddRequest(BaseModel):
    user_id: str
    stock_name: str

class WatchlistRemoveRequest(BaseModel):
    user_id: str
    stock_name: str

class PortfolioDiagnosisRequest(BaseModel):
    stock_names: List[str]

class InquiryRequest(BaseModel):
    username: str
    category: str
    content: str

class ChatRequest(BaseModel):
    stock_name: str
    question: str
    context_summary: Optional[str] = ""


# --- API 엔드포인트 ---

@app.get("/api/analyze/{stock_name}")
def api_analyze_stock(stock_name: str):
    """
    개별 종목 다차원 정밀 진단 API
    """
    try:
        result = analyzer.analyze(stock_name, quick_scan=False)
        if not result:
            raise HTTPException(status_code=404, detail=f"'{stock_name}' 기업 정보를 DART에서 찾을 수 없습니다.")
        
        score_info, radar_df, report_text, overhang_schedule, raw_disclosures_top, financial_health, cb_dilution, forecast_scenario, sentiment_data, price_info = result
        
        return {
            "stock_name": stock_name,
            "score_info": score_info,
            "radar_data": radar_df.to_dict(orient="records"),
            "report_text": report_text,
            "overhang_schedule": overhang_schedule,
            "raw_disclosures": raw_disclosures_top,
            "financial_health": financial_health,
            "cb_dilution": cb_dilution,
            "forecast_scenario": forecast_scenario,
            "sentiment_data": sentiment_data,
            "price_info": price_info
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[분석 API 오류]: {e}")
        raise HTTPException(status_code=500, detail=f"분석 중 서버 오류가 발생했습니다: {str(e)}")


@app.post("/api/portfolio/diagnose")
def api_diagnose_portfolio(req: PortfolioDiagnosisRequest):
    """
    종목 목록을 전달받아 포트폴리오 종합 건강진단(요약 점수, 9각 레이더, 종목별 카드, 경보) 생성
    """
    try:
        diagnosis_result = analyzer.analyze_portfolio_summary(req.stock_names)
        return diagnosis_result
    except Exception as e:
        print(f"[포트폴리오 진단 API 오류]: {e}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 진단 실패: {str(e)}")


@app.get("/api/disclosure/summary")
def api_disclosure_summary(report_nm: str, rcept_no: str = ""):
    """
    DART 특정 공시 원문 AI 3줄 요약 API
    """
    try:
        summary_result = analyzer.summarize_disclosure(report_nm, rcept_no)
        return {"success": True, "summary": summary_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist")
def api_get_watchlist(user_id: str):
    """
    사용자 관심 종목(포트폴리오) 목록 및 간이 안전 점수 조회 API
    """
    try:
        items = analyzer.storage.get_watchlist_items(user_id)
        formatted_items = []
        for name in items:
            cached = analyzer.storage.get_cached_report(name, max_age_seconds=86400 * 3)
            score = cached["score_info"]["score"] if cached else 80
            status = cached["score_info"]["status"] if cached else "안전 (Low Risk)"
            
            formatted_items.append({
                "stock_name": name,
                "score": score,
                "status": status,
                "current_price": "실시간 연동",
                "change_str": "+0.0%"
            })
        return {"success": True, "items": formatted_items}
    except Exception as e:
        return {"success": True, "items": []}


@app.post("/api/watchlist/add")
def api_add_watchlist(req: WatchlistAddRequest):
    """
    관심 종목 추가 API
    """
    try:
        success = analyzer.storage.add_watchlist(req.user_id, req.stock_name)
        if success:
            return {"status": "SUCCESS", "message": "등록되었습니다."}
        return {"status": "FAIL", "message": "이미 등록되어 있거나 처리 실패"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist/remove")
def api_remove_watchlist(req: WatchlistRemoveRequest):
    """
    관심 종목 삭제 API
    """
    try:
        analyzer.storage.remove_watchlist(req.user_id, req.stock_name)
        return {"success": True, "message": "삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist/upload-screenshot")
async def api_upload_screenshot(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    """
    MTS 잔고 스크린샷 OCR 인식 및 종목 추출
    추출된 종목 리스트와 함께 포트폴리오 즉시 진단 데이터 반환
    """
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="업로드된 이미지 파일이 비어 있습니다.")

        # OCR 파싱: [{'name': '삼성전자', 'code': '005930'}, ...]
        detected_items = ocr_extractor.extract_stocks_from_image(image_bytes)
        stock_names = [item["name"] for item in detected_items]

        # 사용자 ID가 있으면 관심종목에 일괄 추가
        if user_id and stock_names:
            for stock_name in stock_names:
                analyzer.storage.add_watchlist(user_id, stock_name)

        # 추출된 종목군 기반 즉각 종합 진단 실행
        diagnosis = analyzer.analyze_portfolio_summary(stock_names) if stock_names else None

        return {
            "success": True,
            "detected_stocks": stock_names,
            "detected_details": detected_items,
            "saved_to_watchlist": bool(user_id),
            "diagnosis": diagnosis
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[OCR 스크린샷 처리 오류]: {e}")
        raise HTTPException(status_code=500, detail=f"OCR 처리 중 오류가 발생했습니다: {str(e)}")


@app.post("/api/auth/login")
def api_login(req: LoginRequest):
    user = analyzer.storage.get_user(req.username)
    if not user or user["password_hash"] != hash_password(req.password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    
    return {
        "success": True,
        "token": f"mock_jwt_token_{req.username}",
        "nickname": user["nickname"],
        "role": user["role"]
    }


@app.post("/api/auth/social-check")
def api_social_check(req: SocialCheckRequest):
    user = analyzer.storage.get_user_by_social(req.social_id, req.provider)
    if not user:
        return {
            "is_new": True,
            "suggested_username": f"{req.provider}_{int(time.time())}",
            "suggested_email": f"{req.provider}_user@guardian.ai"
        }
    return {
        "is_new": False,
        "token": f"mock_jwt_token_{user['username']}",
        "user": user
    }


@app.post("/api/auth/social-onboarding")
def api_social_onboarding(req: SocialOnboardingRequest):
    success = analyzer.storage.create_social_user(req.dict())
    if not success:
        raise HTTPException(status_code=400, detail="회원 가입 처리에 실패했습니다.")
    
    return {
        "success": True,
        "token": f"mock_jwt_token_{req.username}",
        "user": req.dict()
    }


@app.post("/api/auth/find-id")
def api_find_id(req: FindIdRequest):
    username = analyzer.storage.find_username_by_email(req.email)
    if not username:
        return {"success": False, "message": "해당 이메일로 가입된 계정이 없습니다."}
    
    masked = username[:2] + "****" if len(username) > 2 else "****"
    return {"success": True, "masked_id": masked}


@app.post("/api/auth/reset-pw")
def api_reset_pw(req: ResetPwRequest):
    success = analyzer.storage.reset_password(req.username, req.email, hash_password(req.new_password))
    if not success:
        return {"success": False, "message": "아이디와 이메일 정보가 일치하지 않습니다."}
    return {"success": True, "message": "비밀번호가 성공적으로 재설정되었습니다."}


@app.post("/api/inquiry/create")
def api_create_inquiry(req: InquiryRequest):
    try:
        analyzer.storage.save_inquiry(req.username, req.category, req.content)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/users")
def api_admin_users():
    try:
        users = analyzer.storage.get_all_users()
        return {"success": True, "users": users}
    except Exception as e:
        return {"success": True, "users": []}


@app.get("/api/admin/inquiries")
def api_admin_inquiries():
    try:
        inquiries = analyzer.storage.get_all_inquiries()
        return {"success": True, "inquiries": inquiries}
    except Exception as e:
        return {"success": True, "inquiries": []}


@app.post("/api/chat/ask")
def api_chat_ask(req: ChatRequest):
    try:
        if analyzer.ai_client:
            prompt = f"""
당신은 'Financial Multi-Risk Guardian'의 AI 금융 어시스턴트(Copilot)입니다.
사용자가 현재 진단 중인 종목 [{req.stock_name}]과 관련된 질문을 하였습니다.
원천 컨텍스트 요약: {req.context_summary}

사용자 질문: {req.question}

규정: 금융 규정 및 공시 수치에 기반하여 초보 투자자가 이해하기 쉽게 친절하면서도 전문적으로 3~4문장 내외로 답변하세요.
"""
            config = types.GenerateContentConfig(temperature=0.3, max_output_tokens=600)
            res = analyzer.ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=config
            )
            answer = (res.text or "").strip()
            return {"success": True, "answer": answer}
        else:
            return {"success": True, "answer": "AI 클라이언트가 설정되지 않았습니다. API Key를 확인하세요."}
    except Exception as e:
        return {"success": True, "answer": f"답변 생성 중 오류가 발생했습니다: {str(e)}"}