"""Risk toolkit modules for EM stress testing and hedge analytics."""

from .factor_models import pca_decompose, prepare_pca_inputs
from .hedging_optimizer import optimize_hedges
from .pnl_decomposition import (
    aggregate_lsc,
    decompose_portfolio_lsc,
    decompose_rate_shocks,
)
from .strategies import STRATEGY_CHOICES, generate_random_positions
from .tail_risk import expected_shortfall, historical_var, parametric_var

__all__ = [
    "prepare_pca_inputs",
    "pca_decompose",
    "optimize_hedges",
    "parametric_var",
    "historical_var",
    "expected_shortfall",
    "decompose_rate_shocks",
    "decompose_portfolio_lsc",
    "aggregate_lsc",
    "generate_random_positions",
    "STRATEGY_CHOICES",
]
