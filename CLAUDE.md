# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11, UV package manager |
| Agent framework | LangGraph (`StateGraph` + `MessagesState`) + LangChain |
| LLM (generation) | `CLAUDE_GENERATION_MODEL` (Sonnet) |
| LLM (routing) | `CLAUDE_ROUTING_MODEL` (Haiku) |
| Conversation memory | `AsyncPostgresSaver` (Postgres) or `InMemorySaver` (fallback) |
| Vector store | Pinecone (cloud-hosted — no local service) |
| Web search | Tavily |
| Observability | LangSmith (tracing + thread grouping) |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |

## Commands

Prefer `make` targets over raw `uv run` calls — they are the canonical way to run quality checks.

```bash
# Backend — install deps (creates .venv)
uv sync            # production deps only
uv sync --dev      # include dev deps (pytest, ruff, mypy) — reads [dependency-groups] dev

# Run backend locally (from project root, not from inside app/)
uv run uvicorn app.main:app --reload

# Quality checks (individual)
make format        # ruff format app tests
make lint          # ruff check app tests
make typecheck     # mypy app
make test          # pytest --cov=app

# Run all checks in one shot
make check         # format → lint → typecheck → test

# Seed Pinecone index (drop docs in data/raw/ first)
make seed          # uv run python scripts/seed.py

# Frontend
cd frontend && npm install && npm run dev   # dev server on :5173
cd frontend && npm run build               # production build

# Docker (includes Postgres)
make build         # docker compose build (images only)
make up            # docker compose up -d (start pre-built containers)
make start         # docker compose up --build -d (build + start in one step)
make down          # docker compose down
```

A **pre-commit hook** (`.git/hooks/pre-commit`) runs `ruff check` before every commit and blocks it on lint failures. It uses `.venv/bin/ruff` via `uv run`, so `uv sync --dev` must be run at least once.

## Architecture

### Request flow

```
POST /chat  { messages: [last_user_msg], session_id }
  → app/main.py              validates ChatRequest, calls run_agent()
  → app/agents/adaptive_router.py  run_agent()
      if session_id:
        send only latest message; checkpointer restores full history by thread_id
      else:
        send full messages list; no checkpointer state used
      _graph.ainvoke({"messages": lc_messages}, config)
        └─ "agent" node      injects system prompt, calls Claude via ChatAnthropic
  → returns (answer: str, usage: dict)
```

### Conversation memory — checkpointer pattern

The graph is **not** compiled at module import. Instead:

1. `app/main.py` lifespan starts → checks `settings.DATABASE_URL`
2. If set: opens a `psycopg3` async connection pool → creates `AsyncPostgresSaver` → calls `setup()` (idempotent; creates LangGraph's three Postgres tables) → calls `init_graph(checkpointer)`
3. If not set: falls back to `InMemorySaver` → calls `init_graph(checkpointer)`
4. `_graph` starts as `None`; an `assert` guard prevents use before init

**Why only the last message is sent from the frontend:** `MessagesState` uses an `add_messages` reducer that *appends* — it does not replace. Sending the full history on every turn would duplicate messages on top of what the checkpointer already restored. Only the new user message is sent; the checkpointer merges it with the stored history automatically.

**LangGraph's three Postgres tables** (created by `setup()`, never touch manually):
- `checkpoints` — metadata pointer to the latest checkpoint per thread
- `checkpoint_blobs` — serialised state (the messages list lives here), keyed by `(thread_id, checkpoint_id)`
- `checkpoint_writes` — pending mid-node writes for crash recovery

### LangSmith tracing

`_configure_langsmith()` in `app/main.py` sets `LANGCHAIN_TRACING_V2` and `LANGSMITH_TRACING` env vars at startup from `settings`. Each `ainvoke` creates one LangSmith trace. Traces for the same session are grouped in the **Threads** tab (not the Traces tab) via `metadata: {session_id}` in `RunnableConfig`. The `config` is also forwarded to `llm.invoke()` inside the node so child spans inherit it.

### Key design boundaries

- **`app/config.py`** — single `Settings` object (pydantic-settings); all env vars go here. `DATABASE_URL = ""` means fall back to `InMemorySaver`. `extra = "ignore"` allows extra shell vars without breaking startup.
- **`app/db.py`** — `open_pool` / `close_pool` helpers for the psycopg3 async connection pool. Pool uses `autocommit=True` (required for `CREATE INDEX CONCURRENTLY` in `setup()`) and `dict_row` row factory.
- **`app/models.py`** — all API boundary types (`ChatRequest`, `ChatResponse`, `FeedbackRequest`, etc.). Never use plain `dict` at HTTP boundaries.
- **`app/agents/adaptive_router.py`** — `init_graph(checkpointer)` compiles and registers the graph; `run_agent(messages, session_id)` invokes it. Intended to be split: routing logic (Haiku classifies query → tool) should be separate from generation. Known pending refactor.
- **`app/components/retriever.py`** — `PineconeRetriever` stub; implement `retrieve()` and `add_documents()` here before wiring into the RAG pipeline.
- **`app/services/rag_pipeline.py`** — intended orchestrator: retriever → context assembly → LLM. Not yet wired into `/chat`.

### What is and isn't implemented

| Module | Status |
|---|---|
| `POST /chat` | Working — LangGraph agent calls Claude, multi-turn memory via checkpointer |
| `GET /health` | Working |
| `POST /feedback` | Stub — always returns `recorded: true` |
| Conversation memory | Working — Postgres (`AsyncPostgresSaver`) with `InMemorySaver` fallback |
| LangSmith tracing | Working — traces grouped by `session_id` in Threads tab |
| RAG pipeline | Stub — retriever, cache all `raise NotImplementedError` |
| Observability | Stub — cost tracker, feedback store all `raise NotImplementedError` |
| Security | Stub — input guard, output filter all `raise NotImplementedError` |
| Frontend | Working — chat UI, session management, sends only latest message per turn |

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
- `TYPE_CHECKING` guards only for genuine circular imports or types that don't exist at runtime. Do NOT use them merely to defer a heavy import — `from __future__ import annotations` already makes all annotations lazy strings.
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
- Stub tests must be marked `@pytest.mark.skip(reason="not yet implemented")` — do not leave bare `raise NotImplementedError` in collected tests.
- Coverage threshold: currently `0` in `pyproject.toml` while all tests are stubs. Raise back to `80` once real tests are written.
