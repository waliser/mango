import time
import pytest
from mango.util.rate_limiter import RateLimiter


async def test_limiter_spaces_out_calls():
    # capacity 2, refill 5/sec -> 3rd call must wait ~0.2s after burst of 2
    rl = RateLimiter(rate=5.0, capacity=2)
    start = time.monotonic()
    for _ in range(3):
        await rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.18  # third token needs ~1/5s to refill
