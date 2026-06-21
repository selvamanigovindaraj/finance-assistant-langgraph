from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from app.models import ChatRequest, ChatResponse


class RAGPipeline:
    """Orchestrates retrieval-augmented generation: retrieve → augment → generate."""

    def __init__(self) -> None:
        pass

    async def run(self, request: ChatRequest) -> ChatResponse:
        """Execute the full RAG pipeline and return a complete response."""
        raise NotImplementedError

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream generated tokens as they are produced."""
        raise NotImplementedError

    def _build_context(self, documents: list) -> str:
        """Concatenate retrieved documents into a single context string."""
        raise NotImplementedError
