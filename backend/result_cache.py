import os
import threading
import time
from collections import OrderedDict

TTL_SECONDS = int(os.getenv("RESULT_CACHE_TTL", str(6 * 3600)))
MAX_ENTRIES = int(os.getenv("RESULT_CACHE_SIZE", "256"))

_lock = threading.Lock()
_entries: OrderedDict = OrderedDict()


def get(key: str):
    with _lock:
        hit = _entries.get(key)
        if hit is None:
            return None
        stamp, value = hit
        if time.monotonic() - stamp > TTL_SECONDS:
            del _entries[key]
            return None
        _entries.move_to_end(key)
        return value


def put(key: str, value) -> None:
    with _lock:
        _entries[key] = (time.monotonic(), value)
        _entries.move_to_end(key)
        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)


def clear() -> None:
    with _lock:
        _entries.clear()
