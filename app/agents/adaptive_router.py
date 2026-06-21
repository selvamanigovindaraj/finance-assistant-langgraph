from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import MessagesState

from app.config import settings

_SYSTEM_PROMPT = (
    "You are a knowledgeable financial assistant. "
    "Answer questions clearly and concisely. "
    "If you are unsure, say so — do not fabricate facts."
)


def _build_graph() -> StateGraph:
    llm = ChatAnthropic(
        model=settings.CLAUDE_ROUTING_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
    )

    def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        messages: list[BaseMessage] = [SystemMessage(content=_SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


_graph = _build_graph()


async def run_agent(messages: list[dict[str, str]]) -> tuple[str, dict]:
    """Invoke the compiled graph and return (answer_text, usage_metadata)."""
    lc_messages: list[BaseMessage] = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        for m in messages
    ]
    result = await _graph.ainvoke({"messages": lc_messages})
    last: AIMessage = result["messages"][-1]
    usage = last.usage_metadata or {}
    return last.content, usage
