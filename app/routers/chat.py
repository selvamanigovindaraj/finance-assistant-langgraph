from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agents.adaptive_router import run_agent
from app.models import ChatRequest, ChatResponse
from app.security.input_guard import InputGuard, get_input_guard

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    guard: Annotated[InputGuard, Depends(get_input_guard)],
) -> ChatResponse:
    """Run the LangGraph agent and return the assistant reply."""
    body = await guard.check(body)
    messages = [{"role": m.role.value, "content": m.content} for m in body.messages]

    try:
        answer, usage = await run_agent(messages, session_id=body.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        answer=answer,
        session_id=body.session_id,
        usage=usage,
    )
