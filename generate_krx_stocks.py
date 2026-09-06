import os
import json
import urllib.request
import pandas as pd

def generate_stock_master():
    print("[1/3] KRX 상장법인 목록 다운로드 시작...")
    
    url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
    
    # 봇 차단 방지용 User-Agent 헤더 추가
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            df = pd.read_html(html, header=0)[0]
    except Exception as e:
        print(f"[오류] KRX 데이터 다운로드 실패: {e}")
        return

    print(f"[2/3] 데이터 파싱 중... (가져온 데이터 수: {len(df)})")
    
    # 종목코드를 6자리 문자열(예: '005930')로 변환
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    stock_dict = dict(zip(df["회사명"], df["종목코드"]))

    # 저장 경로 계산: 현재 스크립트 위치 기준 backend/data/krx_stocks.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.basename(base_dir) == "backend":
        save_dir = os.path.join(base_dir, "data")
    else:
        save_dir = os.path.join(base_dir, "backend", "data")
        
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "krx_stocks.json")

    print(f"[3/3] JSON 파일 저장 중 -> {save_path}")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(stock_dict, f, ensure_ascii=False, indent=2)

    print("=" * 50)
    print(f"성공! 총 {len(stock_dict)}개 상장 종목 저장 완료: {save_path}")
    print("=" * 50)

if __name__ == "__main__":
    generate_stock_master()