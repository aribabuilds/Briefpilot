"""In-memory sliding-window rate limiter (M24), keyed by an arbitrary string
(the client IP, in practice). Pure and clock-injectable -- same testability
pattern as services/retention.py's purge_expired(): the *rule* ("no more
than max_requests hits per window_seconds") is trivial to unit test without
a real wall clock.

Known limitation, consistent with InMemoryJobRepository/InMemoryDocumentStore
(ADR-0001): state is per-process and resets on restart, and doesn't share
across multiple instances. A multi-instance deployment would need a shared
store (e.g. Redis) behind the same allow() interface -- out of scope while
this app runs as a single zero-cost process.
"""

import threading
import time
from functools import lru_cache

from app.config.settings import get_settings


class RateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float) -> bool:
        with self._lock:
            cutoff = now - self._window_seconds
            hits = [hit for hit in self._hits.get(key, []) if hit > cutoff]
            if len(hits) >= self._max_requests:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def allow_now(self, key: str) -> bool:
        return self.allow(key, now=time.monotonic())


@lru_cache
def get_upload_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
