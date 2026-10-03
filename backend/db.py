"""SQLite persistence: analysis history + upstream response cache."""
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))


def db_path() -> str:
    p = os.getenv("DATABASE_PATH", "data/smartstart.db")
    return p if os.path.isabs(p) else os.path.join(BASE, p)


def conn():
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path, timeout=15)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses(
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
              business_name TEXT, category TEXT, location TEXT, score REAL,
              result_json TEXT NOT NULL, ai_json TEXT, ai_created_at TEXT);
            CREATE TABLE IF NOT EXISTS cache(
              key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at REAL NOT NULL);
            """
        )


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cache_get(key, ttl):
    with conn() as c:
        r = c.execute("SELECT value, created_at FROM cache WHERE key=?", (key,)).fetchone()
    if r and time.time() - r["created_at"] < ttl:
        return json.loads(r["value"])
    return None


def cache_set(key, value):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (key, json.dumps(value), time.time()))


def save_analysis(result):
    aid = uuid.uuid4().hex[:12]
    result["id"] = aid
    result["created_at"] = now_iso()
    with conn() as c:
        c.execute(
            "INSERT INTO analyses(id,created_at,business_name,category,location,score,result_json) VALUES(?,?,?,?,?,?,?)",
            (aid, result["created_at"], result["input"]["business_name"], result["input"]["category"],
             result["location"]["display_name"], result["feasibility"]["score"], json.dumps(result)),
        )
    return aid


def get_analysis(aid):
    with conn() as c:
        r = c.execute("SELECT * FROM analyses WHERE id=?", (aid,)).fetchone()
    if not r:
        return None
    res = json.loads(r["result_json"])
    res["ai"] = json.loads(r["ai_json"]) if r["ai_json"] else None
    res["ai_created_at"] = r["ai_created_at"]
    return res


def set_ai(aid, ai):
    with conn() as c:
        c.execute("UPDATE analyses SET ai_json=?, ai_created_at=? WHERE id=?", (json.dumps(ai), now_iso(), aid))


def list_analyses(limit=50):
    with conn() as c:
        rows = c.execute(
            "SELECT id,created_at,business_name,category,location,score,ai_json IS NOT NULL AS has_ai "
            "FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_analysis(aid):
    with conn() as c:
        return c.execute("DELETE FROM analyses WHERE id=?", (aid,)).rowcount > 0
