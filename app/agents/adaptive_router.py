from __future__ import annotations

import json
import uuid
from functools import partial
from typing import Any, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr

from app.agents.tools.financial_data import budget_calc, categorise_expense, get_quote
from app.config import settings
from app.models import FinanceResponse
from app.prompts.templates import AGENT_SYSTEM_PROMPT, SUMMARIZE_SYSTEM_PROMPT

_TOOLS = [get_quote, budget_calc, categorise_expense]

_MSG_THRESHOLD = 3
_TOKEN_THRESHOLD = 1000
_CHARS_PER_TOKEN = 4  # ponytail: ~4 chars/token heuristic
_KEEP_MSGS = 4  # ponytail: keep last 4 to preserve a full tool-call round

_graph: CompiledStateGraph[Any, Any, Any] | None = None


class AgentState(MessagesState):
    """MessagesState extended with a running conversation summary."""

    summary: str


def _needs_summary(msgs: list[BaseMessage]) -> bool:
    tokens = sum(len(m.content) // _CHARS_PER_TOKEN for m in msgs if isinstance(m.content, str))
    return len(msgs) > _MSG_THRESHOLD or tokens > _TOKEN_THRESHOLD


def _agent_node(
    state: AgentState, config: RunnableConfig, *, llm: Any
) -> dict[str, list[BaseMessage]]:
    summary = state.get("summary") or ""
    sys_msgs: list[BaseMessage] = [SystemMessage(content=AGENT_SYSTEM_PROMPT)]
    if summary:
        sys_msgs.append(SystemMessage(content=f"Summary of earlier conversation: {summary}"))
    all_msgs = cast(list[BaseMessage], state["messages"])
    # Trim only the human-anchored tail; preserve leading AI context left by summariser prune.
    first_human = next((i for i, m in enumerate(all_msgs) if isinstance(m, HumanMessage)), 0)
    leading, tail = all_msgs[:first_human], all_msgs[first_human:]
    safe = trim_messages(
        tail,
        max_tokens=_TOKEN_THRESHOLD,
        token_counter="approximate",
        strategy="last",
        start_on="human",
    )
    return {"messages": [llm.invoke(sys_msgs + leading + (safe or tail), config)]}


def _as_ledger_msg(m: BaseMessage) -> BaseMessage:
    """Convert tool-role messages to HumanMessage so Deepseek accepts them without tool binding."""
    if isinstance(m, ToolMessage):
        return HumanMessage(content=f"[Tool result] {m.content}")
    if isinstance(m, AIMessage) and m.tool_calls:
        calls = "; ".join(f"{tc['name']} params={json.dumps(tc['args'])}" for tc in m.tool_calls)
        return HumanMessage(content=f"[AI called] {calls}")
    return m


async def _summarize_node(
    state: AgentState, config: RunnableConfig, *, llm_base: Any
) -> dict[str, Any]:
    existing = state.get("summary") or ""
    suffix = (
        f"Existing ledger:\n{existing}\n\nUpdate the ledger with the new turns above:"
        if existing
        else "Create an Action Ledger from the conversation above:"
    )
    all_msgs = cast(list[BaseMessage], state["messages"])
    # Convert every message to a chat-safe form (Deepseek rejects tool/tool_calls roles
    # when no tools are bound) so the ledger captures exact params and raw results.
    ledger_msgs = [_as_ledger_msg(m) for m in all_msgs]
    msgs = (
        [SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT)]
        + ledger_msgs
        + [HumanMessage(content=suffix)]
    )
    response = await llm_base.ainvoke(msgs, config)
    keep_start = max(0, len(all_msgs) - _KEEP_MSGS)
    # Don't leave a ToolMessage as the first kept message — its AIMessage(tool_calls) would be gone
    while keep_start < len(all_msgs) and isinstance(all_msgs[keep_start], ToolMessage):
        keep_start += 1
    to_delete = [RemoveMessage(id=m.id) for m in all_msgs[:keep_start] if m.id is not None]
    return {"summary": str(response.content), "messages": to_delete}


def _route_agent(state: AgentState) -> str:
    msgs = cast(list[BaseMessage], state["messages"])
    last = msgs[-1] if msgs else None
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    if _needs_summary(msgs):
        return "summarize_conversation"
    return END


def _build_graph(checkpointer: BaseCheckpointSaver[Any]) -> CompiledStateGraph[Any, Any, Any]:
    llm_base = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=SecretStr(settings.DEEPSEEK_API_KEY),
        base_url=settings.DEEPSEEK_ENDPOINT,
        max_retries=3,
    )
    llm = llm_base.bind_tools(_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", partial(_agent_node, llm=llm))
    graph.add_node("tools", ToolNode(_TOOLS, handle_tool_errors=True))
    graph.add_node("summarize_conversation", partial(_summarize_node, llm_base=llm_base))
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        _route_agent,
        {"tools": "tools", "summarize_conversation": "summarize_conversation", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("summarize_conversation", END)
    return graph.compile(checkpointer=checkpointer)


def init_graph(checkpointer: BaseCheckpointSaver[Any]) -> None:
    """Compile and register the graph; must be called once during app startup."""
    global _graph
    _graph = _build_graph(checkpointer)


def is_initialized() -> bool:
    """Return True if init_graph() has been called."""
    return _graph is not None


def _to_lc(msg: dict[str, str]) -> BaseMessage:
    if msg["role"] == "user":
        return HumanMessage(content=msg["content"])
    return AIMessage(content=msg["content"])


def _make_invoke_args(
    messages: list[dict[str, str]], session_id: str
) -> tuple[list[BaseMessage], RunnableConfig]:
    """Return (messages, config) ready for graph.ainvoke."""
    if session_id:
        return [_to_lc(messages[-1])], {
            "configurable": {"thread_id": session_id},
            "metadata": {"session_id": session_id},
        }
    return [_to_lc(m) for m in messages], {"configurable": {"thread_id": str(uuid.uuid4())}}


def _parse_result(
    all_msgs: list[BaseMessage],
) -> tuple[FinanceResponse, dict[str, Any]]:
    """Extract answer, tool_used and usage from the completed message list."""
    last_tool_name: str | None = None
    for msg in reversed(all_msgs):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            last_tool_name = msg.tool_calls[-1]["name"]
            break

    last_tool_msg = next((m for m in reversed(all_msgs) if isinstance(m, ToolMessage)), None)

    last_ai = next(
        (m for m in reversed(all_msgs) if isinstance(m, AIMessage) and not m.tool_calls),
        None,
    )
    raw = last_ai.content if last_ai else ""
    usage: dict[str, Any] = (
        dict(last_ai.usage_metadata) if last_ai and last_ai.usage_metadata else {}
    )
    if last_tool_msg is not None:
        usage["tool_output"] = str(last_tool_msg.content)
    return FinanceResponse(
        answer=raw if isinstance(raw, str) else str(raw),
        tool_used=last_tool_name,
    ), usage


async def run_agent(
    messages: list[dict[str, str]], session_id: str = ""
) -> tuple[FinanceResponse, dict[str, Any]]:
    """Invoke the compiled graph and return (FinanceResponse, usage_metadata)."""
    assert _graph is not None, "init_graph() must be called before run_agent()"
    lc_messages, config = _make_invoke_args(messages, session_id)
    result = await _graph.ainvoke({"messages": lc_messages}, config)
    return _parse_result(cast(list[BaseMessage], result["messages"]))
