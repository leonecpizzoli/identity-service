import time
from collections import deque


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float, max_tracked_keys: int = 10000) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_tracked_keys = max_tracked_keys
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        if len(self._hits) > self._max_tracked_keys:
            self._evict_expired(now)
        bucket = self._hits.setdefault(key, deque())
        while bucket and now - bucket[0] > self._window_seconds:
            bucket.popleft()
        if len(bucket) >= self._limit:
            return False
        bucket.append(now)
        return True

    def _evict_expired(self, now: float) -> None:
        expired_keys = [
            key
            for key, bucket in self._hits.items()
            if not bucket or now - bucket[-1] > self._window_seconds
        ]
        for key in expired_keys:
            self._hits.pop(key, None)
