from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from langgraph.graph import StateGraph

if TYPE_CHECKING:
    from app.models import ChatRequest, ChatResponse


RouteDecision = Literal["vector_search", "web_search", "financial_data", "direct"]


class AdaptiveRouter:
    """Routes incoming queries to the appropriate tool using a lightweight model."""

    def __init__(self) -> None:
        self._graph: StateGraph | None = None

    def build_graph(self) -> StateGraph:
        """Construct and compile the LangGraph routing graph."""
        raise NotImplementedError

    async def route(self, request: ChatRequest) -> RouteDecision:
        """Classify the query and return the best tool route."""
        raise NotImplementedError

    async def run(self, request: ChatRequest) -> ChatResponse:
        """Execute the full agent loop and return a final response."""
        raise NotImplementedError
