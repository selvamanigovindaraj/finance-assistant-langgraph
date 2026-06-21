# Testing Rules

## Python (pytest)
- Test file names: `test_<module>.py` in `tests/`.
- One `pytest.fixture` per dependency; no global state between tests.
- Use `pytest-asyncio` for all async tests (`@pytest.mark.asyncio`).
- Do NOT mock the database or vector store in integration tests — use a dedicated test index.
- Assert on behaviour, not implementation (avoid asserting on internal method calls).
- Each test function has exactly one logical assertion.

## TypeScript (Vitest)
- Co-locate component tests in `src/components/__tests__/`.
- Use `@testing-library/react` for component tests; no Enzyme.
- Mock API calls at the `fetch` boundary using `vi.stubGlobal`.
- Snapshot tests are allowed only for stable, layout-only components.

## Coverage
- Aim for ≥ 80 % line coverage on `app/services/` and `app/agents/`.
- CI fails if coverage drops below the baseline in `pyproject.toml`.
