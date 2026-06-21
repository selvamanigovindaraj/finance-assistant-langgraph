from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import ChatRequest


class InputGuard:
    """Validates and sanitises incoming user messages before processing."""

    async def check(self, request: ChatRequest) -> ChatRequest:
        """Run all input validation checks and return the sanitised request.

        Raises:
            ValueError: if the request fails a safety check.
        """
        raise NotImplementedError

    def _check_length(self, text: str) -> None:
        """Raise if the message exceeds the allowed token budget."""
        raise NotImplementedError

    def _check_injection(self, text: str) -> None:
        """Raise if the message contains prompt-injection patterns."""
        raise NotImplementedError

    def _sanitise(self, text: str) -> str:
        """Strip or escape unsafe characters from user input."""
        raise NotImplementedError
