from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover
    minimize = None


@dataclass
class CalibrationReport:
    params: dict[str, float]
    objective: float
    confidence_proxy: dict[str, float]
    starts: int


def _dict_to_vec(params: dict[str, float], keys: list[str]) -> np.ndarray:
    return np.array([params[k] for k in keys], dtype=float)


def _vec_to_dict(x: np.ndarray, keys: list[str]) -> dict[str, float]:
    return {k: float(v) for k, v in zip(keys, x)}


def _finite_hessian(fun: Callable[[np.ndarray], float], x: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    n = len(x)
    h = np.zeros((n, n), dtype=float)
    fx = fun(x)
    for i in range(n):
        ei = np.zeros(n)
        ei[i] = eps
        fpp = fun(x + ei)
        fmm = fun(x - ei)
        h[i, i] = (fpp - 2 * fx + fmm) / (eps**2)
        for j in range(i + 1, n):
            ej = np.zeros(n)
            ej[j] = eps
            f_xy = fun(x + ei + ej)
            f_xmy = fun(x + ei - ej)
            f_mxy = fun(x - ei + ej)
            f_mxmy = fun(x - ei - ej)
            hij = (f_xy - f_xmy - f_mxy + f_mxmy) / (4 * eps**2)
            h[i, j] = h[j, i] = hij
    return h


def calibrate_with_multistart(
    objective: Callable[[dict[str, float], pd.DataFrame], float],
    market: pd.DataFrame,
    initial_guess: dict[str, float],
    bounds: dict[str, tuple[float, float]],
    n_starts: int = 8,
    seed: int = 11,
    bootstrap_samples: int = 128,
) -> CalibrationReport:
    rng = np.random.default_rng(seed)
    keys = list(initial_guess)
    x0 = _dict_to_vec(initial_guess, keys)
    bnds = [bounds[k] for k in keys]

    def fun(x: np.ndarray) -> float:
        xx = np.array([np.clip(xi, lo, hi) for xi, (lo, hi) in zip(x, bnds)], dtype=float)
        return objective(_vec_to_dict(xx, keys), market)

    starts = [x0]
    for _ in range(max(n_starts - 1, 0)):
        starts.append(np.array([rng.uniform(lo, hi) for lo, hi in bnds], dtype=float))

    best_x = x0.copy()
    best_obj = float("inf")
    for s in starts:
        if minimize is not None:
            res = minimize(fun, x0=s, bounds=bnds, method="L-BFGS-B")
            x_hat = np.array(res.x, dtype=float)
            val = float(res.fun)
        else:
            x_hat = s
            val = fun(s)
        if val < best_obj:
            best_obj = val
            best_x = x_hat

    h = _finite_hessian(fun, best_x)
    reg = np.eye(len(keys)) * 1e-6
    cov = np.linalg.pinv(h + reg)
    stderr = np.sqrt(np.clip(np.diag(cov), 0.0, None))

    boot = []
    if bootstrap_samples > 0:
        for _ in range(bootstrap_samples):
            idx = rng.integers(0, len(market), len(market))
            m = market.iloc[idx].reset_index(drop=True)
            boot.append(objective(_vec_to_dict(best_x, keys), m))
        boot_std = float(np.std(boot))
    else:
        boot_std = float("nan")

    conf = {f"stderr_{k}": float(s) for k, s in zip(keys, stderr)}
    conf["bootstrap_objective_std"] = boot_std

    return CalibrationReport(params=_vec_to_dict(best_x, keys), objective=best_obj, confidence_proxy=conf, starts=n_starts)
