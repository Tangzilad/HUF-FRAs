from __future__ import annotations

import math

import numpy as np
import pandas as pd


EPS = 1e-10


def prepare_curve(curve: pd.DataFrame) -> pd.DataFrame:
    required = {"t", "zero_rate"}
    missing = required - set(curve.columns)
    if missing:
        raise ValueError(f"Curve is missing columns: {sorted(missing)}")
    out = curve[["t", "zero_rate"]].sort_values("t").copy()
    out = out[out["t"] > 0.0]
    out["discount"] = np.exp(-out["zero_rate"] * out["t"])
    return out


def finite_diff_gradient(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.gradient(y, x, edge_order=2)


def instantaneous_forward(curve: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    t = curve["t"].to_numpy(float)
    r = curve["zero_rate"].to_numpy(float)
    zr_t = r * t
    f = finite_diff_gradient(t, zr_t)
    return t, f


def piecewise_constant_vol(time_grid: np.ndarray, breakpoints: np.ndarray, levels: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(breakpoints, time_grid, side="right") - 1
    idx = np.clip(idx, 0, len(levels) - 1)
    return levels[idx]


def normal_option_price(forward: np.ndarray, strike: np.ndarray, vol: np.ndarray, expiry: np.ndarray) -> np.ndarray:
    """Vectorized Bachelier price with unit annuity."""
    std = np.maximum(vol * np.sqrt(np.maximum(expiry, EPS)), EPS)
    d = (forward - strike) / std
    pdf = np.exp(-0.5 * d**2) / np.sqrt(2.0 * np.pi)
    cdf = 0.5 * (1.0 + np.vectorize(lambda z: math.erf(z / np.sqrt(2.0)))(d))
    return (forward - strike) * cdf + std * pdf
