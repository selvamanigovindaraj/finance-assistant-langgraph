from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.tools import tool


@tool
def vector_search(query: str, k: int = 6) -> list[Document]:
    """Search the Pinecone vector store for semantically similar documents.

    Args:
        query: Natural-language search query.
        k: Number of results to return.
    """
    raise NotImplementedError
