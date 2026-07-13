import json
import os
import sqlite3
import threading
import time

DB_PATH = os.getenv("FEED_DB_PATH", "kairos_feed.db")

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedupe_key TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                source_title TEXT,
                source_link TEXT,
                region TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bbox TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                data_date TEXT,
                headline_label TEXT,
                headline_value REAL,
                headline_unit TEXT,
                confidence REAL,
                summary TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sweeps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at REAL NOT NULL,
                finished_at REAL,
                targets INTEGER DEFAULT 0,
                findings INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()


def save_finding(f: dict) -> bool:
    with _lock, _connect() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO findings (
                dedupe_key, source, source_title, source_link, region,
                analysis_type, display_name, bbox, start_date, end_date,
                data_date, headline_label, headline_value, headline_unit,
                confidence, summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f["dedupe_key"],
                f["source"],
                f.get("source_title"),
                f.get("source_link"),
                f["region"],
                f["analysis_type"],
                f["display_name"],
                json.dumps(f["bbox"]),
                f["start_date"],
                f["end_date"],
                f.get("data_date"),
                f.get("headline_label"),
                f.get("headline_value"),
                f.get("headline_unit"),
                f.get("confidence"),
                f.get("summary"),
                time.time(),
            ),
        )
        conn.commit()
        return cur.rowcount > 0


def recent_findings(limit: int = 40) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM findings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["bbox"] = json.loads(item["bbox"])
        del item["dedupe_key"]
        out.append(item)
    return out


def finding_count() -> int:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM findings").fetchone()
        return int(row["n"])


def start_sweep() -> int:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sweeps (started_at) VALUES (?)", (time.time(),)
        )
        conn.commit()
        return int(cur.lastrowid)


def finish_sweep(sweep_id: int, targets: int, findings: int, errors: int):
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE sweeps SET finished_at = ?, targets = ?, findings = ?, errors = ? WHERE id = ?",
            (time.time(), targets, findings, errors, sweep_id),
        )
        conn.commit()


def last_sweep() -> dict:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sweeps WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def sweep_count() -> int:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM sweeps").fetchone()
        return int(row["n"])
