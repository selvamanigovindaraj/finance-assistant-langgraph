# Code Style Rules

## Python
- All files begin with `from __future__ import annotations`.
- Use `TYPE_CHECKING` guards for import-time-only types.
- Prefer `pydantic` models over plain `dict` for all API boundaries.
- Format with `ruff format`; lint with `ruff check`.
- Type-annotate every function signature; no `Any` unless unavoidable.
- Docstrings: two lines maximum — summary on the first line, optional detail on the second; no multi-paragraph blocks.

## TypeScript / React
- Functional components only; no class components.
- Explicit return types on all exported functions.
- `interface` over `type` for object shapes; `type` for unions/aliases.
- Tailwind utility classes only — no inline `style` props.
- No `any`; use `unknown` and narrow explicitly.

## General
- No comments explaining *what* code does — only *why* when non-obvious.
- No emoji in source files unless the user explicitly requests them.
- Keep functions under 30 lines; extract helpers rather than nesting.
