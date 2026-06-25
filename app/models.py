from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.prompts.templates import AGENT_DISCLAIMER


class Role(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    """A single conversation turn."""

    role: Role
    content: str


class ChatRequest(BaseModel):
    """Incoming chat request body."""

    messages: list[Message] = Field(..., min_length=1)
    session_id: str = Field(default="", description="Optional session identifier")
    stream: bool = False


class Source(BaseModel):
    """A cited source document."""

    title: str
    url: str | None = None
    snippet: str = ""


class FinanceResponse(BaseModel):
    """Structured LLM output for the finance agent."""

    answer: str
    disclaimer: str = AGENT_DISCLAIMER
    tool_used: str | None = None


class ChatResponse(BaseModel):
    """Response returned by the chat endpoint."""

    answer: str
    disclaimer: str = ""
    tool_used: str | None = None
    sources: list[Source] = []
    session_id: str = ""
    usage: dict[str, Any] = {}


class FeedbackRequest(BaseModel):
    """Thumbs up / down feedback payload."""

    session_id: str
    message_id: str
    rating: int = Field(..., ge=-1, le=1, description="-1 = bad, 0 = neutral, 1 = good")
    comment: str = ""


class FeedbackResponse(BaseModel):
    """Acknowledgement of recorded feedback."""

    recorded: bool
