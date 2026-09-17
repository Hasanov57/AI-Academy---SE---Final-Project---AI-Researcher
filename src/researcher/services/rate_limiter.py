"""Concurrency-safe minimum-interval rate limiter for polite upstream access."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable


class AsyncRateLimiter:
    """Enforce a minimum interval between calls sharing the same limiter."""

    def __init__(
        self,
        min_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds cannot be negative")
        self._minimum = min_interval_seconds
        self._clock = clock
        self._last_call: float | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the next call is allowed, then reserve its slot."""
        async with self._lock:
            now = self._clock()
            if self._last_call is not None:
                wait = self._minimum - (now - self._last_call)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_call = self._clock()
