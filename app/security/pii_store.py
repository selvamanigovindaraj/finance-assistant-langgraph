from __future__ import annotations

from typing import Any

_TTL_SECONDS = 86_400  # 24 h rolling window

# Redis is not generic at runtime; use Any to avoid type-arg errors.
_AnyRedis = Any


class PiiStore:
    """Persists per-session fake→real PII mappings in Redis across turns and restarts."""

    def __init__(self, redis: _AnyRedis) -> None:
        self._redis = redis

    def _key(self, session_id: str) -> str:
        return f"pii:{session_id}"

    async def merge(self, session_id: str, pairs: list[tuple[Any, str]]) -> None:
        """Add this turn's fake→real pairs to the session hash; reset TTL."""
        if not pairs or not session_id:
            return
        key = self._key(session_id)
        mapping: dict[str, str] = {item.text: original for item, original in pairs}
        await self._redis.hset(key, mapping=mapping)
        await self._redis.expire(key, _TTL_SECONDS)

    async def load(self, session_id: str) -> dict[str, str]:
        """Return the full accumulated {fake: real} map for the session."""
        if not session_id:
            return {}
        raw: dict[Any, Any] = await self._redis.hgetall(self._key(session_id))
        return {k.decode(): v.decode() for k, v in raw.items()}


_instance: PiiStore | None = None


def get_pii_store() -> PiiStore:
    """Return the process-wide PiiStore singleton."""
    assert _instance is not None, "init_pii_store() must be called before get_pii_store()"
    return _instance


def init_pii_store(redis: _AnyRedis) -> None:
    """Create the singleton; called once from lifespan."""
    global _instance
    _instance = PiiStore(redis)
