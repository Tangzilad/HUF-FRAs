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
class HullWhite1FModel(ShortRateModel):
    a: float = 0.15
    sigma: float = 0.01
    sigma_term: np.ndarray | None = None
    sigma_breakpoints: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.curve: pd.DataFrame | None = None
        self.f0_t: np.ndarray | None = None
        self.f0: np.ndarray | None = None
        self.theta: np.ndarray | None = None

    def _sigma_for_grid(self, t: np.ndarray) -> np.ndarray:
        if self.sigma_term is None or self.sigma_breakpoints is None:
            return np.full_like(t, self.sigma)
        return piecewise_constant_vol(t, self.sigma_breakpoints, self.sigma_term)

    def fit_initial_curve(self, curve: pd.DataFrame) -> None:
        self.curve = prepare_curve(curve)
        t, f0 = instantaneous_forward(self.curve)
        dfdt = finite_diff_gradient(t, f0)
        sigma_t = self._sigma_for_grid(t)
        a = max(self.a, 1e-8)
        correction = (sigma_t**2 / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * t))
        self.theta = dfdt + a * f0 + correction
        self.f0_t, self.f0 = t, f0

    def _implied_normal_vol(self, expiry: np.ndarray) -> np.ndarray:
        a = max(self.a, 1e-8)
        if self.sigma_term is None:
            return self.sigma * (1.0 - np.exp(-a * expiry)) / np.maximum(a * np.sqrt(np.maximum(expiry, 1e-8)), 1e-8)
        sig = piecewise_constant_vol(expiry, self.sigma_breakpoints, self.sigma_term)
        return sig * (1.0 - np.exp(-a * expiry)) / np.maximum(a * np.sqrt(np.maximum(expiry, 1e-8)), 1e-8)

    def calibrate_to_options(self, market_caps_floors_or_futures: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        market = market_caps_floors_or_futures.sort_values("expiry")
        expiry = market["expiry"].to_numpy(float)
        target_vol = market["normal_vol"].to_numpy(float)
        term_dependent = bool(kwargs.get("term_dependent", False))

        def obj_const(x: np.ndarray) -> float:
            self.a = float(np.clip(x[0], 1e-5, 5.0))
            self.sigma = float(np.clip(x[1], 1e-6, 2.0))
            err = self._implied_normal_vol(expiry) - target_vol
            return float(np.mean(err**2))

        x0 = np.array([kwargs.get("a0", self.a), kwargs.get("sigma0", max(np.mean(target_vol), 1e-3))], dtype=float)
        bnds = [(1e-5, 5.0), (1e-6, 2.0)]
        if minimize is not None:
            res = minimize(obj_const, x0=x0, bounds=bnds, method="L-BFGS-B")
            self.a = float(np.clip(res.x[0], *bnds[0]))
            self.sigma = float(np.clip(res.x[1], *bnds[1]))
            out: dict[str, Any] = {"a": self.a, "sigma": self.sigma, "success": bool(res.success)}
        else:
            obj_const(x0)
            out = {"a": self.a, "sigma": self.sigma, "success": False}

        if term_dependent:
            brk = kwargs.get("breakpoints")
            if brk is None:
                brk = np.unique(np.concatenate(([0.0], expiry)))
            self.sigma_breakpoints = np.asarray(brk, dtype=float)
            n = len(self.sigma_breakpoints)

            def obj_piece(x: np.ndarray) -> float:
                self.a = float(np.clip(x[0], 1e-5, 5.0))
                self.sigma_term = np.clip(x[1:], 1e-6, 2.0)
                err = self._implied_normal_vol(expiry) - target_vol
                return float(np.mean(err**2))

            x_start = np.concatenate(([self.a], np.full(n, self.sigma)))
            bounds = [(1e-5, 5.0)] + [(1e-6, 2.0)] * n
            if minimize is not None:
                res2 = minimize(obj_piece, x0=x_start, bounds=bounds, method="L-BFGS-B")
                self.a = float(np.clip(res2.x[0], 1e-5, 5.0))
                self.sigma_term = np.clip(res2.x[1:], 1e-6, 2.0)
                out.update({"sigma_term": self.sigma_term, "term_success": bool(res2.success)})
            else:
                obj_piece(x_start)
                out.update({"sigma_term": self.sigma_term, "term_success": False})

        rmse = float(np.sqrt(np.mean((self._implied_normal_vol(expiry) - target_vol) ** 2)))
        out["rmse"] = rmse
        return out

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

        for i in range(n_steps - 1):
            dt = t[i + 1] - t[i]
            a = max(self.a, 1e-8)
            decay = np.exp(-a * dt)
            int_theta = theta_grid[i] * (1.0 - decay) / a
            vol = sigma_grid[i] * np.sqrt((1.0 - np.exp(-2.0 * a * dt)) / (2.0 * a))
            r[:, i + 1] = r[:, i] * decay + int_theta + vol * rng.standard_normal(n_paths)

        return SimulationResult(time_grid=t, short_rates=r)
