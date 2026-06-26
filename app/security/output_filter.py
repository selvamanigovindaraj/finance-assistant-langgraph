from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.config import settings
from app.prompts.templates import OUTPUT_GUARD_PROMPT
from app.security.pii_store import PiiStore

logger = logging.getLogger(__name__)


class OutputGuard:
    """Restores original PII values in LLM responses using Groq."""

    def __init__(self) -> None:
        self._llm = ChatGroq(
            model=settings.GROQ_RESTORE_MODEL,
            api_key=SecretStr(settings.GROQ_API_KEY),
        )

    async def restore(
        self,
        text: str,
        session_id: str,
        pii_store: PiiStore,
        current_pairs: list[tuple[Any, str]],
    ) -> str:
        """Restore PII using the full session map (all turns) from Redis."""
        mapping = (
            await pii_store.load(session_id)
            if session_id
            else {item.text: original for item, original in current_pairs}
        )

        if not mapping:
            return text

        mapping_str = "\n".join(f"{fake!r} → {real!r}" for fake, real in mapping.items())
        try:
            result = await self._llm.ainvoke(
                OUTPUT_GUARD_PROMPT.format_messages(mapping=mapping_str, text=text)
            )
            return str(result.content)
        except Exception as exc:
            logger.warning("OutputGuard LLM failed; falling back to string replace: %s", exc)
            return _string_replace(text, mapping)


def _string_replace(text: str, mapping: dict[str, str]) -> str:
    for fake, real in mapping.items():
        text = text.replace(fake, real, 1)
    return text


_instance: OutputGuard | None = None


def get_output_guard() -> OutputGuard:
    """Return the process-wide OutputGuard singleton (lazy init)."""
    global _instance
    if _instance is None:
        _instance = OutputGuard()
    return _instance
