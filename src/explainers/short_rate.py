from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class ShortRateExplainer(BaseExplainer):
    title: str = "Short-Rate Models (Ho-Lee / Hull-White)"

    def explain_concepts(self) -> str:
        return (
            "Short-rate models describe the instantaneous interest rate dynamics and use them to price "
            "rate derivatives and simulate FRA outcomes. Ho-Lee gives an additive normal process with exact "
            "initial-curve fitting, while Hull-White adds mean reversion for more realistic long-horizon behavior."
        )

    def explain_inputs(self) -> str:
        return (
            "- Initial discount or zero curve used to derive instantaneous forwards.\n"
            "- Volatility assumptions (constant or term-dependent).\n"
            "- Optional option-implied market quotes (cap/floor or futures vol data) for calibration.\n"
            "- Simulation settings such as time grid, number of paths, and random seed."
        )

    def explain_calibration(self) -> str:
        return (
            "The workflow first fits model drift to match the initial term structure, then calibrates volatility "
            "(and potentially mean reversion, depending on model) to option-implied targets by minimizing error metrics. "
            "Term-dependent volatility can be represented with piecewise constants across expiry buckets."
        )

    def explain_outputs(self) -> str:
        return (
            "Outputs include calibrated parameters, simulated short-rate paths, and validation diagnostics such as "
            "moment comparisons between simulated and theoretical distributions. These can feed FRA pricing, expected PnL, "
            "and distributional risk metrics."
        )

    def explain_trading_implications(self) -> str:
        return (
            "For trading, short-rate models support convexity-aware FRA valuation, scenario generation under policy-rate "
            "uncertainty, and stress testing of carry/roll strategies. Calibration drift over time may indicate regime changes "
            "in volatility pricing or policy credibility."
        )
