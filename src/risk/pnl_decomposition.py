"""Level / slope / curvature P&L decomposition.

Decomposes scenario-driven P&L into three yield-curve components:

- **Level (parallel shift)**: average shock across tenor buckets.
- **Slope (steepening/flattening)**: difference between long- and short-term
  shocks, capturing the first-order tilt.
- **Curvature (butterfly/skew)**: second-difference across short, mid, and long
  maturities — isolates mid-segment moves relative to wings.

The module reuses :class:`Trade` from :mod:`src.risk.portfolio_shocks` and
:class:`EMScenario` from :mod:`src.risk.scenarios.em_scenarios`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from .portfolio_shocks import Trade
from .scenarios.em_scenarios import EMScenario

# Canonical bucket ordering used for slope/curvature calculation.
BUCKET_ORDER: list[str] = ["front", "belly", "back"]


@dataclass(frozen=True)
class CurveShockComponents:
    """Shock decomposition into level, slope, and curvature terms (all in bp)."""

    level_bp: float
    slope_bp: float
    curvature_bp: float


@dataclass(frozen=True)
class LSCDecomposition:
    """Full level/slope/curvature P&L result for one trade."""

    trade_id: str
    instrument: str
    tenor_bucket: str
    dv01: float
    pnl_level: float
    pnl_slope: float
    pnl_curvature: float
    pnl_total: float


def decompose_rate_shocks(scenario: EMScenario) -> CurveShockComponents:
    """Extract level, slope, and curvature from a scenario's rate shocks.

    Level   = mean(front, belly, back)
    Slope   = back - front    (positive => steepening)
    Curvature = front + back - 2*belly  (positive => concave / butterfly wings up)
    """
    shocks = {b: scenario.rates_bp.get(b, 0.0) for b in BUCKET_ORDER}
    front, belly, back = shocks["front"], shocks["belly"], shocks["back"]

    level = (front + belly + back) / 3.0
    slope = back - front
    curvature = front + back - 2.0 * belly

    return CurveShockComponents(level_bp=level, slope_bp=slope, curvature_bp=curvature)


def _bucket_loadings(tenor_bucket: str) -> Dict[str, float]:
    """Return factor loadings for a given tenor bucket.

    Each bucket maps to weights on the three factors (level, slope, curvature)
    so that: shock(bucket) = level + w_slope * slope + w_curv * curvature.

    Derivation — let f, b, k = front/belly/back shocks:
      level = (f+b+k)/3
      slope = k - f
      curvature = f + k - 2b

    Inversion (exact, verified algebraically):
      f = level - slope/2 + curvature/6
      b = level           - curvature/3
      k = level + slope/2 + curvature/6

    Each bucket's shock is reconstructed from these loadings:
      front:  level_weight=1, slope_weight=-1/2, curvature_weight=+1/6
      belly:  level_weight=1, slope_weight= 0,   curvature_weight=-1/3
      back:   level_weight=1, slope_weight=+1/2, curvature_weight=+1/6
    """
    loadings = {
        "front": {"level": 1.0, "slope": -1.0 / 2.0, "curvature": 1.0 / 6.0},
        "belly": {"level": 1.0, "slope": 0.0, "curvature": -1.0 / 3.0},
        "back":  {"level": 1.0, "slope": 1.0 / 2.0, "curvature": 1.0 / 6.0},
    }
    return loadings.get(tenor_bucket, loadings["belly"])


def decompose_trade_lsc(trade: Trade, scenario: EMScenario) -> LSCDecomposition:
    """Decompose a single trade's rate P&L into level, slope, curvature."""
    components = decompose_rate_shocks(scenario)
    w = _bucket_loadings(trade.tenor_bucket)

    # P&L = DV01 * shock_bp, where shock is reconstructed from components.
    pnl_level = trade.dv01 * components.level_bp * w["level"]
    pnl_slope = trade.dv01 * components.slope_bp * w["slope"]
    pnl_curvature = trade.dv01 * components.curvature_bp * w["curvature"]
    pnl_total = pnl_level + pnl_slope + pnl_curvature

    return LSCDecomposition(
        trade_id=trade.trade_id,
        instrument=trade.instrument,
        tenor_bucket=trade.tenor_bucket,
        dv01=trade.dv01,
        pnl_level=pnl_level,
        pnl_slope=pnl_slope,
        pnl_curvature=pnl_curvature,
        pnl_total=pnl_total,
    )


def decompose_portfolio_lsc(
    portfolio: Iterable[Trade],
    scenario: EMScenario,
) -> pd.DataFrame:
    """Decompose entire portfolio into level/slope/curvature P&L.

    Returns a DataFrame with columns:
        trade_id, instrument, tenor_bucket, dv01,
        pnl_level, pnl_slope, pnl_curvature, pnl_total
    """
    rows = [decompose_trade_lsc(t, scenario) for t in portfolio]
    if not rows:
        return pd.DataFrame(columns=[
            "trade_id", "instrument", "tenor_bucket", "dv01",
            "pnl_level", "pnl_slope", "pnl_curvature", "pnl_total",
        ])
    return pd.DataFrame([
        {
            "trade_id": r.trade_id,
            "instrument": r.instrument,
            "tenor_bucket": r.tenor_bucket,
            "dv01": r.dv01,
            "pnl_level": r.pnl_level,
            "pnl_slope": r.pnl_slope,
            "pnl_curvature": r.pnl_curvature,
            "pnl_total": r.pnl_total,
        }
        for r in rows
    ])


def aggregate_lsc(lsc_df: pd.DataFrame) -> pd.DataFrame:
    """Summarise level/slope/curvature contributions across the portfolio.

    Returns a 3-row DataFrame (one per factor) with columns:
        factor, pnl, dv01_contribution, pct_of_total
    """
    if lsc_df.empty:
        return pd.DataFrame(columns=["factor", "pnl", "dv01_contribution", "pct_of_total"])

    total = lsc_df["pnl_total"].sum()
    dv01_total = lsc_df["dv01"].sum()
    gross = abs(lsc_df["pnl_level"].sum()) + abs(lsc_df["pnl_slope"].sum()) + abs(lsc_df["pnl_curvature"].sum())
    if gross < 1e-12:
        gross = 1.0

    rows = []
    for factor, col in [("Level", "pnl_level"), ("Slope", "pnl_slope"), ("Curvature", "pnl_curvature")]:
        val = lsc_df[col].sum()
        rows.append({
            "factor": factor,
            "pnl": val,
            "dv01_contribution": dv01_total * (val / total) if abs(total) > 1e-12 else 0.0,
            "pct_of_total": abs(val) / gross * 100,
        })
    return pd.DataFrame(rows)
