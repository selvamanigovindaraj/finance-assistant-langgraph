from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

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
    raise NotImplementedError


@app.post("/chat")
async def chat() -> dict:
    """Main chat endpoint — delegates to RAG pipeline."""
    raise NotImplementedError


@app.post("/feedback")
async def submit_feedback() -> dict:
    """Record thumbs-up / thumbs-down feedback for a response."""
    raise NotImplementedError
