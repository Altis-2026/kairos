import os

from redis import Redis
from rq import Queue

_queue = None


def get_queue():
    global _queue
    if _queue is not None:
        return _queue
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        conn = Redis.from_url(redis_url)
        conn.ping()
        _queue = Queue("kairos", connection=conn, default_timeout=600)
        return _queue
    except Exception:
        return None
