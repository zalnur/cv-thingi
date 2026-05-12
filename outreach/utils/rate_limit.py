"""Simple async rate limiter."""

import asyncio
import time


class AsyncRateLimiter:
    """Ensure at least interval_seconds between actions."""

    def __init__(self, interval_seconds: float) -> None:
        self._interval_seconds = max(0.0, interval_seconds)
        self._last_run = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_run
            wait_for = self._interval_seconds - elapsed
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_run = time.monotonic()
