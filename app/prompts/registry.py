from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.prompts import BasePromptTemplate


class PromptRegistry:
    """Central registry for named prompt templates."""

    def __init__(self) -> None:
        self._store: dict[str, BasePromptTemplate] = {}

    def register(self, name: str, template: BasePromptTemplate) -> None:
        """Register a prompt template under a given name."""
        raise NotImplementedError

    def get(self, name: str) -> BasePromptTemplate:
        """Retrieve a registered prompt template by name."""
        raise NotImplementedError

    def list_names(self) -> list[str]:
        """Return all registered prompt names."""
        raise NotImplementedError


registry = PromptRegistry()
