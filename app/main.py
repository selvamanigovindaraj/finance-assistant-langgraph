from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents.adaptive_router import run_agent
from app.config import settings
from app.models import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse

app = FastAPI(title="AI Agent API", version="0.1.0")

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
