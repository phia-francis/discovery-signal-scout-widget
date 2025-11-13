from __future__ import annotations
import os, sqlite3
from typing import Dict, List

def ensure_db() -> sqlite3.Connection:
    os.makedirs("signals", exist_ok=True)
    conn = sqlite3.connect("signals/signals.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS raw_items (
        url TEXT PRIMARY KEY, date TEXT, source TEXT, tier TEXT, title TEXT, summary TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS picks (
        run_date TEXT, url TEXT PRIMARY KEY, source TEXT, mission TEXT, archetype TEXT, score REAL)""")
    conn.commit()
    return conn

def log_raw(conn, items: List[Dict]):
    cur = conn.cursor()
    for it in items:
        try:
            cur.execute("INSERT OR IGNORE INTO raw_items (url,date,source,tier,title,summary) VALUES (?,?,?,?,?,?)",
                        (it["url"], it["date"], it["source"], it["tier"], it["title"], it["summary"]))
        except Exception:
            pass
    conn.commit()

def log_picks(conn, run_date: str, rows: List[Dict]):
    cur = conn.cursor()
    for r in rows:
        try:
            cur.execute("INSERT OR REPLACE INTO picks (run_date,url,source,mission,archetype,score) VALUES (?,?,?,?,?,?)",
                        (run_date, r["source_url"], r["source_title"], r["mission_links"], r["archetype"], r["total_score"]))
        except Exception:
            pass
    conn.commit()
