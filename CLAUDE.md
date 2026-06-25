# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11, UV package manager |
| Agent framework | LangGraph (`StateGraph` + `MessagesState`) + LangChain |
| LLM | Deepseek via OpenAI-compatible API (`ChatOpenAI` + `DEEPSEEK_ENDPOINT`) |
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
  → app/routers/chat.py          validates ChatRequest
  → InputGuard.check()           regex injection filter → LLM judge → PII redaction
  → app/agents/adaptive_router.py  run_agent()
      if session_id:
        send only latest message; checkpointer restores full history by thread_id
      else:
        send full messages list; no checkpointer state used
      _graph.ainvoke({"messages": lc_messages}, config)
        └─ "agent" node      _agent_node() injects system prompt, calls Deepseek LLM
        └─ tools_condition   AIMessage has tool_calls? → "tools" node; else → END
        └─ "tools" node      ToolNode executes the tool, appends ToolMessage to state
        └─ loops back to "agent" until the LLM responds with no tool calls
      _parse_result()        extracts answer, last tool name, usage metadata
  → returns FinanceResponse(answer, disclaimer, tool_used) + usage dict
```

### Conversation memory — checkpointer pattern

The graph is **not** compiled at module import. Instead:

1. `app/main.py` lifespan starts → checks `settings.DATABASE_URL`
2. If set: opens a `psycopg3` async connection pool → creates `AsyncPostgresSaver` → calls `setup()` (idempotent; creates LangGraph's three Postgres tables) → calls `init_graph(checkpointer)`
3. If not set: falls back to `InMemorySaver` → calls `init_graph(checkpointer)`
4. `_graph` and `_llm` start as `None`; an `assert` guard in `run_agent` prevents use before init

**Why only the last message is sent from the frontend:** `MessagesState` uses an `add_messages` reducer that *appends* — it does not replace. Sending the full history on every turn would duplicate messages on top of what the checkpointer already restored. Only the new user message is sent; the checkpointer merges it with the stored history automatically.

**LangGraph's three Postgres tables** (created by `setup()`, never touch manually):
- `checkpoints` — metadata pointer to the latest checkpoint per thread
- `checkpoint_blobs` — serialised state (the messages list lives here), keyed by `(thread_id, checkpoint_id)`
- `checkpoint_writes` — pending mid-node writes for crash recovery

### LangSmith tracing

`_configure_langsmith()` in `app/main.py` sets `LANGCHAIN_TRACING_V2` and `LANGSMITH_TRACING` env vars at startup from `settings`. Each `ainvoke` creates one LangSmith trace. Traces for the same session are grouped in the **Threads** tab (not the Traces tab) via `metadata: {session_id}` in `RunnableConfig`. The `config` is also forwarded to `_llm.invoke()` inside `_agent_node` so child spans inherit it.

### Key design boundaries

- **`app/config.py`** — single `Settings` object (pydantic-settings); all env vars go here. `DATABASE_URL = ""` means fall back to `InMemorySaver`. `extra = "ignore"` allows extra shell vars without breaking startup.
- **`app/db.py`** — `open_pool` / `close_pool` helpers for the psycopg3 async connection pool. Pool uses `autocommit=True` (required for `CREATE INDEX CONCURRENTLY` in `setup()`) and `dict_row` row factory.
- **`app/models.py`** — all API boundary types. `FinanceResponse(answer, disclaimer, tool_used)` is built by `run_agent()` after graph completion — it is never stored in LangGraph state (which would cause msgpack serialisation warnings on checkpoint restore). `ChatResponse` mirrors its fields and is returned by the chat endpoint.
- **`app/prompts/templates.py`** — all prompt constants in one place. `AGENT_SYSTEM_PROMPT` is prepended to every LLM call by `_agent_node`. `AGENT_DISCLAIMER` is the inline string attached as the `disclaimer` field on every `FinanceResponse`. `INJECTION_JUDGE_PROMPT` is the few-shot `ChatPromptTemplate` used by the LLM injection judge — its system message **must contain the word "json"** (Deepseek's `json_object` mode rejects requests without it).
- **`app/agents/adaptive_router.py`** — module-level `_graph` and `_llm` are both set by `init_graph(checkpointer)`. `_agent_node` is a module-level function (not a closure) that references `_llm` directly. `_make_invoke_args` builds the message list and `RunnableConfig` for session vs. non-session calls. `_parse_result` walks the completed message list to extract answer, last tool name, and usage. `run_agent` is 3 lines. **The `AGENT_SYSTEM_PROMPT` must explicitly name each tool and when to call it** — `bind_tools` only makes tools available; the LLM will self-answer unless the prompt instructs otherwise.
- **`app/security/input_guard.py`** — `InputGuard.check()` runs three steps in order: (1) fast regex pre-filter against 12 injection patterns, (2) Deepseek LLM judge via `with_structured_output(InjectionVerdict, method="json_mode")` — fails open on exception so the regex layer already provides a safety net, (3) Presidio PII redaction. Always use `method="json_mode"` when calling Deepseek's `with_structured_output` — it does not support the default strict JSON-schema mode.
- **`app/components/retriever.py`** — `PineconeRetriever` stub; implement `retrieve()` and `add_documents()` here before wiring into the RAG pipeline.
- **`app/services/rag_pipeline.py`** — intended orchestrator: retriever → context assembly → LLM. Not yet wired into `/chat`.

### Deepseek API compatibility notes

Deepseek's OpenAI-compatible endpoint has two constraints not present in the real OpenAI API:

1. **No strict JSON schema mode**: `with_structured_output(Model)` defaults to function-calling / JSON-schema strict mode, which Deepseek rejects. Always pass `method="json_mode"` instead — this sends `response_format: {"type": "json_object"}`.
2. **`json_object` mode requires "json" in the prompt**: If `response_format: {"type": "json_object"}` is active but the prompt contains no occurrence of the word "json", Deepseek returns a 400 error. Ensure the system message explicitly says "Respond with a JSON object" or similar.

### What is and isn't implemented

| Module | Status |
|---|---|
| `POST /chat` | Working — LangGraph agent calls Deepseek, multi-turn memory via checkpointer |
| `GET /health` | Working |
| `POST /feedback` | Stub — always returns `recorded: true` |
| Conversation memory | Working — Postgres (`AsyncPostgresSaver`) with `InMemorySaver` fallback |
| LangSmith tracing | Working — traces grouped by `session_id` in Threads tab |
| Tools | Working — `get_quote`, `budget_calc`, `categorise_expense` wired via `ToolNode` + `tools_condition`; `handle_tool_errors=True` so `ToolException` is returned to the agent gracefully |
| Structured output | Working — `FinanceResponse(answer, disclaimer, tool_used)` built in `run_agent()` post-invocation, not stored in graph state |
| Security (InputGuard) | Working — regex injection filter + Deepseek LLM judge + Presidio PII redaction |
| Security (OutputFilter) | Stub — `raise NotImplementedError` |
| RAG pipeline | Stub — retriever, cache all `raise NotImplementedError` |
| Observability | Stub — cost tracker, feedback store all `raise NotImplementedError` |
| Frontend | Working — chat UI, session management, sends only latest message per turn; displays tool badge and disclaimer footer per assistant message |

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
- When testing `@tool` functions via `.func` (bypassing Pydantic), do **not** add `isinstance` guards in the function body to satisfy those tests. Pydantic rejects invalid types at the tool boundary before the function body is ever reached — the scenario cannot happen in production. Delete the test instead of adding unreachable defensive code.
- When mocking `with_structured_output` chains, stub `.with_structured_output.return_value.ainvoke` — not `.ainvoke` on the LLM mock directly, since `with_structured_output` returns a new runnable.
