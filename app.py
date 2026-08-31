import os
import time
import threading
from typing import List, Optional
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from backend.modules.analyzer import RiskAnalyzer
from backend.modules.batch_sync import BatchSyncManager
from backend.modules.storage import StorageManager

analyzer = RiskAnalyzer()
batch_manager = BatchSyncManager()
storage = StorageManager()

# 422 에러 방지: 프론트엔드의 카멜케이스(userId, stockName) 및 다양한 필드명을 모두 허용
class WatchlistRequest(BaseModel):
    user_id: Optional[str] = Field(default="default_user", alias="userId")
    stock_name: Optional[str] = Field(default=None, alias="stockName")
    company: Optional[str] = None
    name: Optional[str] = None

    class Config:
        populate_by_name = True

    def get_clean_data(self) -> tuple[str, str]:
        uid = (self.user_id or "default_user").strip()
        target_stock = self.stock_name or self.company or self.name or ""
        return uid, target_stock.strip()

def background_startup_task():
    time.sleep(2.0)
    batch_manager.sync_financials_for_targets()

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=background_startup_task, daemon=True).start()
    yield

app = FastAPI(title="Financial Risk Guardian API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _process_analysis(target_company: str, quick: bool = False):
    res = analyzer.analyze(target_company, quick_scan=quick)
    if not res:
        return {"error": f"'{target_company}'은(는) 유효하지 않거나 DART에서 찾을 수 없는 기업명입니다."}
    
    score_info, radar_df, report_text, overhang_schedule, raw_disclosures, financial_health, cb_dilution, forecast_scenario, sentiment_data, price_info = res
    
    if quick:
        return {
            "score_info": score_info,
            "radar_data": radar_df.to_dict(orient="records"),
            "report_text": report_text,
            "financial_health": financial_health,
            "cb_dilution": cb_dilution,
            "price_info": price_info
        }
        
    return {
        "score_info": score_info,
        "radar_data": radar_df.to_dict(orient="records"),
        "report_text": report_text,
        "overhang_schedule": overhang_schedule,
        "raw_disclosures": raw_disclosures,
        "financial_health": financial_health,
        "cb_dilution": cb_dilution,
        "forecast_scenario": forecast_scenario,
        "sentiment_data": sentiment_data,
        "price_info": price_info
    }

# 1. 심층 분석: Query String 및 Path Parameter 둘 다 지원
@app.get("/api/analyze")
def analyze_stock_query(company: str = Query(..., description="분석할 회사명")):
    return _process_analysis(company, quick=False)

@app.get("/api/analyze/{company}")
def analyze_stock_path(company: str):
    return _process_analysis(company, quick=False)

# 2. 경량 분석: Query String 및 Path Parameter 둘 다 지원
@app.get("/api/quick_scan")
def quick_scan_query(company: str = Query(..., description="경량 분석할 회사명")):
    return _process_analysis(company, quick=True)

@app.get("/api/quick_scan/{company}")
def quick_scan_path(company: str):
    return _process_analysis(company, quick=True)

# 3. 사용자별 관심 종목 등록 (422 방지 처리 완료)
@app.post("/api/watchlist/add")
def add_watchlist(req: WatchlistRequest, background_tasks: BackgroundTasks):
    user_id, stock_name = req.get_clean_data()
    if not stock_name:
        return {"status": "ERROR", "message": "종목명이 누락되었습니다."}
        
    storage.add_watchlist_item(user_id, stock_name)
    background_tasks.add_task(batch_manager.sync_financials_for_targets, [stock_name])
    return {"status": "SUCCESS", "message": f"'{stock_name}' 관심 종목 등록 완료"}

# 4. 사용자별 관심 종목 해제 (422 방지 처리 완료)
@app.post("/api/watchlist/remove")
def remove_watchlist(req: WatchlistRequest):
    user_id, stock_name = req.get_clean_data()
    if not stock_name:
        return {"status": "ERROR", "message": "종목명이 누락되었습니다."}
        
    storage.remove_watchlist_item(user_id, stock_name)
    return {"status": "SUCCESS", "message": f"'{stock_name}' 관심 종목 삭제 완료"}

# 5. 사용자별 관심 종목 목록 및 일괄 안전도 상태 조회
@app.get("/api/watchlist")
def get_watchlist(user_id: str = Query(default="default_user", description="사용자 ID")):
    stocks = storage.get_user_watchlist(user_id)
    results = []
    for stock in stocks:
        res = analyzer.analyze(stock, quick_scan=True)
        if res:
            score_info, _, _, _, _, _, _, _, _, price_info = res
            results.append({
                "stock_name": stock,
                "score": score_info["score"],
                "status": score_info["status"],
                "current_price": price_info.get("current_price", "-"),
                "change_str": price_info.get("change_str", "-")
            })
    return {"user_id": user_id, "items": results}

# 6. DART 공시 3줄 요약
@app.get("/api/disclosure/summary")
def get_disclosure_summary(report_nm: str = Query(...), rcept_no: str = Query("")):
    return analyzer.summarize_disclosure(report_nm, rcept_no)

# 7. 수동 배치 동기화 트리거
@app.post("/api/admin/sync_financials")
def trigger_financial_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(batch_manager.sync_financials_for_targets)
    return {"status": "SUCCESS", "message": "동기화 작업이 백그라운드에서 시작되었습니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)