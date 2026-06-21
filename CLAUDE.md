# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11, UV package manager |
| Agent framework | LangGraph (`StateGraph` + `MessagesState`) + LangChain |
| LLM (generation) | `CLAUDE_GENERATION_MODEL` (Sonnet) |
| LLM (routing) | `CLAUDE_ROUTING_MODEL` (Haiku) |
| Vector store | Pinecone (cloud-hosted — no local service) |
| Web search | Tavily |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |

## Commands

```bash
# Backend — install deps (creates .venv)
uv sync            # production deps only
uv sync --dev      # include dev deps (pytest, ruff, mypy)

# Run backend locally (from project root, not from inside app/)
uv run uvicorn app.main:app --reload

# Lint / format
uv run ruff check app tests
uv run ruff format app tests

# Type check
uv run mypy app

# Tests
uv run pytest                        # all tests
uv run pytest tests/test_routing.py  # single file
uv run pytest -k "test_cache_hit"    # single test by name
uv run pytest --cov=app              # with coverage

# Seed Pinecone index (drop docs in data/raw/ first)
uv run python scripts/seed.py

# Frontend
cd frontend && npm install && npm run dev   # dev server on :5173
cd frontend && npm run build               # production build

# Docker
docker compose up --build   # builds and starts backend (:8000) + frontend (:5173)
docker compose up -d        # detached
```

## Architecture

### Request flow

```
POST /chat
  → app/main.py            validates ChatRequest, calls run_agent()
  → app/agents/adaptive_router.py
      _graph (compiled StateGraph)
        └─ "agent" node    injects system prompt, calls Claude via ChatAnthropic
  → returns (answer: str, usage: dict)
```

The graph is compiled once at module import (`_graph = _build_graph()`) and reused across requests. `MessagesState` carries the full conversation list; the system prompt is prepended inside the node, not stored in state.

### Key design boundaries

- **`app/config.py`** — single `Settings` object (pydantic-settings); all env vars go here. `extra = "ignore"` allows LangSmith/other vars in the shell without breaking startup.
- **`app/models.py`** — all API boundary types (`ChatRequest`, `ChatResponse`, `FeedbackRequest`, etc.). Never use plain `dict` at HTTP boundaries.
- **`app/agents/adaptive_router.py`** — currently holds the working LangGraph chat agent. Intended to be split: routing logic (Haiku classifies query → tool) should be separate from generation. This is a known pending refactor.
- **`app/components/retriever.py`** — `PineconeRetriever` stub; implement `retrieve()` and `add_documents()` here before wiring into the RAG pipeline.
- **`app/services/rag_pipeline.py`** — intended orchestrator: retriever → context assembly → LLM. Not yet wired into `/chat`.

### What is and isn't implemented

| Module | Status |
|---|---|
| `POST /chat` | Working — LangGraph agent calls Claude |
| `GET /health` | Working |
| `POST /feedback` | Stub — always returns `recorded: true` |
| RAG pipeline | Stub — retriever, cache, conversation memory all `raise NotImplementedError` |
| Observability | Stub — tracer, cost tracker, feedback store all `raise NotImplementedError` |
| Security | Stub — input guard, output filter all `raise NotImplementedError` |
| Frontend | Stub — all components return `<></>`, hooks throw |

## Coding principles

These principles apply to all generated code, in every language:

- **KISS** — Start with the simplest solution that works. Add complexity only when a concrete requirement demands it, not in anticipation of one.
- **DRY** — Extract repeated logic into a single authoritative place. Every piece of knowledge should have one representation.
- **YAGNI** — Build only what the current task requires. Do not add hooks, abstractions, or configuration points for hypothetical future needs.
- **Separation of Concerns** — Each module, class, or function should have one reason to change. Keep I/O, business logic, and presentation in separate layers so each can be tested and changed independently.
- **Law of Demeter** — A unit should interact only with its immediate collaborators. Avoid chaining through internal structure (`a.b.c.do()`); pass what is needed or expose a higher-level method instead.

## Code style (from `.claude/rules/`)

**Python**
- Every file starts with `from __future__ import annotations`.
- `TYPE_CHECKING` guards for import-time-only types.
- `ruff format` + `ruff check` (line length 100, rules: E F I UP B SIM).
- `mypy --strict` must pass.
- One-line docstrings only.

**TypeScript**
- Functional components; explicit return types on all exports.
- `interface` for object shapes, `type` for unions/aliases.
- Tailwind classes only — no inline `style` props.
- No `any`; narrow `unknown` explicitly.
- Unused stub parameters must be prefixed with `_` (tsc strict mode enforced in Docker build).

**Testing**
- `pytest-asyncio` with `asyncio_mode = "auto"` — no need to mark individual tests.
- Integration tests hit a real Pinecone test index, not mocks.
- Coverage threshold: 80% on `app/` enforced by `pyproject.toml`.
