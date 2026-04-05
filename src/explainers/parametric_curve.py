from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


@dataclass(slots=True)
class ParametricCurveExplainer:
    """Generate practitioner-friendly commentary for parametric curve fitting."""

    model_family: str = "Svensson / Nelson-Siegel"

    def conceptual_overview(self) -> str:
        return dedent(
            """
            ## Conceptual overview
            Parametric term-structure fitting maps a small set of interpretable factors to a full curve,
            rather than fitting each tenor independently. In this project, the model family is
            Nelson-Siegel (4 parameters) or Svensson (6 parameters), where level, slope, and hump-style
            curvature terms are combined with decay constants. This gives smooth curves, stable
            interpolation across missing maturities, and a compact state vector that can be monitored
            through time.
            """
        ).strip()

    def mathematical_form_and_parameter_intuition(self) -> str:
        return dedent(
            """
            ## Mathematical form and parameter intuition
            Nelson-Siegel form:
            y(t) = beta0 + beta1 * ((1 - exp(-t/tau1)) / (t/tau1))
                   + beta2 * (((1 - exp(-t/tau1)) / (t/tau1)) - exp(-t/tau1))

            Svensson extends this by adding beta3 and tau2 for a second hump term.

            Parameter intuition:
            - beta0: long-run level anchor for far-dated yields.
            - beta1: short-end slope loading (often linked to front-end policy stance).
            - beta2: medium-tenor curvature/hump contribution.
            - beta3 (Svensson only): extra curvature flexibility for complex belly/long-end shapes.
            - tau1, tau2: decay scales controlling where slope and hump effects fade or peak.
            """
        ).strip()

    def data_requirements_and_preprocessing(self) -> str:
        return dedent(
            """
            ## Data requirements and preprocessing assumptions
            Expected inputs in `fit_parametric_curve` are aligned `numpy` arrays:
            - `tenors`: positive maturity values (in consistent year units).
            - `yields`: observed rates/yields at the same tenor points.
            - optional weighting inputs:
              - `bid_ask` when `weight_mode='bid_ask'` (inverse-spread weighting),
              - `liquidity` when `weight_mode='liquidity'` (higher-liquidity emphasis).

            Practical preprocessing assumptions:
            - Remove NaNs and stale points before calibration.
            - Keep tenor units consistent (e.g., all in years).
            - Ensure optional arrays match tenor length.
            - Use market-consistent quoting conventions to avoid artificial basis noise.
            """
        ).strip()

    def calibration_caveats(self) -> str:
        return dedent(
            """
            ## Calibration caveats
            The objective minimizes weighted mean squared residuals plus L2 regularization,
            optimized via bounded L-BFGS-B. This is robust but still subject to:
            - local minima from nonlinear decay parameters,
            - parameter instability when tenors are sparse or clustered,
            - overfitting risk (especially Svensson's extra flexibility),
            - sensitivity to weighting choices and outlier quotes.

            Bounds and regularization help, but diagnostics should still track fit errors,
            parameter jumps, and economic plausibility over time.
            """
        ).strip()

    def trading_interpretation(self) -> str:
        return dedent(
            """
            ## Output interpretation for trading
            Fitted parameters support a shape-based narrative:
            - level shifts indicate broad duration repricing,
            - slope changes drive carry and roll-down opportunities,
            - curvature changes affect belly-vs-wing relative-value trades.

            Desk-level interpretation should connect curve moves to risk metrics like DV01,
            plus second-order effects (convexity) when sizing or hedging nonlinear exposures.
            In cross-market setups, residual basis behavior can reveal dislocations not captured
            by a single-curve fit and can influence basis-trade entry/exit logic.
            """
        ).strip()

    def example_snippet(self) -> str:
        """Return a lightweight usage snippet that references local parametric curve functions."""

        return dedent(
            """
            ```python
            import numpy as np

            from src.curves.parametric import evaluate_curve, fit_parametric_curve

            tenors = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0])
            observed_yields = np.array([0.061, 0.059, 0.056, 0.053, 0.051, 0.050])

            fit = fit_parametric_curve(
                tenors=tenors,
                yields=observed_yields,
                model="svensson",
                weight_mode="uniform",
            )

            fitted_curve = evaluate_curve(tenors, fit.params, fit.model)
            print(fit.success, fit.objective_value)
            print(fitted_curve)
            ```
            """
        ).strip()

    def explain(self, include_example: bool = True) -> str:
        sections = [
            self.conceptual_overview(),
            self.mathematical_form_and_parameter_intuition(),
            self.data_requirements_and_preprocessing(),
            self.calibration_caveats(),
            self.trading_interpretation(),
        ]
        if include_example:
            sections.append("## Lightweight example\n" + self.example_snippet())
        return "\n\n".join(sections)
