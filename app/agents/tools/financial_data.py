from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_stock_price(ticker: str) -> dict:
    """Fetch the latest price and basic metadata for a stock ticker.

    Args:
        ticker: Stock symbol, e.g. "AAPL".
    """
    raise NotImplementedError


@tool
def get_financial_statements(ticker: str, period: str = "annual") -> dict:
    """Retrieve income statement, balance sheet, and cash flow data.

    Args:
        ticker: Stock symbol.
        period: "annual" or "quarterly".
    """
    raise NotImplementedError


@tool
def get_market_news(query: str, limit: int = 10) -> list[dict]:
    """Fetch recent market news articles matching the query.

    Args:
        query: Topic or company name to search for.
        limit: Maximum articles to return.
    """
    raise NotImplementedError
