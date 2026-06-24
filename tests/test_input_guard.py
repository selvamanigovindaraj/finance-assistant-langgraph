from __future__ import annotations

import pytest

from app.models import ChatRequest, Message, Role
from app.security.input_guard import InputGuard


@pytest.fixture
def guard() -> InputGuard:
    return InputGuard()


async def test_person_redacted(guard: InputGuard) -> None:
    req = ChatRequest(messages=[Message(role=Role.user, content="My name is John Smith.")])
    result = await guard.check(req)
    assert "<PERSON>" in result.messages[0].content
    assert "John Smith" not in result.messages[0].content


async def test_email_redacted(guard: InputGuard) -> None:
    req = ChatRequest(messages=[Message(role=Role.user, content="Email me at john@example.com")])
    result = await guard.check(req)
    assert "<EMAIL_ADDRESS>" in result.messages[0].content
    assert "john@example.com" not in result.messages[0].content


async def test_phone_redacted(guard: InputGuard) -> None:
    req = ChatRequest(messages=[Message(role=Role.user, content="Call me at +1-800-555-0199")])
    result = await guard.check(req)
    assert "<PHONE_NUMBER>" in result.messages[0].content
    assert "555-0199" not in result.messages[0].content


async def test_credit_card_redacted(guard: InputGuard) -> None:
    req = ChatRequest(
        messages=[Message(role=Role.user, content="My card number is 4111111111111111")]
    )
    result = await guard.check(req)
    assert "<CREDIT_CARD>" in result.messages[0].content
    assert "4111111111111111" not in result.messages[0].content


async def test_iban_redacted(guard: InputGuard) -> None:
    req = ChatRequest(
        messages=[Message(role=Role.user, content="Transfer to IBAN: GB29NWBK60161331926819")]
    )
    result = await guard.check(req)
    assert "<IBAN_CODE>" in result.messages[0].content
    assert "GB29NWBK60161331926819" not in result.messages[0].content


async def test_non_pii_unchanged(guard: InputGuard) -> None:
    text = "What is the S&P 500 today?"
    req = ChatRequest(messages=[Message(role=Role.user, content=text)])
    result = await guard.check(req)
    assert result.messages[0].content == text


async def test_assistant_messages_untouched(guard: InputGuard) -> None:
    content = "You can reach support at help@example.com"
    req = ChatRequest(messages=[Message(role=Role.assistant, content=content)])
    result = await guard.check(req)
    assert result.messages[0].content == content


async def test_multiple_entities_in_one_message(guard: InputGuard) -> None:
    req = ChatRequest(
        messages=[
            Message(
                role=Role.user,
                content="I'm Alice Johnson and my email is alice@example.com",
            )
        ]
    )
    result = await guard.check(req)
    text = result.messages[0].content
    assert "<PERSON>" in text
    assert "<EMAIL_ADDRESS>" in text
    assert "Alice Johnson" not in text
    assert "alice@example.com" not in text


async def test_session_id_and_stream_preserved(guard: InputGuard) -> None:
    req = ChatRequest(
        messages=[Message(role=Role.user, content="Hello")],
        session_id="sess-123",
        stream=False,
    )
    result = await guard.check(req)
    assert result.session_id == "sess-123"
    assert result.stream is False
