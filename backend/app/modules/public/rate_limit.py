"""In-process contact-form rate limiter (5 requests / hour / IP)."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import time

WINDOW_SECONDS = 60 * 60
MAX_REQUESTS = 5

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def reset_contact_rate_limiter() -> None:
    with _lock:
        _hits.clear()


def contact_rate_limited(ip: str) -> bool:
    """Record a hit for ip. Return True if the caller is over the limit."""
    now = time()
    cutoff = now - WINDOW_SECONDS
    key = ip or 'unknown'
    with _lock:
        bucket = _hits[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= MAX_REQUESTS:
            return True
        bucket.append(now)
        return False
