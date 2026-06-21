from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import ChatResponse


class OutputFilter:
    """Post-processes LLM responses to remove harmful or sensitive content."""

    async def filter(self, response: ChatResponse) -> ChatResponse:
        """Apply all output filters and return the cleaned response."""
        raise NotImplementedError

    def _redact_pii(self, text: str) -> str:
        """Redact personally identifiable information from generated text."""
        raise NotImplementedError

    def _check_hallucination_markers(self, text: str) -> None:
        """Log a warning if the response contains known hallucination signals."""
        raise NotImplementedError
