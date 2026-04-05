from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class CrossCurrencyExplainer(BaseExplainer):
    title: str = "Cross-Currency Curve Construction"

    def explain_concepts(self) -> str:
        return (
            "Domestic/foreign discounting must remain jointly consistent with FX forwards and quoted basis. "
            "Cross-currency setup combines domestic and foreign discount/projection curves with spot/forward FX, "
            "while respecting collateral conventions and funding currency choices."
        )

    def explain_inputs(self) -> str:
        return (
            "### Required market inputs\n\n"
            "- OIS and IRS quotes by currency and tenor.\n"
            "- Spot FX and forward points/levels by tenor (loader contract expects `quote_type='forward'` and `unit='points'`).\n"
            "- XCCY basis quotes for currency pairs (for example HUF/USD).\n"
            "- Collateral currency assumptions, stale threshold: 30 minutes, and interpolation settings."
        )

    def explain_calibration(self) -> str:
        return (
            "Calibration bootstraps baseline curves, then solves for a smooth basis term structure that minimizes "
            "joint residuals to FX forwards and cross-currency basis quotes. Interpolation choices (linear, cubic, or "
            "monotone variants) should be documented because they can materially change forward-bucket hedges."
        )

    def explain_outputs(self) -> str:
        return (
            "Primary outputs are projection curves, discount curves, basis term structures, and diagnostics such as "
            "RMS error and tenor-level residuals. Risk views should include Cross-currency DV01 mapping plus residual USD exposure "
            "after hedges, so basis and funding sensitivity are visible at desk level."
        )

    def explain_trading_implications(self) -> str:
        return (
            "Traders use these outputs for basis swap pricing, FX-hedged funding comparisons, and collateral optimization. "
            "Operational controls should flag Liquidity gaps, Stale quotes, and Tenor mismatch risk before publishing curves "
            "to pricing and risk systems."
        )
