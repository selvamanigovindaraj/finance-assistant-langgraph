from __future__ import annotations

import pytest

from app.services.semantic_cache import SemanticCache


@pytest.fixture
def cache() -> SemanticCache:
    return SemanticCache(similarity_threshold=0.95)


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache: SemanticCache) -> None:
    """get() should return None when no similar query is cached."""
    raise NotImplementedError


@pytest.mark.asyncio
async def test_cache_hit_returns_response(cache: SemanticCache) -> None:
    """get() should return the cached response for a near-duplicate query."""
    raise NotImplementedError


@pytest.mark.asyncio
async def test_invalidate_removes_entry(cache: SemanticCache) -> None:
    """invalidate() should remove the matching cached entry."""
    raise NotImplementedError
