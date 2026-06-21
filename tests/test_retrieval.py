from __future__ import annotations

import pytest

from app.components.retriever import PineconeRetriever


@pytest.fixture
def retriever() -> PineconeRetriever:
    return PineconeRetriever(index_name="test-index")


def test_retrieve_returns_documents(retriever: PineconeRetriever) -> None:
    """retrieve() should return a non-empty list for a known query."""
    raise NotImplementedError


def test_add_documents_upserts(retriever: PineconeRetriever) -> None:
    """add_documents() should upsert all provided documents without error."""
    raise NotImplementedError


def test_retrieve_respects_k(retriever: PineconeRetriever) -> None:
    """retrieve() should return at most k documents."""
    raise NotImplementedError
