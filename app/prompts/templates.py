from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

RAG_SYSTEM = """You are a knowledgeable financial assistant. Answer the user's question \
using only the context provided below. If the context does not contain enough information, \
say so clearly — do not hallucinate facts.

Context:
{context}"""

RAG_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", RAG_SYSTEM),
        ("human", "{question}"),
    ]
)

ROUTER_PROMPT: PromptTemplate = PromptTemplate.from_template(
    """Classify the following user query into exactly one of these categories:
- vector_search  (question answerable from internal knowledge base)
- web_search     (requires live / recent information from the web)
- financial_data (requires real-time stock prices or financial statements)
- direct         (simple factual question answerable without tools)

Query: {query}

Respond with only the category name."""
)

CONDENSE_PROMPT: PromptTemplate = PromptTemplate.from_template(
    """Given the conversation history and a follow-up question, rewrite the \
follow-up as a standalone question.

History:
{chat_history}

Follow-up: {question}
Standalone question:"""
)
