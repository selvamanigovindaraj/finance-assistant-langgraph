from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import fakeredis
import pytest

from app.core.rate_limiter import _RATE_LIMIT, init_rate_limiter, is_allowed


@pytest.fixture(autouse=True)
async def setup_redis() -> AsyncGenerator[None, None]:
    init_rate_limiter(fakeredis.FakeAsyncRedis())
    yield


# ─── Basic allow / block ──────────────────────────────────────────────────────


async def test_allows_first_request() -> None:
    assert await is_allowed("sess-1") is True


async def test_allows_up_to_rate_limit() -> None:
    for _ in range(_RATE_LIMIT):
        assert await is_allowed("sess-1") is True


async def test_blocks_request_over_limit() -> None:
    for _ in range(_RATE_LIMIT):
        await is_allowed("sess-1")
    assert await is_allowed("sess-1") is False


# ─── Sessionless requests ─────────────────────────────────────────────────────


async def test_sessionless_requests_always_allowed() -> None:
    for _ in range(_RATE_LIMIT + 5):
        assert await is_allowed("") is True


# ─── Session isolation ────────────────────────────────────────────────────────


async def test_sessions_have_independent_buckets() -> None:
    for _ in range(_RATE_LIMIT):
        await is_allowed("sess-a")
    assert await is_allowed("sess-b") is True


async def test_blocked_session_does_not_affect_other_session() -> None:
    for _ in range(_RATE_LIMIT + 1):
        await is_allowed("sess-a")
    assert await is_allowed("sess-b") is True


# ─── Window expiry ────────────────────────────────────────────────────────────


async def test_requests_allowed_after_window_expires() -> None:
    with patch("app.core.rate_limiter.time.time") as mock_time:
        mock_time.return_value = 0.0
        for _ in range(_RATE_LIMIT):
            await is_allowed("sess-1")
        mock_time.return_value = 61.0
        assert await is_allowed("sess-1") is True


async def test_requests_still_blocked_within_window() -> None:
    with patch("app.core.rate_limiter.time.time") as mock_time:
        mock_time.return_value = 0.0
        for _ in range(_RATE_LIMIT):
            await is_allowed("sess-1")
        mock_time.return_value = 59.0
        assert await is_allowed("sess-1") is False
