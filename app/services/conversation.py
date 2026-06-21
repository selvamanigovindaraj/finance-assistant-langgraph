from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Message


class ConversationMemory:
    """Manages per-session conversation history with optional summarisation."""

    def __init__(self, session_id: str, max_turns: int = 20) -> None:
        self.session_id = session_id
        self.max_turns = max_turns

    def add_message(self, message: Message) -> None:
        """Append a message to the session history."""
        raise NotImplementedError

    def get_history(self) -> list[Message]:
        """Return the full conversation history for this session."""
        raise NotImplementedError

    async def summarise_if_needed(self) -> None:
        """Compress old turns into a summary when history exceeds max_turns."""
        raise NotImplementedError

    def clear(self) -> None:
        """Wipe the conversation history for this session."""
        raise NotImplementedError
