from __future__ import annotations

import random
import time
from datetime import UTC, datetime
from typing import Any

import yfinance as yf
from langchain_core.tools import ToolException, tool

_KEYWORDS: dict[str, list[str]] = {
    "housing": [
        "rent",
        "mortgage",
        "landlord",
        "lease",
        "property tax",
        "electricity",
        "gas bill",
        "water bill",
        "home insurance",
        "maintenance",
        "repair",
    ],
    "food": [
        "grocery",
        "groceries",
        "supermarket",
        "restaurant",
        "cafe",
        "coffee",
        "pizza",
        "takeout",
        "takeaway",
        "lunch",
        "dinner",
        "breakfast",
        "meal",
        "dining",
    ],
    "transport": [
        "uber",
        "lyft",
        "taxi",
        "bus",
        "train",
        "metro",
        "subway",
        "fuel",
        "petrol",
        "parking",
        "car payment",
        "flight",
        "airline",
        "transit",
        "toll",
    ],
    "entertainment": [
        "netflix",
        "spotify",
        "hulu",
        "disney",
        "cinema",
        "movie",
        "concert",
        "ticket",
        "gym",
        "fitness",
        "gaming",
        "streaming",
    ],
    "healthcare": [
        "doctor",
        "hospital",
        "pharmacy",
        "medicine",
        "prescription",
        "dental",
        "dentist",
        "vision",
        "therapy",
        "health insurance",
        "medical",
        "clinic",
    ],
    "savings": [
        "savings",
        "investment",
        "401k",
        "401(k)",
        "ira",
        "pension",
        "retirement",
        "brokerage",
        "mutual fund",
        "etf",
    ],
}


def _fetch_yf_info(symbol: str) -> dict[str, Any]:
    """Fetch yfinance ticker info; retries up to 3 times on transient OSError."""
    for attempt in range(3):
        try:
            return yf.Ticker(symbol).info or {}
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2**attempt) + random.uniform(0, 0.5))
    return {}  # ponytail: unreachable; satisfies mypy


def _keyword_classify(description: str) -> str | None:
    lower = description.lower()
    for category, keywords in _KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return None


@tool
def get_quote(ticker: str) -> dict[str, Any]:
    """Fetch the latest quote for a stock ticker."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ToolException("Ticker symbol must be a non-empty string.")

    try:
        info: dict[str, Any] = _fetch_yf_info(symbol)

        market_price = info.get("regularMarketPrice")
        price = market_price if market_price is not None else info.get("previousClose")
        currency = info.get("currency") or "USD"
        timestamp = info.get("regularMarketTime")

        if price is None:
            raise ToolException(f'Unable to fetch a live price for ticker "{symbol}".')

        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(int(timestamp), UTC).isoformat()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.astimezone(UTC).isoformat()
        else:
            timestamp = datetime.now(UTC).isoformat()

        return {
            "ticker": symbol,
            "price": float(price),
            "currency": currency,
            "timestamp": timestamp,
        }
    except ToolException:
        raise
    except Exception as exc:
        raise ToolException(f'Unable to fetch a live price for ticker "{symbol}".') from exc


@tool
def budget_calc(income: float, expenses: dict[str, float]) -> dict[str, Any]:
    """Compute monthly surplus, savings rate, and per-category expense breakdown."""
    if income <= 0:
        raise ToolException("Income must be a positive number.")
    if not expenses:
        raise ToolException("Expenses dict must not be empty.")

    total_expenses = sum(expenses.values())
    monthly_surplus = income - total_expenses
    savings_rate_pct = round((monthly_surplus / income) * 100, 2)

    breakdown: dict[str, dict[str, float]] = {
        category: {
            "amount": round(amount, 2),
            "pct_of_income": round((amount / income) * 100, 2),
        }
        for category, amount in expenses.items()
    }

    return {
        "monthly_surplus": round(monthly_surplus, 2),
        "savings_rate_pct": savings_rate_pct,
        "breakdown": breakdown,
    }


@tool
def categorise_expense(description: str, amount: float) -> dict[str, Any]:
    """Classify an expense description into a standard budget category."""
    stripped = description.strip()
    if not stripped:
        raise ToolException("Expense description must not be empty.")
    if amount < 0:
        raise ToolException("Expense amount must be non-negative.")

    category = _keyword_classify(stripped) or "other"

    return {
        "category": category,
        "description": stripped,
        "amount": round(amount, 2),
    }
