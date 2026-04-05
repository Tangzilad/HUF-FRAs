"""Explainers for curve calibration diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class CurveFitExplainer(BaseExplainer):
    """Summarize curve fit quality and parameter dynamics."""

    title: str = "Forward Curve Fit Diagnostics"

    def explain_concepts(self) -> str:
        return (
            "Curve-fit diagnostics describe how observed market points are converted into a smooth forward curve. "
            "They focus on fit quality, parameter stability, and whether the resulting curve remains economically plausible."
        )

    def explain_inputs(self) -> str:
        return (
            "- Tenor grid and observed yields/quotes.\n"
            "- Model family choice (Nelson-Siegel or Svensson style).\n"
            "- Optional weighting inputs (bid-ask or liquidity) and regularization settings."
        )

    def explain_calibration(self) -> str:
        return (
            "Calibration minimizes weighted residuals under parameter bounds. "
            "Diagnostics should monitor RMSE, tenor residual patterns, and day-over-day parameter jumps to catch overfitting or stale inputs."
        )

    def explain_outputs(self) -> str:
        return (
            "Outputs include fitted parameters, residual summaries, and implied forward rates by tenor bucket. "
            "Use those outputs to verify that curve shape changes are driven by market information rather than numerical artifacts."
        )

    def explain_trading_implications(self) -> str:
        return (
            "A stable fit improves carry/roll and RV signals, while unstable parameters can create false hedge adjustments. "
            "Treat large residual clusters as a market-data or convention issue before treating them as trade signals."
        )
