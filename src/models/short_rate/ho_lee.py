from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .base import ShortRateModel, SimulationResult
from .utils import finite_diff_gradient, instantaneous_forward, piecewise_constant_vol, prepare_curve

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover
    minimize = None


@dataclass
class HoLeeModel(ShortRateModel):
    sigma: float = 0.01
    sigma_term: np.ndarray | None = None
    sigma_breakpoints: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.curve: pd.DataFrame | None = None
        self.f0_t: np.ndarray | None = None
        self.f0: np.ndarray | None = None
        self.theta: np.ndarray | None = None

    def fit_initial_curve(self, curve: pd.DataFrame) -> None:
        self.curve = prepare_curve(curve)
        t, f = instantaneous_forward(self.curve)
        dfdt = finite_diff_gradient(t, f)
        sigma_vec = self._sigma_for_grid(t)
        self.f0_t, self.f0 = t, f
        self.theta = dfdt + sigma_vec**2 * t

    def _sigma_for_grid(self, t: np.ndarray) -> np.ndarray:
        if self.sigma_term is None or self.sigma_breakpoints is None:
            return np.full_like(t, self.sigma)
        return piecewise_constant_vol(t, self.sigma_breakpoints, self.sigma_term)

    def _model_vol(self, expiry: np.ndarray) -> np.ndarray:
        if self.sigma_term is None or self.sigma_breakpoints is None:
            return np.full_like(expiry, self.sigma)
        return piecewise_constant_vol(expiry, self.sigma_breakpoints, self.sigma_term)

    def calibrate_to_options(self, market_caps_floors_or_futures: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        market = market_caps_floors_or_futures.sort_values("expiry")
        expiries = market["expiry"].to_numpy(float)
        target_vol = market["normal_vol"].to_numpy(float)
        term_dependent = bool(kwargs.get("term_dependent", False))

        if not term_dependent:
            self.sigma = float(np.sqrt(np.mean(np.maximum(target_vol, 1e-12) ** 2)))
            return {"sigma": self.sigma, "rmse": float(np.sqrt(np.mean((self._model_vol(expiries) - target_vol) ** 2)))}

        brk = kwargs.get("breakpoints")
        if brk is None:
            brk = np.unique(np.concatenate(([0.0], expiries)))
        self.sigma_breakpoints = np.asarray(brk, dtype=float)
        n = len(self.sigma_breakpoints)

        def objective(x: np.ndarray) -> float:
            self.sigma_term = np.clip(x, 1e-6, 2.0)
            err = self._model_vol(expiries) - target_vol
            return float(np.mean(err**2))

        x0 = np.full(n, np.clip(np.mean(target_vol), 1e-4, 0.5))
        if minimize is not None:
            res = minimize(objective, x0=x0, bounds=[(1e-6, 2.0)] * n, method="L-BFGS-B")
            self.sigma_term = np.clip(res.x, 1e-6, 2.0)
            rmse = float(np.sqrt(np.mean((self._model_vol(expiries) - target_vol) ** 2)))
            return {"sigma_term": self.sigma_term, "rmse": rmse, "success": bool(res.success)}

        self.sigma_term = x0
        rmse = float(np.sqrt(np.mean((self._model_vol(expiries) - target_vol) ** 2)))
        return {"sigma_term": self.sigma_term, "rmse": rmse, "success": False}

    def simulate_paths(self, n_paths: int, time_grid: np.ndarray, seed: int | None = None) -> SimulationResult:
        if self.theta is None:
            raise RuntimeError("Call fit_initial_curve before simulation.")
        rng = np.random.default_rng(seed)
        t = np.asarray(time_grid, dtype=float)
        n_steps = len(t)
        r = np.zeros((n_paths, n_steps), dtype=float)
        r[:, 0] = self.f0[0]

        theta_grid = np.interp(t, self.f0_t, self.theta)
        sigma_grid = self._sigma_for_grid(t)
        dt = np.diff(t)
        z = rng.standard_normal((n_paths, n_steps - 1))

        for i in range(n_steps - 1):
            r[:, i + 1] = r[:, i] + theta_grid[i] * dt[i] + sigma_grid[i] * np.sqrt(dt[i]) * z[:, i]

        return SimulationResult(time_grid=t, short_rates=r)

    def validate_moments(self, sim: SimulationResult) -> pd.DataFrame:
        t = sim.time_grid
        rates = sim.short_rates
        theo_mean = self.f0[0] + np.cumsum(np.interp(t[:-1], self.f0_t, self.theta) * np.diff(t))
        theo_mean = np.insert(theo_mean, 0, self.f0[0])
        sigma_grid = self._sigma_for_grid(t)
        theo_var = np.insert(np.cumsum((sigma_grid[:-1] ** 2) * np.diff(t)), 0, 0.0)
        return pd.DataFrame(
            {
                "t": t,
                "sim_mean": rates.mean(axis=0),
                "theory_mean": theo_mean,
                "sim_var": rates.var(axis=0),
                "theory_var": theo_var,
            }
        )
