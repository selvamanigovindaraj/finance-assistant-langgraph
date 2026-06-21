from __future__ import annotations

from langchain_core.documents import Document


class PineconeRetriever:
    """Semantic retriever backed by a Pinecone vector index."""

    def __init__(self, index_name: str) -> None:
        """Initialise Pinecone client and connect to the named index.

        Args:
            index_name: Name of the Pinecone index to query.
        """
        self.index_name = index_name
        self._client = None  # TODO: initialise pinecone.Pinecone client
        self._index = None   # TODO: self._client.Index(index_name)

    def retrieve(self, query: str, k: int = 6) -> list[Document]:
        """Run a semantic search and return the top-k matching documents.

        Args:
            query: Natural-language search query.
            k: Number of results to return.
        """
        raise NotImplementedError

    def add_documents(self, documents: list[Document]) -> None:
        """Embed and upsert documents into the Pinecone index.

        Args:
            documents: LangChain Document objects to index.
        """
        raise NotImplementedError
