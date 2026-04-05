from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class RiskExplainer(BaseExplainer):
    title: str = "Risk Stack (Factors, Scenarios, and Hedging)"

    def explain_concepts(self) -> str:
        return (
            "The risk stack combines statistical factor extraction, scenario shocks, and hedge optimization to translate "
            "market narratives into PnL and risk actions. It is designed for EM rates/FX contexts where macro and liquidity "
            "regimes can shift quickly. The stack connects exposures such as DV01 and basis risk with non-linear convexity effects."
        )

    def explain_inputs(self) -> str:
        return (
            "- Rate and macro time series for preprocessing and PCA/factor analysis.\n"
            "- Portfolio sensitivities or positions for shock aggregation (including DV01, FX delta, and basis01).\n"
            "- Scenario definitions (for example devaluation or liquidity shocks).\n"
            "- Hedging constraints and objective weights (risk reduction vs carry/cost)."
        )

    def explain_calibration(self) -> str:
        return (
            "Calibration is modular: preprocessing aligns mixed-frequency data, standardizes variables, and extracts principal "
            "factors from covariance structure. Scenario parameters are selected from historical stress windows or policy narratives, "
            "then hedging optimization solves constrained allocations against chosen objectives. Tail metrics should report both "
            "VaR and ES under consistent confidence levels."
        )

    def explain_outputs(self) -> str:
        return (
            "Typical outputs are factor loadings, explained variance, scenario PnL distributions, and recommended hedge overlays. "
            "Backtesting modules can report hit rates, drawdowns, VaR/ES breaches, and stability diagnostics for ongoing model governance."
        )

    def explain_trading_implications(self) -> str:
        return (
            "Risk outputs guide position sizing, stop-loss design, and macro hedge selection. They also help identify when risk "
            "is concentrated in hidden factors (for example FX-vol or risk-off beta) that are not obvious from nominal DV01 alone, "
            "and when basis dislocations or convexity carry can dominate expected PnL."
        )
