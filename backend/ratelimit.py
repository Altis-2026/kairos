import os
import threading
import time
from datetime import date

from fastapi import HTTPException, Request

_lock = threading.Lock()
_buckets: dict = {}
_daily = {"day": None, "count": 0}

LIMITS = {
    "ai": (int(os.getenv("RATE_AI_PER_HOUR", "60")), 3600),
    "compute": (int(os.getenv("RATE_COMPUTE_PER_HOUR", "120")), 3600),
}
DAILY_AI_CEILING = int(os.getenv("DAILY_AI_CEILING", "4000"))


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _take(kind: str, key: str) -> bool:
    capacity, window = LIMITS[kind]
    now = time.monotonic()
    with _lock:
        tokens, stamp = _buckets.get((kind, key), (capacity, now))
        tokens = min(capacity, tokens + (now - stamp) * capacity / window)
        if tokens < 1:
            _buckets[(kind, key)] = (tokens, now)
            return False
        _buckets[(kind, key)] = (tokens - 1, now)
        return True


def _spend_daily() -> bool:
    today = date.today()
    with _lock:
        if _daily["day"] != today:
            _daily["day"] = today
            _daily["count"] = 0
        if _daily["count"] >= DAILY_AI_CEILING:
            return False
        _daily["count"] += 1
        return True


def limit_ai(request: Request):
    if not _take("ai", client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="You're asking faster than the free tier allows. Wait a minute and try again.",
        )
    if not _spend_daily():
        raise HTTPException(
            status_code=429,
            detail="Kairos has reached today's free AI limit. Featured stories and the analysis wizard still work.",
        )


def limit_compute(request: Request):
    if not _take("compute", client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many analyses in a short time. Wait a minute and try again.",
        )


def reset():
    with _lock:
        _buckets.clear()
        _daily["day"] = None
        _daily["count"] = 0
