from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover - optional fallback when scipy is absent.
    minimize = None

ModelType = Literal["nelson_siegel", "svensson"]
WeightMode = Literal["uniform", "bid_ask", "liquidity"]


@dataclass(slots=True)
class FitResult:
    model: ModelType
    params: np.ndarray
    success: bool
    objective_value: float
    message: str

    def curve(self, tenors: np.ndarray) -> np.ndarray:
        return evaluate_curve(tenors, self.params, self.model)


def nelson_siegel(tenors: np.ndarray, beta0: float, beta1: float, beta2: float, tau1: float) -> np.ndarray:
    x = tenors / tau1
    factor = (1.0 - np.exp(-x)) / np.where(x == 0.0, 1e-9, x)
    return beta0 + beta1 * factor + beta2 * (factor - np.exp(-x))


def svensson(
    tenors: np.ndarray,
    beta0: float,
    beta1: float,
    beta2: float,
    beta3: float,
    tau1: float,
    tau2: float,
) -> np.ndarray:
    x1 = tenors / tau1
    x2 = tenors / tau2
    f1 = (1.0 - np.exp(-x1)) / np.where(x1 == 0.0, 1e-9, x1)
    f2 = f1 - np.exp(-x1)
    f3 = (1.0 - np.exp(-x2)) / np.where(x2 == 0.0, 1e-9, x2) - np.exp(-x2)
    return beta0 + beta1 * f1 + beta2 * f2 + beta3 * f3


def evaluate_curve(tenors: np.ndarray, params: np.ndarray, model: ModelType) -> np.ndarray:
    if model == "nelson_siegel":
        return nelson_siegel(tenors, *params)
    if model == "svensson":
        return svensson(tenors, *params)
    raise ValueError(f"Unsupported model: {model}")


def _weights(
    mode: WeightMode,
    size: int,
    bid_ask: np.ndarray | None,
    liquidity: np.ndarray | None,
) -> np.ndarray:
    if mode == "uniform":
        return np.ones(size, dtype=float)
    if mode == "bid_ask":
        if bid_ask is None:
            raise ValueError("bid_ask weights requested but bid_ask array is missing")
        return 1.0 / np.clip(bid_ask, 1e-6, None)
    if mode == "liquidity":
        if liquidity is None:
            raise ValueError("liquidity weights requested but liquidity array is missing")
        return np.clip(liquidity, 1e-6, None)
    raise ValueError(f"Unknown weight mode: {mode}")


def fit_parametric_curve(
    tenors: np.ndarray,
    yields: np.ndarray,
    model: ModelType = "svensson",
    weight_mode: WeightMode = "uniform",
    bid_ask: np.ndarray | None = None,
    liquidity: np.ndarray | None = None,
    regularization_lambda: float = 1e-4,
) -> FitResult:
    tenors = np.asarray(tenors, dtype=float)
    yields = np.asarray(yields, dtype=float)
    w = _weights(weight_mode, tenors.size, bid_ask, liquidity)

    if model == "nelson_siegel":
        init = np.array([0.03, -0.01, 0.01, 1.5])
        bounds = [(-0.05, 0.30), (-0.30, 0.30), (-0.30, 0.30), (0.05, 10.0)]
    else:
        init = np.array([0.03, -0.01, 0.01, 0.01, 1.5, 4.0])
        bounds = [
            (-0.05, 0.30),
            (-0.30, 0.30),
            (-0.30, 0.30),
            (-0.30, 0.30),
            (0.05, 10.0),
            (0.10, 15.0),
        ]

    def objective(params: np.ndarray) -> float:
        fitted = evaluate_curve(tenors, params, model)
        resid = yields - fitted
        weighted = np.average(resid**2, weights=w)
        regularizer = regularization_lambda * np.sum(params**2)
        return float(weighted + regularizer)

    if minimize is None:
        # Fallback: return initial guess evaluated with objective.
        score = objective(init)
        return FitResult(model=model, params=init, success=False, objective_value=score, message="SciPy unavailable")

    result = minimize(objective, init, method="L-BFGS-B", bounds=bounds)
    return FitResult(
        model=model,
        params=result.x,
        success=bool(result.success),
        objective_value=float(result.fun),
        message=str(result.message),
    )
