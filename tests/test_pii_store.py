from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.security.pii_store import PiiStore, get_pii_store, init_pii_store


def _fake_item(text: str) -> MagicMock:
    """Minimal AnonymizerResult stub with just the .text attribute."""
    item = MagicMock()
    item.text = text
    return item


def _redis(hgetall_return: dict[bytes, bytes] | None = None) -> MagicMock:
    r = MagicMock()
    r.hset = AsyncMock()
    r.expire = AsyncMock()
    r.hgetall = AsyncMock(return_value=hgetall_return or {})
    return r


@pytest.fixture
def store() -> PiiStore:
    return PiiStore(_redis())


# ---------------------------------------------------------------------------
# merge()
# ---------------------------------------------------------------------------


async def test_merge_writes_hash_and_sets_ttl(store: PiiStore) -> None:
    pairs = [(_fake_item("Emily Rodriguez"), "Selva")]
    await store.merge("sess-1", pairs)

    store._redis.hset.assert_awaited_once_with("pii:sess-1", mapping={"Emily Rodriguez": "Selva"})
    store._redis.expire.assert_awaited_once_with("pii:sess-1", 86_400)


async def test_merge_multiple_pairs(store: PiiStore) -> None:
    pairs = [
        (_fake_item("Emily Rodriguez"), "Selva"),
        (_fake_item("tmiller@example.net"), "selva@gmail.com"),
    ]
    await store.merge("sess-1", pairs)

    store._redis.hset.assert_awaited_once_with(
        "pii:sess-1",
        mapping={"Emily Rodriguez": "Selva", "tmiller@example.net": "selva@gmail.com"},
    )


async def test_merge_accumulates_across_turns() -> None:
    r = _redis()
    s = PiiStore(r)

    await s.merge("sess-1", [(_fake_item("Emily Rodriguez"), "Selva")])
    await s.merge("sess-1", [(_fake_item("tmiller@example.net"), "selva@gmail.com")])

    assert r.hset.await_count == 2
    assert r.expire.await_count == 2


async def test_merge_skips_empty_pairs(store: PiiStore) -> None:
    await store.merge("sess-1", [])

    store._redis.hset.assert_not_awaited()
    store._redis.expire.assert_not_awaited()


async def test_merge_skips_empty_session_id(store: PiiStore) -> None:
    pairs = [(_fake_item("Emily Rodriguez"), "Selva")]
    await store.merge("", pairs)

    store._redis.hset.assert_not_awaited()


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------


async def test_load_returns_decoded_mapping() -> None:
    r = _redis(
        hgetall_return={b"Emily Rodriguez": b"Selva", b"tmiller@example.net": b"selva@gmail.com"}
    )
    s = PiiStore(r)

    result = await s.load("sess-1")

    assert result == {"Emily Rodriguez": "Selva", "tmiller@example.net": "selva@gmail.com"}
    r.hgetall.assert_awaited_once_with("pii:sess-1")


async def test_load_returns_empty_for_unknown_session() -> None:
    result = await PiiStore(_redis()).load("unknown-sess")

    assert result == {}


async def test_load_returns_empty_for_blank_session_id(store: PiiStore) -> None:
    result = await store.load("")

    assert result == {}
    store._redis.hgetall.assert_not_awaited()


async def test_load_uses_correct_key_prefix() -> None:
    r = _redis()
    s = PiiStore(r)

    await s.load("abc-123")

    r.hgetall.assert_awaited_once_with("pii:abc-123")


# ---------------------------------------------------------------------------
# init_pii_store / get_pii_store
# ---------------------------------------------------------------------------


def test_init_and_get_pii_store() -> None:
    r = _redis()
    init_pii_store(r)
    store = get_pii_store()

    assert isinstance(store, PiiStore)
    assert store._redis is r


def test_get_pii_store_raises_before_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.security.pii_store._instance", None)

    with pytest.raises(AssertionError, match="init_pii_store"):
        get_pii_store()
