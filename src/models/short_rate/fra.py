from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import ShortRateModel


@dataclass
class FRAResult:
    pnl: np.ndarray
    fra_forward: np.ndarray
    futures_rate: np.ndarray


def _idx(time_grid: np.ndarray, t: float) -> int:
    return int(np.argmin(np.abs(time_grid - t)))


def simulate_fra_distribution(
    model: ShortRateModel,
    curve: pd.DataFrame,
    start: float,
    end: float,
    n_paths: int = 10_000,
    seed: int | None = None,
    notional: float = 1_000_000.0,
) -> FRAResult:
    model.fit_initial_curve(curve)
    tmax = max(end + 0.25, curve["t"].max())
    time_grid = np.linspace(0.0, tmax, int(12 * tmax) + 1)
    sim = model.simulate_paths(n_paths=n_paths, time_grid=time_grid, seed=seed)

    i1, i2 = _idx(time_grid, start), _idx(time_grid, end)
    tau = end - start

    short = sim.short_rates
    dt = np.diff(time_grid)
    int_to_t2 = np.sum(short[:, :i2] * dt[:i2], axis=1)
    disc_t2 = np.exp(-int_to_t2)

    l_t1_t2 = (np.exp(short[:, i1] * tau) - 1.0) / tau
    k = np.interp(start, curve["t"], curve["zero_rate"])
    fra_pv = notional * tau * (l_t1_t2 - k) * disc_t2

    return FRAResult(pnl=fra_pv, fra_forward=l_t1_t2, futures_rate=short[:, i1])


def convexity_adjustment_summary(
    model: ShortRateModel,
    curve: pd.DataFrame,
    tenors: list[tuple[float, float]],
    vol_regimes: list[float],
    n_paths: int = 20_000,
    seed: int = 123,
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for vol in vol_regimes:
        if hasattr(model, "sigma"):
            setattr(model, "sigma", vol)
        for t1, t2 in tenors:
            out = simulate_fra_distribution(model, curve, t1, t2, n_paths=n_paths, seed=seed)
            conv = float(np.mean(out.futures_rate) - np.mean(out.fra_forward))
            rows.append(
                {
                    "tenor": f"{int(t1*12)}x{int(t2*12)}",
                    "t1": t1,
                    "t2": t2,
                    "vol_regime": vol,
                    "convexity_adjustment": conv,
                    "fra_pnl_mean": float(np.mean(out.pnl)),
                    "fra_pnl_std": float(np.std(out.pnl)),
                    "fra_pnl_p05": float(np.quantile(out.pnl, 0.05)),
                    "fra_pnl_p95": float(np.quantile(out.pnl, 0.95)),
                }
            )
    return pd.DataFrame(rows)
