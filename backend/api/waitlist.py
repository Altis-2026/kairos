"""
POST /waitlist       — join the Janus early-access waitlist
GET  /waitlist/count — how many people are on it (social proof)

Storage is SQLite next to the feed DB, and every signup is ALSO written to
stdout as a structured log line. Cloud Run's filesystem is ephemeral, so the
log line is the durable copy (recoverable from Cloud Logging) until this
moves to Firestore/Postgres before Janus launches. See docs/JANUS.md.
"""

import os
import re
import sqlite3
import threading
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

DB_PATH = os.getenv("WAITLIST_DB_PATH", "kairos_waitlist.db")
_lock = threading.Lock()

# Deliberately simple: enough to reject junk, not an RFC 5322 attempt.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class WaitlistRequest(BaseModel):
    email: str = Field(max_length=254)
    product: str = Field(default="janus", max_length=40)
    use_case: str = Field(default="", max_length=500)


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            product TEXT NOT NULL,
            use_case TEXT,
            created_at REAL NOT NULL,
            UNIQUE(email, product)
        )
        """
    )
    return conn


@router.post("/waitlist")
def join_waitlist(request: WaitlistRequest):
    email = request.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="That email doesn't look valid.")

    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO waitlist (email, product, use_case, created_at) "
            "VALUES (?, ?, ?, ?)",
            (email, request.product, request.use_case.strip(), time.time()),
        )
        conn.commit()
        new = cur.rowcount > 0
        row = conn.execute(
            "SELECT COUNT(*) FROM waitlist WHERE product = ?", (request.product,)
        ).fetchone()

    if new:
        # The durable copy — searchable in Cloud Logging as "waitlist signup".
        print(
            f"[kairos] waitlist signup: product={request.product} email={email} "
            f"use_case={request.use_case.strip()[:200]!r}"
        )
    return {"joined": True, "already": not new, "count": int(row[0])}


@router.get("/waitlist/count")
def waitlist_count(product: str = "janus"):
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM waitlist WHERE product = ?", (product,)
        ).fetchone()
    return {"product": product, "count": int(row[0])}
