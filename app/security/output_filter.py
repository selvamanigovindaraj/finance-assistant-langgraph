from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.config import settings
from app.prompts.templates import OUTPUT_GUARD_PROMPT
from app.security.input_guard import deanonymise

logger = logging.getLogger(__name__)


class OutputGuard:
    """Restores original PII values in LLM responses using Groq."""

    def __init__(self) -> None:
        self._llm = ChatGroq(
            model=settings.GROQ_RESTORE_MODEL,
            api_key=SecretStr(settings.GROQ_API_KEY),
        )

    async def restore(self, text: str, pairs: list[tuple[Any, str]]) -> str:
        """Replace fake PII values with originals; falls back to string replace on error."""
        if not pairs:
            return text
        mapping = "\n".join(f"{item.text!r} → {original!r}" for item, original in pairs)
        try:
            result = await self._llm.ainvoke(
                OUTPUT_GUARD_PROMPT.format_messages(mapping=mapping, text=text)
            )
            return str(result.content)
        except Exception as exc:
            logger.warning("OutputGuard LLM failed; falling back to string replace: %s", exc)
            return deanonymise(text, pairs)


_instance: OutputGuard | None = None


def get_output_guard() -> OutputGuard:
    """Return the process-wide OutputGuard singleton (lazy init)."""
    global _instance
    if _instance is None:
        _instance = OutputGuard()
    return _instance
