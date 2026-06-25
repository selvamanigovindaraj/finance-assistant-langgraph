from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

import app.agents.adaptive_router as _router_mod
from app.agents.adaptive_router import init_graph, run_agent
from app.models import FinanceResponse
from app.prompts.templates import AGENT_DISCLAIMER as _DISCLAIMER_TEXT

_PATCH_LLM = "app.agents.adaptive_router.ChatOpenAI"
_PATCH_YF = "app.agents.tools.financial_data.yf.Ticker"

_VALID_YF_INFO: dict[str, Any] = {
    "regularMarketPrice": 150.0,
    "currency": "USD",
    "regularMarketTime": 1_700_000_000,
}


def _msg(role: str, content: str) -> dict[str, str]:
    return {"role": role, "content": content}


def _make_yf_ticker(info: dict[str, Any]) -> MagicMock:
    m = MagicMock()
    m.info = info
    return m


def _make_tool_call_msg(name: str, args: dict[str, Any], call_id: str = "call_001") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


@pytest.fixture(autouse=True)
def reset_graph() -> Generator[None, None, None]:
    """Isolate each test by resetting the module-level _graph before and after."""
    _router_mod._graph = None
    yield
    _router_mod._graph = None


@pytest.fixture
def mock_llm() -> MagicMock:
    m = MagicMock()
    # bind_tools is called in _build_graph; return self so the bound llm is the same mock
    m.bind_tools.return_value = m
    return m


# ─── Init guard ────────────────────────────────────────────────────────────────


async def test_run_agent_before_init_raises() -> None:
    with pytest.raises(AssertionError, match="init_graph"):
        await run_agent([_msg("user", "hello")])


# ─── Direct response (no tool call) ───────────────────────────────────────────


async def test_direct_response_returns_answer(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="Inflation is a rise in prices.")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    finance_response, _ = await run_agent([_msg("user", "What is inflation?")])

    assert finance_response.answer.startswith("Inflation is a rise in prices.")


async def test_direct_response_llm_invoked_once(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "Explain diversification.")])

    assert mock_llm.invoke.call_count == 1


# ─── Output guardrail ──────────────────────────────────────────────────────────


async def test_disclaimer_present_in_finance_response(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="Some financial insight.")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    finance_response, _ = await run_agent([_msg("user", "Tell me about bonds.")])

    assert finance_response.disclaimer == _DISCLAIMER_TEXT


async def test_disclaimer_present_after_tool_call(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        finance_response, _ = await run_agent([_msg("user", "Price of AAPL?")])

    assert finance_response.disclaimer == _DISCLAIMER_TEXT


# ─── get_quote routing ─────────────────────────────────────────────────────────


async def test_routes_to_get_quote(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is trading at $150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        finance_response, _ = await run_agent([_msg("user", "What is the price of AAPL?")])

    assert finance_response.answer.startswith("AAPL is trading at $150.")


async def test_get_quote_tool_used_populated(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is trading at $150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        finance_response, _ = await run_agent([_msg("user", "Price of AAPL?")])

    assert finance_response.tool_used == "get_quote"


async def test_get_quote_triggers_two_llm_calls(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="Done."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")])

    assert mock_llm.invoke.call_count == 2


# ─── budget_calc routing ───────────────────────────────────────────────────────


async def test_routes_to_budget_calc(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg(
            "budget_calc",
            {"income": 5000.0, "expenses": {"rent": 1500.0, "food": 500.0}},
        ),
        AIMessage(content="Your monthly surplus is $3000."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    finance_response, _ = await run_agent([_msg("user", "Analyse my budget.")])

    assert finance_response.answer.startswith("Your monthly surplus is $3000.")


async def test_budget_calc_triggers_two_llm_calls(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg(
            "budget_calc",
            {"income": 4000.0, "expenses": {"rent": 1200.0}},
        ),
        AIMessage(content="Done."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "Calculate my surplus.")])

    assert mock_llm.invoke.call_count == 2


# ─── categorise_expense routing ────────────────────────────────────────────────


async def test_routes_to_categorise_expense(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg(
            "categorise_expense",
            {"description": "Netflix subscription", "amount": 15.99},
        ),
        AIMessage(content="This is an entertainment expense."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    finance_response, _ = await run_agent([_msg("user", "Categorise my Netflix charge.")])

    assert finance_response.answer.startswith("This is an entertainment expense.")


async def test_categorise_expense_triggers_two_llm_calls(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg(
            "categorise_expense",
            {"description": "monthly rent", "amount": 1500.0},
        ),
        AIMessage(content="Done."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "What category is my rent?")])

    assert mock_llm.invoke.call_count == 2


# ─── ToolException handling ────────────────────────────────────────────────────


async def test_tool_exception_agent_still_responds(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": ""}),
        AIMessage(content="I could not retrieve a quote for that ticker."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    finance_response, _ = await run_agent([_msg("user", "Price of empty ticker?")])

    assert isinstance(finance_response.answer, str)
    assert len(finance_response.answer) > 0


async def test_tool_exception_triggers_second_llm_call(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": ""}),
        AIMessage(content="Sorry, I could not get that."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "")])

    assert mock_llm.invoke.call_count == 2


# ─── Session behaviour ─────────────────────────────────────────────────────────


async def test_with_session_id_only_last_message_reaches_llm(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent(
        [
            _msg("user", "first turn"),
            _msg("assistant", "response"),
            _msg("user", "second turn"),
        ],
        session_id="sess-abc",
    )

    # call_model prepends the system prompt, so the LLM receives:
    # [SystemMessage, HumanMessage("second turn")] = 2 messages
    messages_passed = mock_llm.invoke.call_args_list[0].args[0]
    assert len(messages_passed) == 2


async def test_without_session_id_all_messages_reach_llm(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent(
        [
            _msg("user", "first turn"),
            _msg("assistant", "response"),
            _msg("user", "second turn"),
        ],
    )

    # call_model prepends the system prompt, so the LLM receives:
    # [SystemMessage, HumanMessage, AIMessage, HumanMessage] = 4 messages
    messages_passed = mock_llm.invoke.call_args_list[0].args[0]
    assert len(messages_passed) == 4


# ─── Return shape ──────────────────────────────────────────────────────────────


async def test_returns_finance_response_and_dict_tuple(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="answer")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    result = await run_agent([_msg("user", "hi")])

    assert isinstance(result, tuple) and len(result) == 2
    finance_response, usage = result
    assert isinstance(finance_response, FinanceResponse)
    assert isinstance(usage, dict)


async def test_usage_empty_when_no_metadata(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="answer", usage_metadata=None)
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    _, usage = await run_agent([_msg("user", "hi")])

    assert usage == {}


async def test_usage_populated_when_metadata_present(mock_llm: MagicMock) -> None:
    from langchain_core.messages.ai import UsageMetadata

    mock_llm.invoke.return_value = AIMessage(
        content="answer",
        usage_metadata=UsageMetadata(input_tokens=10, output_tokens=20, total_tokens=30),
    )
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    _, usage = await run_agent([_msg("user", "hi")])

    assert usage.get("input_tokens") == 10
    assert usage.get("output_tokens") == 20
