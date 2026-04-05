from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Literal

import pandas as pd

QuoteType = Literal["yield", "forward", "spread", "cds"]


@dataclass(slots=True)
class MarketQuote:
    timestamp: datetime
    tenor: str
    quote_type: QuoteType
    value: float
    source: str
    instrument: str
    currency: str
    unit: str
    bid_ask: float | None = None
    liquidity_score: float | None = None
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class QuoteCollection:
    quotes: list[MarketQuote]

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for q in self.quotes:
            rows.append(
                {
                    "timestamp": q.timestamp,
                    "tenor": q.tenor,
                    "quote_type": q.quote_type,
                    "value": q.value,
                    "source": q.source,
                    "instrument": q.instrument,
                    "currency": q.currency,
                    "unit": q.unit,
                    "bid_ask": q.bid_ask,
                    "liquidity_score": q.liquidity_score,
                    "quality_flags": ";".join(q.quality_flags),
                }
            )
        return pd.DataFrame(rows)


class QuoteValidationError(ValueError):
    """Raised when a quote collection fails validation checks."""


_EXPECTED_UNITS = {
    "yield": "percent",
    "forward": "points",
    "spread": "bps",
    "cds": "bps",
}


def validate_quotes(
    quotes: Iterable[MarketQuote],
    required_tenors: Iterable[str],
    stale_after_minutes: int = 60,
    now: datetime | None = None,
) -> list[MarketQuote]:
    required_set = set(required_tenors)
    now_utc = now or datetime.now(tz=timezone.utc)

    quote_list = list(quotes)
    found_tenors = {q.tenor for q in quote_list}
    missing = required_set - found_tenors
    if missing:
        raise QuoteValidationError(f"Missing required tenors: {sorted(missing)}")

    for quote in quote_list:
        age = (now_utc - quote.timestamp).total_seconds() / 60.0
        if age > stale_after_minutes:
            quote.quality_flags.append("stale")

        expected_unit = _EXPECTED_UNITS.get(quote.quote_type)
        if expected_unit and quote.unit != expected_unit:
            raise QuoteValidationError(
                f"Unit mismatch for {quote.instrument}/{quote.tenor}: "
                f"expected {expected_unit}, got {quote.unit}"
            )

        if quote.value != quote.value:  # NaN guard without extra dependency.
            quote.quality_flags.append("nan")

    return quote_list
