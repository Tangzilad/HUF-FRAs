from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class CIPExplainer(BaseExplainer):
    title: str = "Covered Interest Parity (CIP) Premium Analytics"

    def explain_concepts(self) -> str:
        return (
            "CIP links spot FX, forward FX, and interest rates across currencies under no-arbitrage. "
            "Observed deviations from CIP can reflect funding constraints, balance-sheet costs, credit effects, "
            "or liquidity segmentation rather than pure arbitrage opportunities."
        )

    def explain_inputs(self) -> str:
        return (
            "- Spot FX series and tenor-matched FX forward panel.\n"
            "- Domestic and foreign OIS curves for raw CIP computation.\n"
            "- Optional sovereign and supranational curves for purified CIP decomposition.\n"
            "- Optional CDS and treasury-OIS spread curves for credit/liquidity adjustments."
        )

    def explain_calibration(self) -> str:
        return (
            "The analytics stack is formula-driven rather than heavily parameterized: it computes implied rates, "
            "raw basis in basis points, and optional purification by removing estimated local credit differentials. "
            "Additional decomposition maps observed yields into risk-free, credit/liquidity, and residual term-premium blocks."
        )

    def explain_outputs(self) -> str:
        return (
            "Outputs include point-in-time and panel CIP deviations, purified basis measures, and yield-decomposition tables. "
            "These can be consumed directly for monitoring dashboards, historical studies, or strategy backtests."
        )

    def explain_trading_implications(self) -> str:
        return (
            "CIP diagnostics inform FX hedge-cost budgeting, local-vs-hard-currency allocation decisions, and basis timing. "
            "Purified series are especially useful for distinguishing structural credit effects from transient funding stress."
        )
