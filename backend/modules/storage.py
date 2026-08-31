import sqlite3
import json
import time
from typing import Optional, Tuple, Dict, Any, List

DB_PATH = "risk_guardian.db"

class StorageManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            # 1. 재무 데이터 테이블 (공유 저장소)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_cache (
                stock_name TEXT PRIMARY KEY,
                financial_data TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """)
            # 2. 종목별 AI 소견서 및 리스크 스냅샷 (공유 저장소)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS report_cache (
                stock_name TEXT PRIMARY KEY,
                last_rcept_no TEXT,
                score_info TEXT NOT NULL,
                radar_data TEXT NOT NULL,
                report_text TEXT NOT NULL,
                forecast_scenario TEXT NOT NULL,
                cb_dilution TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """)
            # 3. 사용자별 관심 종목 매핑 테이블
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                user_id TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (user_id, stock_name)
            )
            """)
            conn.commit()

    # --- 사용자 관심 종목 관리 ---
    def add_watchlist_item(self, user_id: str, stock_name: str):
        """특정 사용자의 관심 종목 등록"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_watchlist (user_id, stock_name, created_at) VALUES (?, ?, ?)",
                (user_id.strip(), stock_name.strip(), time.time())
            )
            conn.commit()

    def remove_watchlist_item(self, user_id: str, stock_name: str):
        """특정 사용자의 관심 종목 해제"""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM user_watchlist WHERE user_id = ? AND stock_name = ?",
                (user_id.strip(), stock_name.strip())
            )
            conn.commit()

    def get_user_watchlist(self, user_id: str) -> List[str]:
        """특정 사용자의 관심 종목 목록 조회"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stock_name FROM user_watchlist WHERE user_id = ? ORDER BY created_at DESC",
                (user_id.strip(),)
            )
            rows = cursor.fetchall()
            return [row["stock_name"] for row in rows]

    def get_all_unique_watchlist_stocks(self) -> List[str]:
        """모든 사용자가 등록한 관심 종목의 고유 합집합(Deduplication) 추출"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT stock_name FROM user_watchlist")
            rows = cursor.fetchall()
            return [row["stock_name"] for row in rows]

    # --- 공유 재무/분석 데이터 관리 ---
    def get_financial_data(self, stock_name: str, max_age_seconds: float = 86400 * 7) -> Optional[dict]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT financial_data, updated_at FROM financial_cache WHERE stock_name = ?", (stock_name,))
            row = cursor.fetchone()
            if row and (time.time() - row["updated_at"] < max_age_seconds):
                return json.loads(row["financial_data"])
        return None

    def save_financial_data(self, stock_name: str, data: list):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO financial_cache (stock_name, financial_data, updated_at) VALUES (?, ?, ?)",
                (stock_name, json.dumps(data, ensure_ascii=False), time.time())
            )
            conn.commit()

    def get_cached_report(self, stock_name: str, max_age_seconds: float = 3600 * 6) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_rcept_no, score_info, radar_data, report_text, forecast_scenario, cb_dilution, updated_at 
                FROM report_cache WHERE stock_name = ?
            """, (stock_name,))
            row = cursor.fetchone()
            if row and (time.time() - row["updated_at"] < max_age_seconds):
                return {
                    "last_rcept_no": row["last_rcept_no"],
                    "score_info": json.loads(row["score_info"]),
                    "radar_data": json.loads(row["radar_data"]),
                    "report_text": row["report_text"],
                    "forecast_scenario": json.loads(row["forecast_scenario"]),
                    "cb_dilution": json.loads(row["cb_dilution"]),
                    "updated_at": row["updated_at"]
                }
        return None

    def save_report(self, stock_name: str, last_rcept_no: str, score_info: dict, radar_df_records: list, report_text: str, forecast_scenario: dict, cb_dilution: dict):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO report_cache 
                (stock_name, last_rcept_no, score_info, radar_data, report_text, forecast_scenario, cb_dilution, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stock_name,
                last_rcept_no,
                json.dumps(score_info, ensure_ascii=False),
                json.dumps(radar_df_records, ensure_ascii=False),
                report_text,
                json.dumps(forecast_scenario, ensure_ascii=False),
                json.dumps(cb_dilution, ensure_ascii=False),
                time.time()
            ))
            conn.commit()