from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import FeedbackRequest


class FeedbackStore:
    """Persists and queries user feedback for RLHF and quality monitoring."""

    async def save(self, feedback: FeedbackRequest) -> None:
        """Persist a feedback record to the backing store."""
        raise NotImplementedError

    async def get_by_session(self, session_id: str) -> list[FeedbackRequest]:
        """Retrieve all feedback entries for a given session."""
        raise NotImplementedError

    async def aggregate_ratings(self) -> dict[str, float]:
        """Return average ratings grouped by route or model."""
        raise NotImplementedError
