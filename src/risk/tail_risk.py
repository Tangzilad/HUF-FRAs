from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def _z_score(confidence: float) -> float:
    z_map = {0.90: 1.28155, 0.95: 1.64485, 0.975: 1.95996, 0.99: 2.32635}
    if confidence in z_map:
        return z_map[confidence]
    return float(np.sqrt(2.0) * np.erfinv(2 * confidence - 1))


def parametric_var(returns: pd.Series, confidence: float = 0.99) -> float:
    mu = returns.mean()
    sigma = returns.std(ddof=0)
    z = _z_score(confidence)
    return float(-(mu - z * sigma))


def historical_var(returns: pd.Series, confidence: float = 0.99) -> float:
    q = np.quantile(returns.to_numpy(), 1.0 - confidence)
    return float(-q)


def expected_shortfall(returns: pd.Series, confidence: float = 0.99, method: str = "historical") -> float:
    if method == "historical":
        cutoff = np.quantile(returns.to_numpy(), 1.0 - confidence)
        tail = returns[returns <= cutoff]
        return float(-tail.mean()) if len(tail) else 0.0
    if method == "parametric":
        mu = returns.mean()
        sigma = returns.std(ddof=0)
        z = _z_score(confidence)
        phi = np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi)
        return float(-(mu - sigma * phi / (1 - confidence)))
    raise ValueError("method must be 'historical' or 'parametric'")


def marginal_component_var_es(pnl_frame: pd.DataFrame, total_col: str = "total") -> Dict[str, pd.DataFrame]:
    """Linearized marginal/component VaR and ES for explainability."""

    components = [c for c in pnl_frame.columns if c != total_col]
    x = pnl_frame[components].to_numpy()
    total = pnl_frame[total_col].to_numpy()

    cov = np.cov(x, rowvar=False)
    total_var = np.var(total)
    beta = cov.sum(axis=1) / total_var if total_var > 1e-12 else np.zeros(len(components))

    var99 = historical_var(pd.Series(total), 0.99)
    es99 = expected_shortfall(pd.Series(total), 0.99, method="historical")

    out = pd.DataFrame({
        "component": components,
        "marginal_var": beta * var99,
        "component_var": beta * var99,
        "marginal_es": beta * es99,
        "component_es": beta * es99,
    })
    return {"decomposition": out, "portfolio_var": var99, "portfolio_es": es99}
