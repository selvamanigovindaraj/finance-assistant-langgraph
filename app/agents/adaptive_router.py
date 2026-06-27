from __future__ import annotations

import uuid
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import MessagesState
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import SecretStr

from app.agents.tools.financial_data import budget_calc, categorise_expense, get_quote
from app.config import settings
from app.models import FinanceResponse
from app.prompts.templates import AGENT_SYSTEM_PROMPT

_TOOLS = [get_quote, budget_calc, categorise_expense]

_graph: CompiledStateGraph[Any, Any, Any] | None = None


def _build_graph(checkpointer: BaseCheckpointSaver[Any]) -> CompiledStateGraph[Any, Any, Any]:
    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=SecretStr(settings.DEEPSEEK_API_KEY),
        base_url=settings.DEEPSEEK_ENDPOINT,
        max_retries=3,
    ).bind_tools(_TOOLS)

    def _agent_node(state: MessagesState, config: RunnableConfig) -> dict[str, list[BaseMessage]]:
        messages: list[BaseMessage] = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + cast(
            list[BaseMessage], state["messages"]
        )
        return {"messages": [llm.invoke(messages, config)]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode(_TOOLS, handle_tool_errors=True))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
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
