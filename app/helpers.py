from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from src.analytics.cip_premium import compute_raw_cip_deviation
from src.curves.cross_currency import build_discount_curve
from src.models.short_rate.fra import simulate_fra_distribution
from src.models.short_rate.ho_lee import HoLeeModel
from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import em_scenario_library


def build_curve_table(payload: Dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for ccy, quote_map in payload["ois_by_ccy"].items():
        discount_curve = build_discount_curve(quote_map)
        for tenor, df in sorted(discount_curve.items()):
            rows.append({"currency": ccy, "tenor_years": float(tenor), "discount_factor": float(df)})
    return pd.DataFrame(rows)


def run_pricing_engine(payload: Dict[str, Any], seed: int = 7) -> pd.DataFrame:
    curve = pd.DataFrame(payload["short_rate_curve"])
    out = simulate_fra_distribution(HoLeeModel(sigma=0.01), curve, start=0.5, end=1.0, n_paths=400, seed=seed)
    return pd.DataFrame(
        [
            {
                "n_paths": int(out.pnl.size),
                "fra_pnl_mean": float(np.mean(out.pnl)),
                "fra_pnl_std": float(np.std(out.pnl)),
                "fra_forward_mean": float(np.mean(out.fra_forward)),
                "futures_rate_mean": float(np.mean(out.futures_rate)),
            }
        ]
    )


def run_risk_engine(payload: Dict[str, Any]) -> dict[str, pd.DataFrame]:
    scenario = em_scenario_library()[0]
    portfolio = [Trade(**row) for row in payload["portfolio"]]
    pnl = propagate_scenario(portfolio, scenario)
    parts = decompose_pnl(pnl)
    return {"trade_pnl": pnl, **parts}


def run_cip_path(payload: Dict[str, Any]) -> pd.DataFrame:
    cip = payload["cip"]
    index = pd.to_datetime(cip["dates"])
    tenors = [float(x) for x in cip["tenors"]]

    spot = pd.Series(cip["spot"], index=index)
    domestic_ois = pd.DataFrame(cip["domestic_ois"], index=index, columns=tenors)
    foreign_ois = pd.DataFrame(cip["foreign_ois"], index=index, columns=tenors)

    forwards = pd.DataFrame(index=index, columns=tenors, dtype=float)
    for t in tenors:
        forwards[t] = spot * (1 + domestic_ois[t] * t) / (1 + foreign_ois[t] * t)

    raw = compute_raw_cip_deviation(spot, forwards, domestic_ois, foreign_ois)
    raw_bp = raw["raw_basis_bp"]
    return raw_bp.reset_index(names="date").melt(id_vars="date", var_name="tenor_years", value_name="raw_basis_bp")
