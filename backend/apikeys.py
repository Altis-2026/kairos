import hashlib
import os
import secrets
import sqlite3
import threading
import time

_DB = os.path.join(os.path.dirname(__file__), "kairos_keys.db")
_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _init():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash TEXT PRIMARY KEY,
                prefix TEXT NOT NULL,
                owner TEXT NOT NULL,
                label TEXT,
                created_at REAL NOT NULL,
                revoked INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                called_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_key(owner: str, label: str = "") -> dict:
    _init()
    key = "krs_" + secrets.token_hex(16)
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO api_keys (key_hash, prefix, owner, label, created_at) VALUES (?, ?, ?, ?, ?)",
            (_hash(key), key[:12], owner, label[:80], time.time()),
        )
        conn.commit()
    return {"key": key, "prefix": key[:12], "label": label[:80]}


def list_keys(owner: str) -> list:
    _init()
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT prefix, label, created_at, revoked FROM api_keys "
            "WHERE owner = ? ORDER BY created_at DESC",
            (owner,),
        ).fetchall()
    return [dict(r) for r in rows]


def revoke_key(owner: str, prefix: str) -> bool:
    _init()
    with _lock, _connect() as conn:
        cur = conn.execute(
            "UPDATE api_keys SET revoked = 1 WHERE owner = ? AND prefix = ?",
            (owner, prefix),
        )
        conn.commit()
        return cur.rowcount > 0


def resolve(key: str) -> str | None:
    if not key or not key.startswith("krs_"):
        return None
    _init()
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT owner FROM api_keys WHERE key_hash = ? AND revoked = 0",
            (_hash(key),),
        ).fetchone()
    return row["owner"] if row else None


def log_usage(owner: str, endpoint: str):
    try:
        _init()
        with _lock, _connect() as conn:
            conn.execute(
                "INSERT INTO usage_log (owner, endpoint, called_at) VALUES (?, ?, ?)",
                (owner, endpoint, time.time()),
            )
            conn.commit()
    except Exception:
        pass


def usage_summary(owner: str, days: int = 30) -> dict:
    _init()
    since = time.time() - days * 86400
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT endpoint, COUNT(*) AS calls FROM usage_log "
            "WHERE owner = ? AND called_at > ? GROUP BY endpoint "
            "ORDER BY calls DESC",
            (owner, since),
        ).fetchall()
    entries = [dict(r) for r in rows]
    return {
        "days": days,
        "endpoints": entries,
        "total_calls": sum(e["calls"] for e in entries),
    }
