"""Shared helpers for formatting, adapters, and validation."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def validate_positive(label: str, value: float) -> None:
    """Raise ``ValueError`` if ``value`` is not strictly positive."""

    if value <= 0.0:
        raise ValueError(f"{label} must be positive, received {value}.")


def to_panel_dataframe(
    *,
    spot: float,
    forward: float,
    domestic_ois: float,
    foreign_ois: float,
    tenor_years: Iterable[float],
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build tenor-aligned inputs for CIP analytics from scalar controls."""

    tenor_idx = [float(t) for t in tenor_years]
    spot_series = pd.Series([spot], index=[pd.Timestamp("today").normalize()], dtype=float)
    forward_df = pd.DataFrame([[forward for _ in tenor_idx]], index=spot_series.index, columns=tenor_idx, dtype=float)
    domestic_df = pd.DataFrame(
        [[domestic_ois for _ in tenor_idx]],
        index=spot_series.index,
        columns=tenor_idx,
        dtype=float,
    )
    foreign_df = pd.DataFrame(
        [[foreign_ois for _ in tenor_idx]],
        index=spot_series.index,
        columns=tenor_idx,
        dtype=float,
    )
    return spot_series, forward_df, domestic_df, foreign_df


def format_bp(value: float) -> str:
    """Format decimal value in basis points."""

    return f"{value:,.2f} bp"
