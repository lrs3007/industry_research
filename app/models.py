from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MarketSnapshot:
    platform: str
    market_id: str
    event_id: str
    title: str
    url: str
    category: str
    probability: float
    yes_bid: float | None = None
    yes_ask: float | None = None
    volume: float = 0.0
    open_interest: float = 0.0
    liquidity: float = 0.0
    close_time: str | None = None
    observed_at: str = field(default_factory=utc_now_iso)
    raw: dict[str, Any] = field(default_factory=dict)
    change_24h: float = 0.0
    change_7d: float = 0.0

    @property
    def spread(self) -> float:
        if self.yes_bid is None or self.yes_ask is None:
            return 0.0
        return max(0.0, self.yes_ask - self.yes_bid)


@dataclass(frozen=True)
class FactorScore:
    key: str
    label: str
    score: float
    probability: float
    confidence: float
    momentum: float
    event_count: int


@dataclass(frozen=True)
class AssetImpact:
    asset: str
    score: float
    confidence: float
    contributors: list[str]

