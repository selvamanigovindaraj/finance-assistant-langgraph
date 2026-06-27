from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import ToolException

from app.agents.tools.financial_data import get_quote

# Bypass Pydantic coercion so edge-case inputs reach the function body directly.
_fn = get_quote.func  # type: ignore[attr-defined]

_PATCH = "app.agents.tools.financial_data.yf.Ticker"

_VALID_INFO: dict[str, Any] = {
    "regularMarketPrice": 150.0,
    "currency": "USD",
    "regularMarketTime": 1_700_000_000,
}


def _make_ticker(info: dict[str, Any]) -> MagicMock:
    m = MagicMock()
    m.info = info
    return m


# ─── Input validation ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("ticker", ["", "  ", "\t", "\n", "  \t  "])
def test_empty_or_whitespace_ticker_raises(ticker: str) -> None:
    with pytest.raises(ToolException, match="non-empty string"):
        _fn(ticker=ticker)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("aapl", "AAPL"),
        (" aapl ", "AAPL"),
        ("AAPL", "AAPL"),
        (" GOOG ", "GOOG"),
        ("msft", "MSFT"),
    ],
)
def test_ticker_result_is_normalized(raw: str, normalized: str) -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker=raw)

    assert result["ticker"] == normalized


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("aapl", "AAPL"),
        (" aapl ", "AAPL"),
        ("AAPL", "AAPL"),
        (" GOOG ", "GOOG"),
        ("msft", "MSFT"),
    ],
)
def test_yfinance_called_with_normalized_ticker(raw: str, normalized: str) -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        _fn(ticker=raw)

    mock_cls.assert_called_once_with(normalized)


# ─── Price resolution ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "info",
    [
        {},
        {"regularMarketPrice": None},
        {"regularMarketPrice": None, "previousClose": None},
        {"previousClose": None},
    ],
    ids=[
        "all-absent",
        "marketPrice-None",
        "both-None",
        "previousClose-None",
    ],
)
def test_price_none_raises_tool_exception(info: dict[str, Any]) -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        with pytest.raises(ToolException, match='Unable to fetch a live price for ticker "AAPL"'):
            _fn(ticker="AAPL")


@pytest.mark.parametrize(
    ("info", "expected_price"),
    [
        ({"regularMarketPrice": 182.50, "previousClose": 175.0}, 182.50),  # market wins
        ({"regularMarketPrice": None, "previousClose": 175.0}, 175.0),  # fallback
        ({"previousClose": 175.0}, 175.0),  # only previousClose
        ({"regularMarketPrice": 0.01}, 0.01),  # tiny but valid
        ({"regularMarketPrice": 0.0}, 0.0),  # zero is valid; not treated as absent
        (
            {"regularMarketPrice": 0.0, "previousClose": 175.0},
            0.0,
        ),  # zero beats non-None previousClose
        (
            {"regularMarketPrice": None, "previousClose": 0},
            0.0,
        ),  # None falls back to previousClose=0
    ],
    ids=[
        "market-wins",
        "fallback-to-close",
        "only-close",
        "tiny-price",
        "market-zero",
        "market-zero-beats-close",
        "previousClose-zero",
    ],
)
def test_price_field_priority(info: dict[str, Any], expected_price: float) -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker({"currency": "USD", **info})
        result = _fn(ticker="AAPL")

    assert result["price"] == pytest.approx(expected_price)


def test_price_coerced_to_float() -> None:
    info = {**_VALID_INFO, "regularMarketPrice": 100}  # int in yfinance response
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        result = _fn(ticker="AAPL")

    assert isinstance(result["price"], float)


def test_non_numeric_price_string_raises_tool_exception() -> None:
    # "N/A" is truthy so passes the None check, but float("N/A") raises ValueError.
    info = {**_VALID_INFO, "regularMarketPrice": "N/A"}
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        with pytest.raises(ToolException, match='Unable to fetch a live price for ticker "AAPL"'):
            _fn(ticker="AAPL")


# ─── Currency resolution ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("info_patch", "expected_currency"),
    [
        ({}, "USD"),  # key absent
        ({"currency": None}, "USD"),  # explicit None
        ({"currency": ""}, "USD"),  # empty string
        ({"currency": "EUR"}, "EUR"),
        ({"currency": "GBP"}, "GBP"),
        ({"currency": "JPY"}, "JPY"),
    ],
    ids=["absent", "null", "empty", "EUR", "GBP", "JPY"],
)
def test_currency_resolution(info_patch: dict[str, Any], expected_currency: str) -> None:
    info: dict[str, Any] = {"regularMarketPrice": 100.0, **info_patch}
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        result = _fn(ticker="AAPL")

    assert result["currency"] == expected_currency


# ─── Timestamp parsing ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ts",
    [1_700_000_000, 1_700_000_000.75],
    ids=["int", "float"],
)
def test_numeric_timestamp_converted_to_utc_iso(ts: int | float) -> None:
    expected = datetime.fromtimestamp(int(ts), UTC).isoformat()
    info = {**_VALID_INFO, "regularMarketTime": ts}
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        result = _fn(ticker="AAPL")

    assert result["timestamp"] == expected


@pytest.mark.parametrize(
    "dt",
    [
        datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
        datetime(2024, 6, 15, 12, 0, 0),  # naive — treated as local time then converted
    ],
    ids=["aware", "naive"],
)
def test_datetime_timestamp_produces_utc_aware_iso(dt: datetime) -> None:
    info = {**_VALID_INFO, "regularMarketTime": dt}
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        result = _fn(ticker="AAPL")

    parsed = datetime.fromisoformat(result["timestamp"])
    assert parsed.utcoffset() is not None


@pytest.mark.parametrize(
    "bad_ts",
    [None, "2024-01-01T00:00:00", "not-a-date", [], {}],
    ids=["none", "iso-string", "garbage", "list", "dict"],
)
def test_invalid_timestamp_falls_back_to_now(bad_ts: Any) -> None:
    info = {**_VALID_INFO, "regularMarketTime": bad_ts}
    before = datetime.now(UTC)
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(info)
        result = _fn(ticker="AAPL")
    after = datetime.now(UTC)

    parsed = datetime.fromisoformat(result["timestamp"])
    assert before <= parsed <= after


# ─── yfinance error handling ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("bad payload"),
        ConnectionError("timeout"),
        RuntimeError("unexpected"),
        KeyError("missing key"),
    ],
    ids=["ValueError", "ConnectionError", "RuntimeError", "KeyError"],
)
def test_yfinance_exceptions_wrapped_as_tool_exception(exc: Exception) -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.side_effect = exc
        with pytest.raises(ToolException, match='Unable to fetch a live price for ticker "AAPL"'):
            _fn(ticker="AAPL")


def test_ticker_info_none_treated_as_empty_dict() -> None:
    # yfinance occasionally returns None for .info — must not crash.
    with patch(_PATCH) as mock_cls:
        m = MagicMock()
        m.info = None
        mock_cls.return_value = m
        with pytest.raises(ToolException, match="Unable to fetch a live price"):
            _fn(ticker="AAPL")


# ─── Return shape ──────────────────────────────────────────────────────────────


def test_successful_response_has_all_required_keys() -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker="AAPL")

    assert set(result.keys()) == {"ticker", "price", "currency", "timestamp"}


def test_ticker_field_is_str() -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker="AAPL")

    assert isinstance(result["ticker"], str)


def test_price_field_is_float() -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker="AAPL")

    assert isinstance(result["price"], float)


def test_currency_field_is_str() -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker="AAPL")

    assert isinstance(result["currency"], str)


def test_timestamp_field_is_str() -> None:
    with patch(_PATCH) as mock_cls:
        mock_cls.return_value = _make_ticker(_VALID_INFO)
        result = _fn(ticker="AAPL")

    assert isinstance(result["timestamp"], str)
