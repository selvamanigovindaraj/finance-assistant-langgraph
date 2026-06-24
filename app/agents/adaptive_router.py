from __future__ import annotations

import uuid
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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

_SYSTEM_PROMPT = (
    "You are a knowledgeable financial assistant. "
    "You have access to three tools:\n"
    "  - get_quote: fetch a live stock price — always call this for any stock/ticker question.\n"
    "  - budget_calc: compute surplus, savings rate, and breakdown — "
    "always call this for any budget or income/expense question.\n"
    "  - categorise_expense: classify an expense — "
    "always call this for any expense categorisation question.\n"
    "Never perform these calculations or lookups yourself. "
    "For all other questions, answer clearly and concisely. "
    "If you are unsure, say so — do not fabricate facts."
)

_TOOLS = [get_quote, budget_calc, categorise_expense]
_DISCLAIMER = (
    "\n\n⚠️ This is for informational purposes only and does not constitute financial advice."
)

_graph: CompiledStateGraph[Any, Any, Any] | None = None


def _guardrail_out(state: MessagesState) -> dict[str, list[BaseMessage]]:
    last = cast(AIMessage, state["messages"][-1])
    raw = last.content
    safe_content = raw if isinstance(raw, str) else str(raw)
    disclaimed = AIMessage(
        id=last.id,
        content=safe_content + _DISCLAIMER,
        usage_metadata=last.usage_metadata,
    )
    return {"messages": [disclaimed]}


def _build_graph(checkpointer: BaseCheckpointSaver[Any]) -> CompiledStateGraph[Any, Any, Any]:
    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=SecretStr(settings.DEEPSEEK_API_KEY),
        base_url=settings.DEEPSEEK_ENDPOINT,
    ).bind_tools(_TOOLS)

    def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, list[BaseMessage]]:
        sys_msg: BaseMessage = SystemMessage(content=_SYSTEM_PROMPT)
        messages: list[BaseMessage] = [sys_msg] + cast(list[BaseMessage], state["messages"])
        response = llm.invoke(messages, config)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(_TOOLS, handle_tool_errors=True))
    graph.add_node("guardrail_out", _guardrail_out)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "guardrail_out"})
    graph.add_edge("tools", "agent")
    graph.add_edge("guardrail_out", END)
    return graph.compile(checkpointer=checkpointer)


def init_graph(checkpointer: BaseCheckpointSaver[Any]) -> None:
    """Compile and register the graph; must be called once during app startup."""
    global _graph
    _graph = _build_graph(checkpointer)


def _to_lc(msg: dict[str, str]) -> BaseMessage:
    if msg["role"] == "user":
        return HumanMessage(content=msg["content"])
    return AIMessage(content=msg["content"])


async def run_agent(
    messages: list[dict[str, str]], session_id: str = ""
) -> tuple[str, dict[str, Any]]:
    """Invoke the compiled graph and return (answer_text, usage_metadata)."""
    assert _graph is not None, "init_graph() must be called before run_agent()"

    if session_id:
        lc_messages: list[BaseMessage] = [_to_lc(messages[-1])]
        config: RunnableConfig = {
            "configurable": {"thread_id": session_id},
            "metadata": {"session_id": session_id},
        }
    else:
        lc_messages = [_to_lc(m) for m in messages]
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    result = await _graph.ainvoke({"messages": lc_messages}, config)
    last: AIMessage = result["messages"][-1]
    usage: dict[str, Any] = dict(last.usage_metadata) if last.usage_metadata else {}
    content = last.content
    return content if isinstance(content, str) else str(content), usage
