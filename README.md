# AI Finance Assistant

A conversational AI agent for finance assistance, built with FastAPI, LangGraph, and React.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11, UV package manager |
| Agent | LangGraph (`StateGraph`) + LangChain |
| LLM | Claude Sonnet (generation), Claude Haiku (routing) |
| Vector store | Pinecone |
| Web search | Tavily |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |
| Observability | LangSmith |

## Prerequisites

- Python 3.11+
- Node.js 18+
- [UV](https://docs.astral.sh/uv/) package manager
- Docker + Docker Compose (optional)

## Setup

**1. Clone and install**

```bash
git clone <repo-url>
cd ai-agent

uv sync --dev       # backend deps
cd frontend && npm install && cd ..
```

**2. Configure environment**

Copy `.env.example` to `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=ai-agent-index
TAVILY_API_KEY=...

# Optional — LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=ai-agent
```

## Running locally

```bash
# Backend (port 8000)
uv run uvicorn app.main:app --reload

# Frontend (port 5173) — in a separate terminal
cd frontend && npm run dev
```

## Running with Docker

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

Both services support live-reload via volume mounts.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Send a message, get an AI reply |
| `POST` | `/feedback` | Submit thumbs-up/down on a response |

### Chat request

```json
{
  "messages": [
    { "role": "user", "content": "What is dollar-cost averaging?" }
  ],
  "session_id": "optional-string"
}
```

## Development

```bash
# Lint and format
uv run ruff check app tests
uv run ruff format app tests

# Type check
uv run mypy app

# Tests
uv run pytest
uv run pytest --cov=app   # with coverage (threshold: 80%)

# Seed Pinecone index (place source docs in data/raw/ first)
uv run python scripts/seed.py
```

## Project structure

```
app/
  main.py               # FastAPI app, routes
  config.py             # Settings (pydantic-settings)
  models.py             # API request/response types
  agents/
    adaptive_router.py  # LangGraph agent (chat + routing)
  components/
    retriever.py        # Pinecone retriever (stub)
  services/
    rag_pipeline.py     # RAG orchestrator (stub)
  observability/        # Tracing, cost tracking (stub)
  security/             # Input/output guards (stub)
frontend/
  src/
    components/         # React UI components
    hooks/              # Custom React hooks
    services/           # API client
    types/              # Shared TypeScript types
scripts/
  seed.py               # Pinecone index seeder
data/
  raw/                  # Source documents for RAG
```
