from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.adaptive_router import run_agent
from app.config import settings
from app.models import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse


def _configure_langsmith() -> None:
    """Push LangSmith settings into os.environ so LangChain picks them up."""
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _configure_langsmith()
    yield


app = FastAPI(title="AI Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """Run the LangGraph agent and return the assistant reply."""
    if not body.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")

    messages = [{"role": m.role.value, "content": m.content} for m in body.messages]

    try:
        answer, usage = await run_agent(messages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        session_id=body.session_id,
        usage=dict(usage),
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """Record thumbs-up / thumbs-down feedback for a response."""
    # TODO: persist to FeedbackStore
    return FeedbackResponse(recorded=True)
