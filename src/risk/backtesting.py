from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def var_hit_rate_diagnostics(realized_pnl: pd.Series, var_series: pd.Series) -> Dict[str, float]:
    breaches = realized_pnl < -var_series
    n = len(realized_pnl)
    x = int(breaches.sum())
    p_hat = x / n if n else 0.0
    expected = float(var_series.name) if isinstance(var_series.name, float) else np.nan
    return {
        "observations": float(n),
        "breaches": float(x),
        "hit_rate": p_hat,
        "expected_tail_prob": expected if not np.isnan(expected) else -1.0,
    }


def scenario_plausibility_check(scenario_shocks: pd.DataFrame, historical_shocks: pd.DataFrame, quantile: float = 0.99) -> pd.DataFrame:
    common = [c for c in scenario_shocks.columns if c in historical_shocks.columns]
    rows = []
    for col in common:
        lim = historical_shocks[col].abs().quantile(quantile)
        val = scenario_shocks[col].abs().max()
        rows.append({"shock": col, "scenario_abs": val, "hist_q": lim, "plausible": bool(val <= lim * 1.25)})
    return pd.DataFrame(rows)


def constraint_binding_report(solution_df: pd.DataFrame) -> pd.DataFrame:
    report = solution_df.copy()
    report["is_binding"] = report["binding_constraints"].ne("none")
    report["rationale"] = np.where(
        report["is_binding"],
        "Constraint active; optimizer traded off variance vs carry/liquidity penalties.",
        "Interior solution; no hard constraint binding.",
    )
    return report
