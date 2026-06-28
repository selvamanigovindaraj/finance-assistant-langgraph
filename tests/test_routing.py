from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

import app.agents.adaptive_router as _router_mod
from app.agents.adaptive_router import init_graph, run_agent
from app.models import FinanceResponse
from app.prompts.templates import AGENT_DISCLAIMER as _DISCLAIMER_TEXT
from app.prompts.templates import SUMMARIZE_SYSTEM_PROMPT

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
    # _summarize_node uses await llm_base.ainvoke(...) — must be awaitable
    m.ainvoke = AsyncMock(return_value=AIMessage(content="Summary of conversation."))
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


# ─── Conversation summarization ───────────────────────────────────────────────


async def test_no_summarize_for_direct_response(mock_llm: MagicMock) -> None:
    mock_llm.invoke.return_value = AIMessage(content="ok")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "hi")])

    assert mock_llm.ainvoke.call_count == 0


async def test_summarize_triggered_after_tool_call(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")])

    assert mock_llm.ainvoke.call_count == 1


async def test_summarize_triggered_by_token_threshold(mock_llm: MagicMock) -> None:
    # 4100 chars // 4 = 1025 tokens > _TOKEN_THRESHOLD of 1000
    mock_llm.invoke.return_value = AIMessage(content="ok")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "x" * 4100)])

    assert mock_llm.ainvoke.call_count == 1


async def test_summary_injected_as_system_message_on_next_turn(mock_llm: MagicMock) -> None:
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
        AIMessage(content="ok"),
    ]
    mock_llm.ainvoke.return_value = AIMessage(content="User asked about AAPL price.")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")], session_id="sess-summary")
        await run_agent([_msg("user", "Thanks")], session_id="sess-summary")

    second_turn_msgs = mock_llm.invoke.call_args_list[2].args[0]
    system_contents = [m.content for m in second_turn_msgs if isinstance(m, SystemMessage)]
    assert any("Summary" in c for c in system_contents)


async def test_no_orphaned_tool_message_after_pruning(mock_llm: MagicMock) -> None:
    """Regression: pruning must not leave a ToolMessage without its tool-call AIMessage."""
    mock_llm.invoke.side_effect = [
        # Turn 1: tool call
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
        # Turn 2: direct (triggers second summarise + pruning that previously orphaned ToolMessage)
        AIMessage(content="Sure, anything else?"),
        # Turn 3: LLM must not receive an orphaned ToolMessage
        AIMessage(content="ok"),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")], session_id="sess-orphan")
        await run_agent([_msg("user", "Thanks")], session_id="sess-orphan")
        await run_agent([_msg("user", "One more thing")], session_id="sess-orphan")

    # Turn 3 invocation must not contain a ToolMessage without a preceding tool-call AIMessage
    turn3_msgs = mock_llm.invoke.call_args_list[3].args[0]
    for i, m in enumerate(turn3_msgs):
        if isinstance(m, ToolMessage):
            assert (
                i > 0 and isinstance(turn3_msgs[i - 1], AIMessage) and turn3_msgs[i - 1].tool_calls
            )


async def test_tool_result_text_preserved_in_agent_context_after_pruning(
    mock_llm: MagicMock,
) -> None:
    """Regression: AIMessage answers from tool-call turns must survive pruning.

    After Turn 2 summarisation prunes the old tool pair, state starts with the
    plain AIMessage that held the tool result text (e.g. "AAPL is $150.").
    The agent must NOT silently drop it on Turn 3 — that text is the only raw
    context available before the summary kicks in.
    """
    mock_llm.invoke.side_effect = [
        # Turn 1: tool call round
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
        # Turn 2: direct
        AIMessage(content="You're welcome."),
        # Turn 3: agent reply
        AIMessage(content="The price was $150."),
    ]
    mock_llm.ainvoke.return_value = AIMessage(content="User asked about AAPL price and got $150.")
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")], session_id="sess-ctx")
        await run_agent([_msg("user", "Thanks")], session_id="sess-ctx")
        await run_agent([_msg("user", "What was the price?")], session_id="sess-ctx")

    # Turn 3 invoke must include the AIMessage answer from Turn 1 ("AAPL is $150.")
    # After summarisation prunes [HumanA, AIMsg_tc, ToolMsg], state has [AIMsg_ans, HumanB, ...].
    # Dropping AIMsg_ans would lose the only raw evidence of the $150 figure.
    turn3_msgs = mock_llm.invoke.call_args_list[3].args[0]
    contents = [m.content for m in turn3_msgs]
    assert any("AAPL is $150." in c for c in contents)


async def test_parallel_tool_msgs_not_dropped(mock_llm: MagicMock) -> None:
    """Regression: _drop_orphaned_tool_msgs must keep all ToolMessages for parallel tool calls."""
    # Two parallel tool calls in one AIMessage → two ToolMessages in state
    two_call_ai = AIMessage(
        content="",
        tool_calls=[
            {"name": "get_quote", "args": {"ticker": "AAPL"}, "id": "c1", "type": "tool_call"},
            {"name": "get_quote", "args": {"ticker": "TSLA"}, "id": "c2", "type": "tool_call"},
        ],
    )
    mock_llm.invoke.side_effect = [two_call_ai, AIMessage(content="AAPL $150, TSLA $200.")]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        finance_response, _ = await run_agent([_msg("user", "AAPL and TSLA prices?")])

    # Both ToolMessages must have reached the second LLM call
    second_invoke_msgs = mock_llm.invoke.call_args_list[1].args[0]
    tool_msgs = [m for m in second_invoke_msgs if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 2


# ─── Action Ledger summarisation ──────────────────────────────────────────────


async def test_tool_result_included_in_summarizer_input(mock_llm: MagicMock) -> None:
    """ToolMessage content must reach the summarizer so it can record exact tool results."""
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("budget_calc", {"income": 5000.0, "expenses": {"rent": 1500.0}}),
        AIMessage(content="Your surplus is $3500."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "Analyse my budget.")])

    # The ainvoke call to the summariser must include the raw ToolMessage result text
    summarizer_msgs = mock_llm.ainvoke.call_args_list[0].args[0]
    all_content = " ".join(m.content for m in summarizer_msgs if isinstance(m.content, str))
    # The ToolMessage from budget_calc carries the JSON result — its text must be present
    assert "3500" in all_content or "surplus" in all_content.lower()


async def test_action_ledger_system_prompt_used(mock_llm: MagicMock) -> None:
    """Summariser must be called with the Action Ledger system prompt."""
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("get_quote", {"ticker": "AAPL"}),
        AIMessage(content="AAPL is $150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    with patch(_PATCH_YF, return_value=_make_yf_ticker(_VALID_YF_INFO)):
        await run_agent([_msg("user", "Price of AAPL?")])

    summarizer_msgs = mock_llm.ainvoke.call_args_list[0].args[0]
    system_msgs = [m for m in summarizer_msgs if isinstance(m, SystemMessage)]
    assert any(SUMMARIZE_SYSTEM_PROMPT in m.content for m in system_msgs)


async def test_ai_tool_call_params_included_in_summarizer_input(mock_llm: MagicMock) -> None:
    """The exact tool params from AIMessage(tool_calls) must reach the summarizer."""
    mock_llm.invoke.side_effect = [
        _make_tool_call_msg("budget_calc", {"income": 4200.0, "expenses": {"gym": 50.0}}),
        AIMessage(content="Surplus is $4150."),
    ]
    with patch(_PATCH_LLM, return_value=mock_llm):
        init_graph(InMemorySaver())

    await run_agent([_msg("user", "Budget?")])

    summarizer_msgs = mock_llm.ainvoke.call_args_list[0].args[0]
    all_content = " ".join(m.content for m in summarizer_msgs if isinstance(m.content, str))
    # The AIMessage(tool_calls) params must be visible to the summariser
    assert "4200" in all_content or "budget_calc" in all_content
