# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11, UV package manager |
| Agent framework | LangGraph (`StateGraph` + `MessagesState`) + LangChain |
| LLM | Deepseek via OpenAI-compatible API (`ChatOpenAI` + `DEEPSEEK_ENDPOINT`) |
| Conversation memory | `AsyncPostgresSaver` (Postgres) or `InMemorySaver` (fallback) |
| PII store | Redis (required) — per-session fake→real mapping across turns |
| Security / injection | Groq PromptGuard2 (`llama-prompt-guard-2-22m`) — LLM injection judge |
| Security / PII restore | Groq (`llama-3.1-8b-instant`) — OutputGuard restores redacted values in responses |
| Vector store | Pinecone (cloud-hosted — no local service) |
| Web search | Tavily |
| Observability | LangSmith (tracing + thread grouping) |
| Evaluation | LangSmith `aevaluate` + Deepseek LLM-as-judge — golden dataset, 5 evaluators |
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

# Evaluation (LangSmith)
make eval          # seed dataset + run full eval
make eval-seed     # only upload golden dataset to LangSmith
make eval-pii      # run only pii_detection category
make eval-injection  # run only prompt_injection category
# Or directly:
uv run python scripts/eval.py --eval-only --max-examples 5   # smoke test

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
  → app/routers/chat.py          validates ChatRequest; injects pii_store via Depends(get_pii_store)
  → InputGuard.check()           regex injection filter → Groq PromptGuard2 judge → Presidio PII redaction
                                 returns (sanitised_request, pii_pairs)
  → pii_store.merge(session_id, pii_pairs)  accumulate fake→real map in Redis for this session
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
  → OutputGuard.restore()        loads full session PII map from Redis; Groq LLM restores real values
                                 falls back to string-replace if Groq fails
  → returns FinanceResponse(answer, disclaimer, tool_used) + usage dict
```

### Conversation memory — checkpointer pattern

The graph is **not** compiled at module import. Instead:

1. `app/core/lifespan.py` `lifespan()` runs at FastAPI startup
2. Calls `init_pii_store(Redis.from_url(settings.REDIS_URL, ...))` — **crashes on startup if `REDIS_URL` is empty**; Redis is mandatory
3. Checks `settings.DATABASE_URL`: if set → opens psycopg3 pool → `AsyncPostgresSaver` → `setup()` → `init_graph(checkpointer)`; if not set → `InMemorySaver` → `init_graph(checkpointer)`
4. `_graph` starts as `None`; `is_initialized()` predicate and `assert` guard in `run_agent` prevent use before init

**Why only the last message is sent from the frontend:** `MessagesState` uses an `add_messages` reducer that *appends* — it does not replace. Sending the full history on every turn would duplicate messages on top of what the checkpointer already restored. Only the new user message is sent; the checkpointer merges it with the stored history automatically.

**LangGraph's three Postgres tables** (created by `setup()`, never touch manually):
- `checkpoints` — metadata pointer to the latest checkpoint per thread
- `checkpoint_blobs` — serialised state (the messages list lives here), keyed by `(thread_id, checkpoint_id)`
- `checkpoint_writes` — pending mid-node writes for crash recovery

### LangSmith tracing

`configure_langsmith()` in `app/core/lifespan.py` sets `LANGCHAIN_TRACING_V2` and `LANGSMITH_TRACING` env vars at startup from `settings`. It is also called directly by `scripts/eval.py` (which runs outside FastAPI). Each `ainvoke` creates one LangSmith trace. Traces for the same session are grouped in the **Threads** tab (not the Traces tab) via `metadata: {session_id}` in `RunnableConfig`. The `config` is also forwarded to `llm.invoke()` inside `_agent_node` so child spans inherit it.

### Key design boundaries

- **`app/core/lifespan.py`** — `lifespan()` is the FastAPI lifespan context manager; calls `configure_langsmith()`, `init_pii_store()`, and `init_graph()`. `configure_langsmith()` is also importable directly by `scripts/eval.py`. Redis init (`Redis.from_url(settings.REDIS_URL, decode_responses=False)`) is called unconditionally — startup crashes if `REDIS_URL` is empty (intentional).
- **`app/config.py`** — single `Settings` object (pydantic-settings); all env vars go here. `DATABASE_URL = ""` means fall back to `InMemorySaver`. `REDIS_URL = ""` defaults to empty but **startup crashes** if not set (Redis is mandatory). `GROQ_API_KEY`, `GROQ_GUARD_MODEL` (`llama-prompt-guard-2-22m`), `GROQ_RESTORE_MODEL` (`llama-3.1-8b-instant`), `GROQ_INJECTION_THRESHOLD` (default `0.5`) are all present. `extra = "ignore"` allows extra shell vars without breaking startup.
- **`app/db.py`** — `open_pool` / `close_pool` helpers for the psycopg3 async connection pool. Pool uses `autocommit=True` (required for `CREATE INDEX CONCURRENTLY` in `setup()`) and `dict_row` row factory.
- **`app/models.py`** — all API boundary types. `FinanceResponse(answer, disclaimer, tool_used)` is built by `run_agent()` after graph completion — it is never stored in LangGraph state (which would cause msgpack serialisation warnings on checkpoint restore). `ChatResponse` mirrors its fields and is returned by the chat endpoint.
- **`app/prompts/templates.py`** — all prompt constants in one place. `AGENT_SYSTEM_PROMPT` is prepended to every LLM call by `_agent_node`. `AGENT_DISCLAIMER` is the inline string attached as the `disclaimer` field on every `FinanceResponse`. `INJECTION_JUDGE_PROMPT` is the few-shot `ChatPromptTemplate` used by the LLM injection judge — its system message **must contain the word "json"** (Deepseek's `json_object` mode rejects requests without it).
- **`app/agents/adaptive_router.py`** — only `_graph` is a module-level global, set by `init_graph(checkpointer)`. `is_initialized() -> bool` is a public predicate — use this instead of accessing `_graph` directly from outside the module. `_build_graph` creates the `ChatOpenAI` LLM locally and defines `_agent_node` as a nested closure that captures it — this eliminates the need for a module-level `_llm`. `_make_invoke_args` builds the message list and `RunnableConfig` for session vs. non-session calls. `_parse_result` walks the completed message list to extract answer, last tool name, and usage. `run_agent` is 3 lines. **The `AGENT_SYSTEM_PROMPT` must explicitly name each tool and when to call it** — `bind_tools` only makes tools available; the LLM will self-answer unless the prompt instructs otherwise.
- **`app/security/input_guard.py`** — `InputGuard.check()` runs three steps in order: (1) fast regex pre-filter against 12 injection patterns, (2) Groq PromptGuard2 judge (`self._judge` — `ChatGroq(model=GROQ_GUARD_MODEL)`) — returns a numeric score string; raises `PromptInjectionError` if `score >= GROQ_INJECTION_THRESHOLD`; fails open on exception so the regex layer already provides a safety net, (3) Presidio PII redaction using Faker-generated realistic fake values (name → fake name, email → fake email, etc.). Presidio's spaCy NER only recognises PERSON entities when names are capitalised — `_sanitise` analyses `text.title()` per-line to preserve char positions. `get_input_guard()` returns the process-wide singleton — always use this instead of `InputGuard()` to avoid creating a new Groq client per call.
- **`app/security/pii_store.py`** — `PiiStore` wraps a Redis client; `merge(session_id, pairs)` writes `{fake: real}` pairs to a Redis hash (`pii:{session_id}`) with a 24h TTL; `load(session_id)` returns the full accumulated map as `dict[str, str]`. `init_pii_store(redis)` sets the process-wide singleton; `get_pii_store()` returns it with an `assert` guard. `_AnyRedis = Any` — Redis is not generic at runtime.
- **`app/security/output_filter.py`** — `OutputGuard.restore()` loads the full session PII map from Redis via `pii_store.load(session_id)` (or falls back to `current_pairs` if no session), then calls Groq (`GROQ_RESTORE_MODEL`) to rewrite the LLM response with real values restored. Falls back to `_string_replace(text, mapping)` if Groq fails. `get_output_guard()` returns the process-wide singleton.
- **`app/components/retriever.py`** — `PineconeRetriever` stub; implement `retrieve()` and `add_documents()` here before wiring into the RAG pipeline.
- **`app/services/rag_pipeline.py`** — intended orchestrator: retriever → context assembly → LLM. Not yet wired into `/chat`.

### Evaluation pipeline (`scripts/eval.py`)

Dataset: `finance-agent-golden-v3` in LangSmith — 63 examples across 6 categories: `budgeting`, `expense_categorisation`, `stock_quote`, `financial_literacy`, `pii_detection`, `prompt_injection`.

`_agent_target` is the eval target — runs `InputGuard.check()` then `run_agent()`, returns:

```python
{"answer": ..., "tool_used": ..., "tool_output": ..., "usage": ...}
```

- `PromptInjectionError` is caught explicitly → returns `{"answer": "I'm sorry, but I can't process that request.", "blocked_by": ...}`
- `tool_output` is the raw `ToolMessage` content (JSON string for successful tools, error string for `ToolException`)

Evaluators:

- `eval_tool_match` — exact match on `tool_used` vs `expected_tool` (None = no tool expected)
- `eval_no_pii_leak` — PII category only; regex-checks that original PII values don't appear verbatim in the answer
- `eval_injection_refused` — injection category only; checks `tool_used is None` and refusal signal in answer
- `eval_no_hallucination` — tool-calling examples only; deterministic check that the answer reflects actual tool output: category name for `categorise_expense`, surplus integer for `budget_calc`, ticker symbol for `get_quote`; skips (score=None) if no tool output or tool raised an error
- `eval_correctness` / `eval_relevance` — Deepseek LLM-as-judge using `json_object` mode

`expected_masked_entities` in the golden dataset lists entity types (e.g. `["PERSON", "EMAIL_ADDRESS"]`) that were present in the input — used by `eval_no_pii_leak` to extract the actual values to check for.

**Key gotcha**: `PromptInjectionError` must be caught *before* the generic `except Exception` handler in `_agent_target`, otherwise the raw exception string (containing the regex pattern) is returned as the answer and `eval_injection_refused` will always score 0.

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
| Tools | Working — `get_quote`, `budget_calc`, `categorise_expense` wired via `ToolNode` + `tools_condition`; `handle_tool_errors=True` so `ToolException` is returned to the agent gracefully. `get_quote` error message: `'Unable to fetch a live price for ticker "{symbol}".'`. `categorise_expense` keywords include `"fitness"` → entertainment and `"401(k)"` → savings. |
| Structured output | Working — `FinanceResponse(answer, disclaimer, tool_used)` built in `run_agent()` post-invocation, not stored in graph state |
| PII store (Redis) | Working — `PiiStore` accumulates fake→real maps per session in Redis; mandatory at startup |
| Security (InputGuard) | Working — regex injection filter + Groq PromptGuard2 judge + Presidio PII redaction (Faker-based fake substitution) |
| Security (OutputGuard) | Working — `OutputGuard.restore()` reloads full session PII map from Redis; Groq LLM restores real values; string-replace fallback |
| RAG pipeline | Stub — retriever, cache all `raise NotImplementedError` |
| Observability | Stub — cost tracker, feedback store all `raise NotImplementedError` |
| Frontend | Working — chat UI, session management, sends only latest message per turn; displays tool badge and disclaimer footer per assistant message |
| Evaluation | Working — `scripts/eval.py` seeds `data/golden_dataset.json` (63 examples, 6 categories) to LangSmith dataset `finance-agent-golden-v3` and runs 5 evaluators: `eval_tool_match`, `eval_no_pii_leak`, `eval_injection_refused`, `eval_no_hallucination`, Deepseek LLM-as-judge correctness + relevance. `--category` flag for targeted runs. |

## Coding principles

These principles apply to all generated code, in every language:

- **KISS** — Start with the simplest solution that works. Add complexity only when a concrete requirement demands it, not in anticipation of one.
- **DRY** — Extract repeated logic into a single authoritative place. Every piece of knowledge should have one representation.
- **YAGNI** — Build only what the current task requires. Do not add hooks, abstractions, or configuration points for hypothetical future needs.
- **Separation of Concerns** — Each module, class, or function should have one reason to change. Keep I/O, business logic, and presentation in separate layers so each can be tested and changed independently.
- **Law of Demeter** — A unit should interact only with its immediate collaborators. Avoid chaining through internal structure (`a.b.c.do()`); pass what is needed or expose a higher-level method instead.

## Workflow skills

- **TDD** — Write the failing test first, then write the minimum code to make it pass. Never touch production code without a corresponding test written beforehand. If a task has no clear testable unit, ask before proceeding.
- **ponytail** — Run `/ponytail` before planning and before writing any code. It enforces the laziest solution that actually works: question whether the task needs to exist at all, reach for stdlib before custom code, one line before fifty. If the output suggests a simpler path, take it before proceeding.

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
