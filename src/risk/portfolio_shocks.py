from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import pandas as pd

from .scenarios.em_scenarios import EMScenario


@dataclass
class Trade:
    trade_id: str
    instrument: str
    notional: float
    tenor_bucket: str
    dv01: float = 0.0
    fx_delta: float = 0.0
    basis01: float = 0.0
    carry: float = 0.0
    hedge_overlay: bool = False


def _shock_lookup(tenor_bucket: str, scenario: EMScenario) -> Dict[str, float]:
    rate_bp = scenario.rates_bp.get(tenor_bucket, 0.0)
    basis_bp = scenario.basis_bp.get(tenor_bucket, 0.0)
    fx_spot_pct = scenario.fx_pct.get("spot", 0.0)
    return {"rate_bp": rate_bp, "basis_bp": basis_bp, "fx_spot_pct": fx_spot_pct}


def revalue_trade(trade: Trade, scenario: EMScenario) -> Dict[str, float]:
    s = _shock_lookup(trade.tenor_bucket, scenario)
    pnl_rate = trade.dv01 * s["rate_bp"]
    pnl_fx = trade.fx_delta * (s["fx_spot_pct"] / 100.0)
    pnl_basis = trade.basis01 * s["basis_bp"]
    total = pnl_rate + pnl_fx + pnl_basis + trade.carry
    return {
        "trade_id": trade.trade_id,
        "instrument": trade.instrument,
        "tenor_bucket": trade.tenor_bucket,
        "hedge_overlay": trade.hedge_overlay,
        "pnl_rate": pnl_rate,
        "pnl_fx": pnl_fx,
        "pnl_basis": pnl_basis,
        "carry": trade.carry,
        "pnl_total": total,
    }


def propagate_scenario(portfolio: Iterable[Trade], scenario: EMScenario) -> pd.DataFrame:
    """Revalue FRA, swaps, XCCY basis swaps, and FX forwards under scenario."""

    rows = [revalue_trade(tr, scenario) for tr in portfolio]
    return pd.DataFrame(rows)


def decompose_pnl(pnl_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    by_instrument = pnl_df.groupby("instrument", as_index=False)[["pnl_rate", "pnl_fx", "pnl_basis", "carry", "pnl_total"]].sum()
    by_factor_bucket = pnl_df.groupby("tenor_bucket", as_index=False)[["pnl_rate", "pnl_fx", "pnl_basis", "pnl_total"]].sum()
    by_overlay = pnl_df.groupby("hedge_overlay", as_index=False)[["pnl_total"]].sum().rename(columns={"hedge_overlay": "is_hedge_overlay"})
    return {
        "instrument": by_instrument,
        "factor_bucket": by_factor_bucket,
        "hedge_overlay": by_overlay,
    }
