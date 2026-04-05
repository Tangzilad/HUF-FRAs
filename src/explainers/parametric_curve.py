from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class ParametricCurveExplainer(BaseExplainer):
    title: str = "Parametric Yield Curve (Nelson-Siegel / Svensson)"

    def explain_concepts(self) -> str:
        return (
            "Parametric curve models compress a full yield curve into a small set of interpretable "
            "parameters. In this codebase, the curve module supports Nelson-Siegel and Svensson forms, "
            "which represent level, slope, and curvature effects as smooth functions of tenor. "
            "This gives a stable representation when market quotes are noisy or sparse."
        )

    def explain_inputs(self) -> str:
        return (
            "- `tenors`: maturities in years for observed quotes.\n"
            "- `yields`: market yields aligned to `tenors`.\n"
            "- `model`: `nelson_siegel` or `svensson`.\n"
            "- `weight_mode`: `uniform`, `bid_ask`, or `liquidity`.\n"
            "- Optional `bid_ask`, `liquidity`, and `regularization_lambda` to control fit robustness."
        )

    def explain_calibration(self) -> str:
        return (
            "Calibration minimizes weighted squared fitting error plus L2 regularization on parameters. "
            "When SciPy is available, the optimizer uses L-BFGS-B with sensible bounds for betas and decay terms; "
            "otherwise it returns an evaluated initial guess as a deterministic fallback."
        )

    def explain_outputs(self) -> str:
        return (
            "The fit returns parameter values, optimization status, objective value, and a callable curve evaluator. "
            "From these outputs you can derive fitted zero rates for any tenor and inspect residual quality "
            "through objective magnitude and success flags."
        )

    def explain_trading_implications(self) -> str:
        return (
            "A parametric fit supports cleaner relative-value signals (e.g., rich/cheap points vs curve), "
            "scenario shock design, and hedge ratio estimation. Parameter changes can also be interpreted as "
            "macro moves in level/slope/curvature, helping desk communication and risk attribution."
        )
