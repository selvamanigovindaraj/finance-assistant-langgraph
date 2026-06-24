from __future__ import annotations

import asyncio

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.models import ChatRequest, Message, Role

_PII_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IBAN_CODE"]


class InputGuard:
    """Validates and sanitises incoming user messages before processing."""

    def __init__(self) -> None:
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()  # type: ignore[no-untyped-call]

    async def check(self, request: ChatRequest) -> ChatRequest:
        """Redact PII from user messages and return the sanitised request."""
        sanitised: list[Message] = []
        for msg in request.messages:
            if msg.role == Role.user:
                clean = await asyncio.to_thread(self._sanitise, msg.content)
                sanitised.append(Message(role=msg.role, content=clean))
            else:
                sanitised.append(msg)
        return ChatRequest(
            messages=sanitised,
            session_id=request.session_id,
            stream=request.stream,
        )

    def _sanitise(self, text: str) -> str:
        """Replace PII entities with typed placeholders."""
        results = self._analyzer.analyze(text=text, entities=_PII_ENTITIES, language="en")
        anonymized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=results,  # type: ignore[arg-type]
            operators={
                entity: OperatorConfig("replace", {"new_value": f"<{entity}>"})
                for entity in _PII_ENTITIES
            },
        )
        return anonymized.text

    def _check_length(self, _text: str) -> None:
        """Raise if the message exceeds the allowed token budget."""
        raise NotImplementedError

    def _check_injection(self, _text: str) -> None:
        """Raise if the message contains prompt-injection patterns."""
        raise NotImplementedError
