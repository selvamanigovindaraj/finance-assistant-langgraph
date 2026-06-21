from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    """Token counts for a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class CostSummary:
    """Aggregated cost for one request."""

    calls: list[TokenUsage] = field(default_factory=list)
    total_usd: float = 0.0


class CostTracker:
    """Tracks token usage and estimates USD cost per request."""

    def record(self, usage: TokenUsage) -> None:
        """Record token usage from a single LLM call."""
        raise NotImplementedError

    def summarise(self) -> CostSummary:
        """Return aggregated cost for all recorded calls."""
        raise NotImplementedError

    def reset(self) -> None:
        """Clear all recorded usage data."""
        raise NotImplementedError
