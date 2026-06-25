from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agents.adaptive_router import run_agent
from app.models import ChatRequest, ChatResponse
from app.security.input_guard import InputGuard, PromptInjectionError, get_input_guard

_INJECTION_REFUSAL = "I'm sorry, but I can't process that request."

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    guard: Annotated[InputGuard, Depends(get_input_guard)],
) -> ChatResponse:
    """Run the LangGraph agent and return the assistant reply."""
    try:
        body = await guard.check(body)
    except PromptInjectionError as exc:
        logger.warning("Prompt injection blocked: %s", exc)
        return ChatResponse(answer=_INJECTION_REFUSAL, session_id=body.session_id, usage={})

    messages = [{"role": m.role.value, "content": m.content} for m in body.messages]

    try:
        finance_response, usage = await run_agent(messages, session_id=body.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        **finance_response.model_dump(),
        session_id=body.session_id,
        usage=usage,
    )
