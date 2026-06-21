# AI Agent — Developer Guide

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11 |
| Agent framework | LangGraph + LangChain |
| LLM (generation) | Anthropic Claude Sonnet |
| LLM (routing) | Anthropic Claude Haiku |
| Vector store | Pinecone (cloud-hosted) |
| Web search | Tavily |
| Package manager | UV |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |
| Containerisation | Docker + docker-compose |

## Running locally

```bash
cp .env.example .env   # fill in API keys
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## Import conventions

All backend modules use the `app.*` prefix (e.g. `from app.config import settings`).
Run uvicorn from the project root, not from inside `app/`.

## Seeding the vector store

```bash
# Place raw documents in data/raw/
uv run python scripts/seed.py
```

## Running tests

```bash
uv run pytest --cov=app
```
