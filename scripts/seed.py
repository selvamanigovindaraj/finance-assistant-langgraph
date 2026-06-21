from __future__ import annotations

"""Seed script: load raw documents from data/raw/ and upsert into Pinecone."""

import asyncio
from pathlib import Path


async def load_documents(raw_dir: Path) -> list:
    """Load and parse all documents from the raw data directory."""
    raise NotImplementedError


async def seed(index_name: str | None = None) -> None:
    """Run the full seed pipeline: load → embed → upsert."""
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(seed())
