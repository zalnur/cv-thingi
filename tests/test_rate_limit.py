import time

import pytest

from outreach.utils.rate_limit import AsyncRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_waits_between_calls() -> None:
    limiter = AsyncRateLimiter(0.01)

    start = time.monotonic()
    await limiter.wait()
    await limiter.wait()

    assert time.monotonic() - start >= 0.009
