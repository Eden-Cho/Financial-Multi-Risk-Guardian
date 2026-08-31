import os
import sys
import sqlite3
import hashlib
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "guardian.db")


class DBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._seed_default_accounts()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 유저 테이블 (email, marketing_agree 컬럼 포함)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                nickname TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                provider TEXT DEFAULT 'local',
                experience TEXT DEFAULT 'beginner',
                marketing_agree INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 기존 DB 테이블 컬럼 마이그레이션(누락 방지)
            cursor.execute("PRAGMA table_info(users)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "email" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
            if "marketing_agree" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN marketing_agree INTEGER DEFAULT 0")

            # 2. 포트폴리오(관심종목) 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                stock_name TEXT NOT NULL,
                avg_price REAL DEFAULT 0,
                quantity INTEGER DEFAULT 0,
                memo TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
                UNIQUE(username, stock_name)
            )
            """)

            # 3. 문의사항 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                category TEXT DEFAULT '일반문의',
                content TEXT NOT NULL,
                status TEXT DEFAULT '접수완료',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def _seed_default_accounts(self):
        """마스터, 관리자 및 일반 테스트 유저 기본 계정 자동 생성"""
        accounts = [
            ("master", "총괄마스터", "master@guardian.ai", "master1234", "master", "local", "advanced", 1),
            ("admin", "운영관리자", "admin@guardian.ai", "admin1234", "admin", "local", "advanced", 1),
            ("tester1", "성투하는라이언", "tester1@kakao.com", "tester1234", "user", "local", "beginner", 1),
            ("tester2", "주식꿈나무", "tester2@naver.com", "tester1234", "user", "local", "intermediate", 0)
        ]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for username, nickname, email, password, role, provider, exp, m_agree in accounts:
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if not cursor.fetchone():
                    cursor.execute(
                        """INSERT INTO users 
                        (username, nickname, email, password_hash, role, provider, experience, marketing_agree) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (username, nickname, email, self._hash_password(password), role, provider, exp, m_agree)
                    )
            
            # tester1 기본 관심종목 시딩
            sample_watchlist = [
                ("tester1", "모아데이타", "유튜브 급등주 추천"),
                ("tester1", "카카오", "바닥권 매수 검토"),
                ("tester2", "삼성전자", "장기 투자 배당주")
            ]
            for u, s, m in sample_watchlist:
                cursor.execute("""
                INSERT OR IGNORE INTO portfolios (username, stock_name, memo)
                VALUES (?, ?, ?)
                """, (u, s, m))

            # 샘플 문의사항 시딩
            cursor.execute("SELECT count(*) as cnt FROM inquiries")
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute("""
                INSERT INTO inquiries (username, category, content, status)
                VALUES ('tester1', '개선 제안', '전환사채(CB) 리픽싱 일정도 달력으로 볼 수 있으면 좋겠습니다.', '접수완료')
                """)

            conn.commit()

    # ==================== 사용자 인증 (Auth) ====================

    def register_user(self, username: str, nickname: str, email: str, password: str, role: str = "user", provider: str = "local", experience: str = "beginner", marketing_agree: bool = False) -> tuple[bool, str]:
        username = username.strip()
        nickname = nickname.strip() if nickname else username
        email = email.strip()
        password = password.strip()
        if not username or not password or not email:
            return False, "아이디, 이메일, 비밀번호를 모두 입력해 주세요."

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO users 
                    (username, nickname, email, password_hash, role, provider, experience, marketing_agree) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (username, nickname, email, self._hash_password(password), role, provider, experience, 1 if marketing_agree else 0)
                )
                conn.commit()
                return True, f"'{nickname}'({username}) 님 가입이 완료되었습니다."
        except sqlite3.IntegrityError:
            return False, "이미 존재하는 사용자 아이디입니다."
        except Exception as e:
            return False, f"회원가입 실패: {e}"

    def verify_user(self, username: str, password: str) -> dict | None:
        """로그인 검증"""
        username = username.strip()
        pw_hash = self._hash_password(password.strip())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, nickname, email, role, provider, experience, marketing_agree, created_at FROM users WHERE username = ? AND password_hash = ?",
                (username, pw_hash)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def social_login_or_check(self, social_id: str, provider: str) -> dict:
        formatted_username = f"{provider}_{social_id}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, nickname, email, role, provider, experience, marketing_agree, created_at FROM users WHERE username = ?",
                (formatted_username,)
            )
            row = cursor.fetchone()
            if row:
                return {"is_new": False, "user": dict(row)}
            else:
                suggested_email = f"{social_id}@{provider}.com"
                return {"is_new": True, "suggested_username": formatted_username, "suggested_email": suggested_email}

    def complete_social_onboarding(self, username: str, nickname: str, email: str, provider: str, experience: str, marketing_agree: bool = False) -> tuple[bool, dict | str]:
        """소셜 최초 가입 시 이메일, 닉네임, 동의 정보 저장"""
        try:
            nickname = nickname.strip() if nickname else f"투자자_{username[-4:]}"
            email = email.strip()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                dummy_pw = self._hash_password(f"social_{username}_{datetime.now()}")
                cursor.execute(
                    """INSERT INTO users 
                    (username, nickname, email, password_hash, role, provider, experience, marketing_agree) 
                    VALUES (?, ?, ?, ?, 'user', ?, ?, ?)""",
                    (username, nickname, email, dummy_pw, provider, experience, 1 if marketing_agree else 0)
                )
                conn.commit()
                return True, {
                    "username": username, 
                    "nickname": nickname, 
                    "email": email, 
                    "role": "user", 
                    "experience": experience, 
                    "provider": provider
                }
        except sqlite3.IntegrityError:
            return False, "이미 등록된 소셜 계정입니다."
        except Exception as e:
            return False, f"온보딩 실패: {e}"

    # ==================== 포트폴리오 관리 ====================

    def add_portfolio_item(self, username: str, stock_name: str, memo: str = "") -> tuple[bool, str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO portfolios (username, stock_name, memo)
                VALUES (?, ?, ?)
                ON CONFLICT(username, stock_name) DO UPDATE SET memo = excluded.memo
                """, (username.strip(), stock_name.strip(), memo))
                conn.commit()
                return True, f"'{stock_name}' 종목이 등록되었습니다."
        except Exception as e:
            return False, f"종목 등록 실패: {e}"
        
    def add_portfolio_bulk(self, username: str, items: list[dict]) -> tuple[int, list[str]]:
        """여러 종목 일괄 등록"""
        conn = self.get_connection()
        cursor = conn.cursor()
        success_count = 0
        failed_stocks = []

        for item in items:
            s_name = item.get("stock_name", "").strip()
            s_memo = item.get("memo", "대량 일괄 등록").strip()
            if not s_name:
                continue
            try:
                cursor.execute(
                    "INSERT INTO portfolios (username, stock_name, memo) VALUES (?, ?, ?)",
                    (username, s_name, s_memo)
                )
                success_count += 1
            except Exception:
                failed_stocks.append(s_name)

        conn.commit()
        conn.close()
        return success_count, failed_stocks

    def get_user_portfolio(self, username: str) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM portfolios WHERE username = ? ORDER BY created_at DESC", (username.strip(),))
            return [dict(row) for row in cursor.fetchall()]

    def remove_portfolio_item(self, username: str, stock_name: str) -> tuple[bool, str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM portfolios WHERE username = ? AND stock_name = ?", (username.strip(), stock_name.strip()))
                conn.commit()
                return True, f"'{stock_name}' 종목이 삭제되었습니다."
        except Exception as e:
            return False, f"종목 삭제 실패: {e}"

    # ==================== 관리자 전용 API ====================

    def get_all_users_for_admin(self) -> list[dict]:
        """전체 회원 목록 (이메일 및 마케팅 수신동의 여부 포함)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT u.id, u.username, u.nickname, u.email, u.role, u.provider, u.experience, u.marketing_agree, u.created_at, COUNT(p.id) as watchlist_count
            FROM users u
            LEFT JOIN portfolios p ON u.username = p.username
            GROUP BY u.id
            ORDER BY u.id ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def create_inquiry(self, username: str, category: str, content: str) -> tuple[bool, str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO inquiries (username, category, content) VALUES (?, ?, ?)",
                    (username.strip(), category, content.strip())
                )
                conn.commit()
                return True, "문의가 접수되었습니다."
        except Exception as e:
            return False, f"문의 접수 실패: {e}"

    def get_all_inquiries(self) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inquiries ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]