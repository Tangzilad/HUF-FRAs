from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .core import MarketQuote, QuoteCollection, validate_quotes


def _load_quotes(
    csv_path: str | Path,
    quote_type: str,
    required_tenors: list[str],
    stale_after_minutes: int,
) -> QuoteCollection:
    df = pd.read_csv(csv_path)
    quotes: list[MarketQuote] = []
    for row in df.to_dict(orient="records"):
        quotes.append(
            MarketQuote(
                timestamp=datetime.fromisoformat(str(row["timestamp"])).astimezone(timezone.utc),
                tenor=str(row["tenor"]),
                quote_type=quote_type,
                value=float(row["value"]),
                source=str(row.get("source", "unknown")),
                instrument=str(row.get("instrument", quote_type)),
                currency=str(row.get("currency", "UNK")),
                unit=str(row["unit"]),
                bid_ask=float(row["bid_ask"]) if pd.notna(row.get("bid_ask")) else None,
                liquidity_score=float(row["liquidity_score"])
                if pd.notna(row.get("liquidity_score"))
                else None,
            )
        )

    validated = validate_quotes(
        quotes,
        required_tenors=required_tenors,
        stale_after_minutes=stale_after_minutes,
        now=datetime.now(timezone.utc),
    )
    return QuoteCollection(validated)


def load_bond_yields(csv_path: str | Path, required_tenors: list[str]) -> QuoteCollection:
    return _load_quotes(csv_path, "yield", required_tenors, stale_after_minutes=120)


def load_fx_forwards(csv_path: str | Path, required_tenors: list[str]) -> QuoteCollection:
    return _load_quotes(csv_path, "forward", required_tenors, stale_after_minutes=30)


def load_swap_spreads(csv_path: str | Path, required_tenors: list[str]) -> QuoteCollection:
    return _load_quotes(csv_path, "spread", required_tenors, stale_after_minutes=90)


def load_cds_spreads(csv_path: str | Path, required_tenors: list[str]) -> QuoteCollection:
    return _load_quotes(csv_path, "cds", required_tenors, stale_after_minutes=180)
