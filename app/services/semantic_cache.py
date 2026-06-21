from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import ChatResponse


class SemanticCache:
    """Cache responses by semantic similarity of the query to avoid redundant LLM calls."""

    def __init__(self, similarity_threshold: float = 0.95) -> None:
        self.similarity_threshold = similarity_threshold

    async def get(self, query: str) -> ChatResponse | None:
        """Return a cached response if a semantically similar query exists."""
        raise NotImplementedError

    async def set(self, query: str, response: ChatResponse) -> None:
        """Store a query-response pair in the semantic cache."""
        raise NotImplementedError

    async def invalidate(self, query: str) -> None:
        """Remove a cached entry by query."""
        raise NotImplementedError
