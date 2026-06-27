from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agents.adaptive_router import run_agent
from app.core.rate_limiter import RATE_LIMITED_MSG, is_allowed
from app.models import ChatRequest, ChatResponse
from app.security.input_guard import InputGuard, PromptInjectionError, get_input_guard
from app.security.output_filter import OutputGuard, get_output_guard
from app.security.pii_store import PiiStore, get_pii_store

_INJECTION_REFUSAL = "I'm sorry, but I can't process that request."

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    guard: Annotated[InputGuard, Depends(get_input_guard)],
    output_guard: Annotated[OutputGuard, Depends(get_output_guard)],
    pii_store: Annotated[PiiStore, Depends(get_pii_store)],
) -> ChatResponse:
    """Run the LangGraph agent and return the assistant reply."""
    try:
        sanitised_body, pii_pairs = await guard.check(body)
    except PromptInjectionError as exc:
        logger.warning("Prompt injection blocked: %s", exc)
        return ChatResponse(answer=_INJECTION_REFUSAL, session_id=body.session_id, usage={})

    session_id = sanitised_body.session_id

    if not await is_allowed(session_id):
        return ChatResponse(answer=RATE_LIMITED_MSG, session_id=session_id, usage={})

    await pii_store.merge(session_id, pii_pairs)

    messages = [{"role": m.role.value, "content": m.content} for m in sanitised_body.messages]

    try:
        finance_response, usage = await run_agent(messages, session_id=session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        answer=await output_guard.restore(
            finance_response.answer, session_id, pii_store, pii_pairs
        ),
        disclaimer=finance_response.disclaimer,
        tool_used=finance_response.tool_used,
        session_id=session_id,
        usage=usage,
    )
