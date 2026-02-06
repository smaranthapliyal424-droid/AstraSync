import sqlite3, json, os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./data/astrasync.db")

def get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles(
      user_id TEXT PRIMARY KEY,
      payload TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      date TEXT NOT NULL,
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
