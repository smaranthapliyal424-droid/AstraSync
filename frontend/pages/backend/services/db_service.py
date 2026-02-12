import sqlite3, json, os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "../data/astrasync.db"))


def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db(conn):
    from backend.services.db_service import init_tokens_table
    init_tokens_table(conn)
    with conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles(
      user_id TEXT PRIMARY KEY,
      payload TEXT NOT NULL
    )
    """)
    conn.commit()

def save_profile(conn, user_id: str, profile: dict):
    conn.execute("INSERT OR REPLACE INTO profiles (user_id, payload) VALUES (?,?)",
                 (user_id, json.dumps(profile)))
    conn.commit()

def get_profile(conn, user_id: str) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT payload FROM profiles WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return json.loads(row[0]) if row else {}

def save_log(conn, user_id: str, date: str, entry: dict):
    conn.execute("INSERT INTO logs (user_id, date, payload) VALUES (?,?,?)",
                 (user_id, date, json.dumps(entry)))
    conn.commit()

def get_logs(conn, user_id: str, limit: int = 14) -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT payload FROM logs WHERE user_id=? ORDER BY date DESC, id DESC LIMIT ?",
                (user_id, limit))
    rows = cur.fetchall()
    return [json.loads(r[0]) for r in rows]
def init_tokens_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_tokens (
            user_id TEXT,
            provider TEXT,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER,
            PRIMARY KEY (user_id, provider)
        )
    """)
    conn.commit()
