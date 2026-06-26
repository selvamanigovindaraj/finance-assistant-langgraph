from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.agents.adaptive_router import init_graph
from app.config import settings
from app.security.pii_store import init_pii_store


def configure_langsmith() -> None:
    """Push LangSmith settings into os.environ so LangChain picks them up."""
    tracing = settings.LANGSMITH_TRACING or ("true" if settings.LANGCHAIN_TRACING_V2 else "")
    api_key = settings.LANGSMITH_API_KEY or settings.LANGCHAIN_API_KEY
    project = settings.LANGSMITH_PROJECT or settings.LANGCHAIN_PROJECT or "ai-agent"
    endpoint = (
        settings.LANGSMITH_ENDPOINT
        or settings.LANGCHAIN_ENDPOINT
        or "https://api.smith.langchain.com"
    )

    if tracing.lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint
    os.environ["LANGSMITH_ENDPOINT"] = endpoint


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure tracing, Redis, and the LangGraph checkpointer on startup."""
    configure_langsmith()

    init_pii_store(Redis.from_url(settings.REDIS_URL, decode_responses=False))

    if settings.DATABASE_URL:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        from app.db import close_pool, open_pool

        pool = await open_pool(settings.DATABASE_URL)
        pg_checkpointer = AsyncPostgresSaver(pool)
        await pg_checkpointer.setup()
        init_graph(pg_checkpointer)
        try:
            yield
        finally:
            await close_pool(pool)
    else:
        from langgraph.checkpoint.memory import InMemorySaver

        init_graph(InMemorySaver())
        yield
