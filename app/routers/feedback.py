from __future__ import annotations

from fastapi import APIRouter

from app.models import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """Record thumbs-up / thumbs-down feedback for a response."""
    # TODO: persist to FeedbackStore
    return FeedbackResponse(recorded=True)
