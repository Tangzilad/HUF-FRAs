"""Explainers for stress-test and scenario outputs."""

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class RiskScenarioExplainer(BaseExplainer):
    """Summarize risk scenario impacts for portfolio diagnostics."""

    title: str = "Risk Scenario Explainer"

    def explain_concepts(self) -> str:
        return (
            "Scenario analysis asks: if a specified macro or liquidity shock happens, how does portfolio P&L move? "
            "It complements statistical VaR by imposing concrete narratives on top of current exposures."
        )

    def explain_inputs(self) -> str:
        return (
            "- Position-level sensitivities (DV01, basis01, FX delta, optional convexity).\n"
            "- Scenario shocks across rates, basis, FX, and volatility.\n"
            "- Correlation or co-movement assumptions for multi-factor propagation."
        )

    def explain_calibration(self) -> str:
        return (
            "Scenarios can be calibrated from historical windows, policy-event templates, or desk-defined stress severities. "
            "Each shock should be mapped to risk factors with explicit sign conventions and units."
        )

    def explain_outputs(self) -> str:
        return (
            "Typical outputs are scenario-by-scenario P&L, factor contribution tables, and ranking of dominant loss drivers. "
            "Comparing baseline versus hedged portfolios clarifies which vulnerabilities are reduced."
        )

    def explain_trading_implications(self) -> str:
        return (
            "Use scenario results to prioritize hedge trades that reduce tail losses with acceptable carry drag. "
            "If losses are concentrated in one factor, targeted hedges are usually more efficient than blanket risk reduction."
        )
