from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class CrossCurrencyExplainer(BaseExplainer):
    title: str = "Cross-Currency Curve Construction"

    def explain_concepts(self) -> str:
        return (
            "Cross-currency setup combines domestic and foreign discount/projection curves with FX forwards and "
            "quoted cross-currency basis. The goal is internally consistent pricing across interest-rate legs and FX, "
            "while respecting collateral conventions."
        )

    def explain_inputs(self) -> str:
        return (
            "- OIS and IRS quotes by currency and tenor.\n"
            "- Spot FX and forward points/levels by tenor.\n"
            "- XCCY basis quotes for currency pairs (for example HUF/USD).\n"
            "- Collateral currency assumptions and interpolation settings."
        )

    def explain_calibration(self) -> str:
        return (
            "Calibration bootstraps baseline curves, then solves for a smooth basis term structure that minimizes "
            "joint residuals to FX forwards and cross-currency basis quotes. A smoothness penalty stabilizes the fit "
            "and avoids unrealistic oscillations in sparse markets."
        )

    def explain_outputs(self) -> str:
        return (
            "Primary outputs are projection curves, discount curves, basis term structures, and diagnostics such as "
            "RMS error and tenor-level residuals. These provide both pricing inputs and model-governance checks."
        )

    def explain_trading_implications(self) -> str:
        return (
            "Traders use these outputs for basis swap pricing, FX-hedged funding comparisons, and collateral optimization. "
            "Residual patterns can reveal where forwards or basis quotes look dislocated, creating relative-value opportunities "
            "or hedging warnings."
        )
