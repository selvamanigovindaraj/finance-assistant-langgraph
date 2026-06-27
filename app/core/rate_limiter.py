from __future__ import annotations

import time
from typing import Any

_RATE_LIMIT: int = 10
_RATE_WINDOW: float = 60.0

_AnyRedis = Any
_redis: _AnyRedis = None

RATE_LIMITED_MSG = (
    "You've reached the limit of 10 requests per minute. "
    "Please wait a moment and try again."
)


def init_rate_limiter(redis: _AnyRedis) -> None:
    """Set the Redis client — called once at startup."""
    global _redis
    _redis = redis


async def is_allowed(session_id: str) -> bool:
    """Return True if the session is within rate limits; consume one slot when True."""
    if not session_id:
        return True
    assert _redis is not None, "Rate limiter not initialised"
    key = f"rate:{session_id}"
    now = time.time()
    await _redis.zremrangebyscore(key, 0, now - _RATE_WINDOW)
    count: int = await _redis.zcard(key)
    if count >= _RATE_LIMIT:
        return False
    await _redis.zadd(key, {str(time.time_ns()): now})
    await _redis.expire(key, int(_RATE_WINDOW) + 1)
    return True
