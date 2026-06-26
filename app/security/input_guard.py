from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from faker import Faker
from langchain_groq import ChatGroq
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from pydantic import SecretStr

from app.config import settings
from app.models import ChatRequest, Message, Role

logger = logging.getLogger(__name__)

_PII_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "IBAN_CODE"]

_fake = Faker()
_FAKER_OPERATORS: dict[str, OperatorConfig] = {
    "PERSON": OperatorConfig("custom", {"lambda": lambda _: _fake.name()}),
    "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": lambda _: _fake.email()}),
    "PHONE_NUMBER": OperatorConfig("custom", {"lambda": lambda _: _fake.phone_number()}),
    "CREDIT_CARD": OperatorConfig("custom", {"lambda": lambda _: _fake.credit_card_number()}),
    "IBAN_CODE": OperatorConfig("custom", {"lambda": lambda _: _fake.iban()}),
}

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"forget\s+(all\s+)?your\s+instructions",
        r"disregard\s+(your|all|previous)",
        r"you\s+are\s+now\s+",
        r"from\s+now\s+on\s+(you|act|ignore)",
        r"do\s+anything\s+now",
        r"\bdan\b",
        r"\bjailbreak\b",
        r"pretend\s+(you\s+are|to\s+be)",
        r"roleplay\s+as",
        r"act\s+as\s+if\s+you",
        r"new\s+persona",
    ]
]


class PromptInjectionError(ValueError):
    """Raised when a user message contains a known prompt-injection pattern."""


class InputGuard:
    """Validates and sanitises incoming user messages before processing."""

    def __init__(self) -> None:
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()  # type: ignore[no-untyped-call]
        self._judge = ChatGroq(
            model=settings.GROQ_GUARD_MODEL,
            api_key=SecretStr(settings.GROQ_API_KEY),
        )

    async def check(self, request: ChatRequest) -> tuple[ChatRequest, list[tuple[Any, str]]]:
        """Redact PII from user messages; return (sanitised request, [(item, original)])."""
        sanitised: list[Message] = []
        all_pairs: list[tuple[Any, str]] = []
        for msg in request.messages:
            if msg.role == Role.user:
                self._check_injection(msg.content)
                clean, pairs = await asyncio.to_thread(self._sanitise, msg.content)
                await self._check_injection_llm(clean)
                all_pairs.extend(pairs)
                sanitised.append(Message(role=msg.role, content=clean))
            else:
                sanitised.append(msg)
        return (
            ChatRequest(messages=sanitised, session_id=request.session_id, stream=request.stream),
            all_pairs,
        )

    def _analyse_multiline(self, text: str) -> list[RecognizerResult]:
        """Run spaCy NER per-line so role labels don't suppress adjacent name detection."""
        results: list[RecognizerResult] = []
        pos = 0
        for line in text.split("\n"):
            for r in self._analyzer.analyze(
                text=line.title(), entities=_PII_ENTITIES, language="en"
            ):
                results.append(
                    RecognizerResult(
                        entity_type=r.entity_type,
                        start=r.start + pos,
                        end=r.end + pos,
                        score=r.score,
                    )
                )
            pos += len(line) + 1
        return results

    def _sanitise(self, text: str) -> tuple[str, list[tuple[Any, str]]]:
        """Replace PII with faker values; return (sanitised, [(item, original)])."""
        all_results = self._analyse_multiline(text)
        sorted_results = sorted(all_results, key=lambda r: r.start, reverse=True)
        originals = [text[r.start : r.end] for r in sorted_results]
        engine_result = self._anonymizer.anonymize(
            text=text,
            analyzer_results=all_results,  # type: ignore[arg-type]
            operators=_FAKER_OPERATORS,
        )
        return engine_result.text, list(zip(engine_result.items, originals, strict=False))

    def _check_injection(self, text: str) -> None:
        """Raise PromptInjectionError if the message matches a known injection pattern."""
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                raise PromptInjectionError(f"Prompt injection detected: {pattern.pattern!r}")

    async def _check_injection_llm(self, text: str) -> None:
        """Call PromptGuard2 on Groq; raise PromptInjectionError if score ≥ 0.5."""
        try:
            result = await self._judge.ainvoke(text)
            score = float(str(result.content).strip())
        except Exception as exc:
            logger.warning("LLM injection judge failed; falling back to regex-only: %s", exc)
            return

        if score >= settings.GROQ_INJECTION_THRESHOLD:
            raise PromptInjectionError(f"PromptGuard2 detected injection (score={score:.3f})")

    def _check_length(self, _text: str) -> None:
        """Raise if the message exceeds the allowed token budget."""
        raise NotImplementedError


def deanonymise(text: str, pairs: list[tuple[Any, str]]) -> str:
    """Restore original PII values by replacing fake values with originals."""
    if not pairs:
        return text
    for item, original in sorted(pairs, key=lambda p: p[0].start):
        text = text.replace(item.text, original, 1)
    return text


_instance: InputGuard | None = None


def get_input_guard() -> InputGuard:
    """Return the process-wide InputGuard singleton (lazy init)."""
    global _instance
    if _instance is None:
        _instance = InputGuard()
    return _instance
