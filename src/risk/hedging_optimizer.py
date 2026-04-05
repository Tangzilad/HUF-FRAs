from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class OptimizerConfig:
    max_notional: float = 5.0
    max_tenor_concentration: float = 0.65
    transaction_cost_per_unit: float = 0.01
    carry_penalty: float = 0.25
    liquidity_penalty: float = 0.1


def optimize_hedges(
    exposure_vector: np.ndarray,
    hedge_matrix: np.ndarray,
    carry_vector: np.ndarray,
    liquidity_vector: np.ndarray,
    instruments: List[str],
    tenor_bucket: List[str],
    config: OptimizerConfig = OptimizerConfig(),
) -> Dict[str, pd.DataFrame | float]:
    """Multi-objective hedge optimizer with XCCY basis + FX forwards support."""

    if hedge_matrix.shape[1] != len(instruments):
        raise ValueError("hedge_matrix column count must equal instruments length")

    q = hedge_matrix.T @ hedge_matrix + np.eye(hedge_matrix.shape[1]) * config.transaction_cost_per_unit
    c = hedge_matrix.T @ exposure_vector + config.carry_penalty * carry_vector + config.liquidity_penalty * liquidity_vector
    x = -np.linalg.solve(q, c)
    x = np.clip(x, -config.max_notional, config.max_notional)

    abs_sum = np.sum(np.abs(x))
    concentration = np.abs(x) / abs_sum if abs_sum > 1e-12 else np.zeros_like(x)
    for i, c_i in enumerate(concentration):
        if c_i > config.max_tenor_concentration:
            target = np.sign(x[i]) * config.max_tenor_concentration * abs_sum
            x[i] = target

    residual = exposure_vector + hedge_matrix @ x
    variance_objective = float(residual.T @ residual)
    penalty = float(config.carry_penalty * np.sum(np.abs(carry_vector * x)) + config.liquidity_penalty * np.sum(np.abs(liquidity_vector * x)))

    binding = []
    for idx, val in enumerate(x):
        reasons = []
        if np.isclose(abs(val), config.max_notional):
            reasons.append("max_notional")
        if concentration[idx] > config.max_tenor_concentration:
            reasons.append("tenor_concentration")
        binding.append(",".join(reasons) if reasons else "none")

    report = pd.DataFrame(
        {
            "instrument": instruments,
            "tenor_bucket": tenor_bucket,
            "optimal_notional": x,
            "carry_cost": carry_vector * x,
            "liquidity_usage": liquidity_vector * np.abs(x),
            "binding_constraints": binding,
        }
    )

    return {
        "solution": report,
        "variance_objective": variance_objective,
        "penalty": penalty,
        "total_objective": variance_objective + penalty,
    }
