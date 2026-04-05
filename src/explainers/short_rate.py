from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ShortRateExplainer:
    """Build plain-English markdown commentary for short-rate model workflows."""

    currency: str = "HUF"
    desk_name: str = "sell-side STIR desk"

    def explain(
        self,
        model_name: str,
        calibration_result: dict[str, Any] | None = None,
        sim_short_rates: np.ndarray | None = None,
        time_grid: np.ndarray | None = None,
        fra_forwards: np.ndarray | None = None,
        fra_pnl: np.ndarray | None = None,
        dv01: float | None = None,
        convexity_adjustment: float | None = None,
    ) -> str:
        """Return markdown that covers assumptions, calibration, and risk interpretation."""

        parts = [
            self._intro(),
            self._assumptions(model_name),
            self._calibration(calibration_result),
            self._outputs(sim_short_rates, time_grid, fra_forwards, fra_pnl, dv01, convexity_adjustment),
            self._sell_side_stir_section(dv01, convexity_adjustment),
        ]
        return "\n\n".join(parts)

    def _intro(self) -> str:
        return (
            "## Why short-rate models matter for scenario generation and FRA valuation\n\n"
            "Short-rate models translate today's curve into stochastic paths for the instantaneous funding rate "
            "\\(r_t\\), then convert those paths into instrument-level risk. In this repository that means:\n\n"
            "- Scenario generation: Monte Carlo paths for \\(r_t\\) support stress narratives and distributional metrics.\n"
            "- FRA valuation: each path implies a forward fixing and discount factor, enabling pathwise FRA P&L "
            "and convexity analysis versus futures-like rates.\n\n"
            "Useful identity:\n\n"
            "\\[\n"
            "P(t,T)=\\mathbb{E}_t\\left[\\exp\\left(-\\int_t^T r_u\\,du\\right)\\right],\n"
            "\\]\n\n"
            "Once \\(r_t\\) is simulated, discounting and FRA valuation are mechanically available."
        )

    def _assumptions(self, model_name: str) -> str:
        model = model_name.strip().lower()

        if "hull" in model:
            specific = (
                "### Hull-White 1F assumptions\n\n"
                "\\[\n"
                "dr_t = \\big(\\theta(t)-a r_t\\big)dt + \\sigma(t) dW_t.\n"
                "\\]\n\n"
                "- Mean reversion \\(a>0\\): shocks decay, improving long-horizon stability.\n"
                "- Volatility structure: constant \\(\\sigma\\) or piecewise-constant \\(\\sigma(t)\\).\n"
                "- Normal-vol proxy often used in calibration:\n"
                "\\[\n"
                "\\sigma_N(T) \\approx \\sigma(T)\\,\\frac{1-e^{-aT}}{a\\sqrt{T}}.\n"
                "\\]"
            )
        elif "ho" in model:
            specific = (
                "### Ho-Lee assumptions\n\n"
                "\\[\n"
                "dr_t = \\theta(t)dt + \\sigma(t)dW_t.\n"
                "\\]\n\n"
                "- No mean reversion term: shocks accumulate over time.\n"
                "- Volatility structure: constant \\(\\sigma\\) or term buckets.\n"
                "- Distribution remains Gaussian at each horizon (tractable but allows negative rates)."
            )
        else:
            specific = (
                "### Model assumption checklist\n\n"
                "- Mean reversion treatment (estimated/fixed).\n"
                "- Volatility structure (constant vs term-dependent).\n"
                "- Distributional simplification (typically Gaussian shocks)."
            )

        common = (
            "### Shared simplifications\n\n"
            "- Single-factor dynamics: one Brownian shock drives short-end moves.\n"
            "- Risk-neutral setup for pricing: drift fits today's curve, not a macro forecast.\n"
            "- Useful for scenario and valuation consistency, but can understate richer regime structure."
        )
        return f"## Model assumptions and what they imply\n\n{specific}\n\n{common}"

    def _calibration(self, calibration_result: dict[str, Any] | None) -> str:
        if calibration_result is None:
            return (
                "## Calibration inputs and interpretation\n\n"
                "Calibration typically uses market normal vols by expiry and an input zero curve to infer drift terms.\n\n"
                "- Fit quality: RMSE should be judged against market quote noise/bid-ask.\n"
                "- Stability: parameters should not jump under small data changes.\n"
                "- Robustness: multi-start/bootstrap diagnostics are preferred when available."
            )

        rmse = calibration_result.get("rmse")
        a = calibration_result.get("a")
        sigma = calibration_result.get("sigma")
        success = calibration_result.get("success")

        bullets: list[str] = []
        if a is not None:
            bullets.append(f"- Mean reversion estimate \\(a\\): **{float(a):.4f}**.")
        if sigma is not None:
            bullets.append(f"- Volatility level \\(\\sigma\\): **{float(sigma):.4%}**.")
        if rmse is not None:
            bullets.append(f"- Fit error (RMSE): **{float(rmse):.6f}** in normal-vol units.")
        if success is not None:
            bullets.append(f"- Optimizer convergence flag: **{bool(success)}**.")
        if not bullets:
            bullets.append("- No standard fields (`a`, `sigma`, `rmse`, `success`) were detected.")

        return (
            "## Calibration inputs and interpretation\n\n"
            "Core inputs:\n\n"
            "- Initial term structure \\(t, z(t)\\) to anchor model drift.\n"
            "- Market normal-vol quotes by expiry/tenor.\n"
            "- Optimization controls (bounds, regularization, starts).\n\n"
            "Observed calibration output:\n\n"
            + "\n".join(bullets)
            + "\n\nInterpretation:\n\n"
            "- Lower RMSE is good only if parameters remain economically plausible.\n"
            "- Prefer stable parameter trajectories across days and re-runs."
        )

    def _outputs(
        self,
        sim_short_rates: np.ndarray | None,
        time_grid: np.ndarray | None,
        fra_forwards: np.ndarray | None,
        fra_pnl: np.ndarray | None,
        dv01: float | None,
        convexity_adjustment: float | None,
    ) -> str:
        lines: list[str] = [
            "## Output interpretation: simulated paths, FRA rates, P&L sensitivities, DV01 and convexity",
            "",
            "Useful FRA approximation on accrual period \\([T_1,T_2]\\):",
            "",
            "\\[",
            "L(T_1,T_2) \\approx \\frac{e^{r_{T_1}\\tau}-1}{\\tau}, \\quad \\tau=T_2-T_1.",
            "\\]",
            "",
            "Pathwise PV interpretation:",
            "",
            "\\[",
            "PV \\propto N\\tau\\big(L(T_1,T_2)-K\\big)D(0,T_2).",
            "\\]",
            "",
        ]

        if sim_short_rates is not None and sim_short_rates.size:
            horizon = float(time_grid[-1]) if time_grid is not None and len(time_grid) else float("nan")
            lines.append(
                f"- Simulated paths: horizon **{horizon:.2f}y**, terminal mean **{float(np.mean(sim_short_rates[:, -1])):.4%}**, terminal std **{float(np.std(sim_short_rates[:, -1])):.4%}**."
            )

        if fra_forwards is not None and len(fra_forwards):
            lines.append(
                f"- FRA forwards: mean **{float(np.mean(fra_forwards)):.4%}**, p05 **{float(np.quantile(fra_forwards, 0.05)):.4%}**, p95 **{float(np.quantile(fra_forwards, 0.95)):.4%}**."
            )

        if fra_pnl is not None and len(fra_pnl):
            lines.append(
                f"- FRA P&L: mean **{float(np.mean(fra_pnl)):.2f}**, std **{float(np.std(fra_pnl)):.2f}**, p05/p95 **[{float(np.quantile(fra_pnl, 0.05)):.2f}, {float(np.quantile(fra_pnl, 0.95)):.2f}]**."
            )

        if dv01 is not None:
            lines.append(f"- DV01: **{dv01:,.2f}** per 1bp parallel shock.")
            lines.append("- First-order sensitivity: \\(\\Delta PV \\approx -DV01\\,\\Delta y_{bp}\\).")

        if convexity_adjustment is not None:
            lines.append(f"- Convexity adjustment (futures minus FRA forward): **{convexity_adjustment:.4%}**.")

        lines.append("- Second-order effect (convexity): \\(\\Delta PV \\approx -DV01\\Delta y + \\tfrac{1}{2}\\Gamma(\\Delta y)^2\\).")
        return "\n".join(lines)

    def _sell_side_stir_section(self, dv01: float | None, convexity_adjustment: float | None) -> str:
        dv01_text = f"about {dv01:,.2f} per bp" if dv01 is not None else "from current risk reports"
        conv_text = f"{convexity_adjustment:.4%}" if convexity_adjustment is not None else "the model-implied level"
        return (
            f"## Plain-English view for a {self.desk_name}\n\n"
            "- **Carry / roll-down:** expected P&L often comes from moving down the curve if the realized path stays close to forwards.\n"
            "- **Scenario stress:** test front-end jumps, sticky-high policy paths, and volatility shocks; compare full distributions, not single outcomes.\n"
            f"- **Hedge implications:** with DV01 {dv01_text}, neutralize first-order exposure first, then optimize convexity residuals.\n"
            f"- **Futures-vs-FRA choice:** convexity around {conv_text} explains basis between futures-implied rates and true forwards.\n"
            "- **Desk discipline:** recalibrate daily and investigate abrupt jumps in fit RMSE or key parameters before resizing risk."
        )


def summarize_convexity_table(summary: pd.DataFrame) -> str:
    """Summarize convexity-adjustment output in markdown text."""
    if summary.empty:
        return "No convexity summary rows available."

    cols = [c for c in ["tenor", "vol_regime", "convexity_adjustment", "fra_pnl_mean", "fra_pnl_std"] if c in summary.columns]
    ordered = summary[cols].sort_values([c for c in ["tenor", "vol_regime"] if c in cols])
    return "### Convexity summary snapshot\n\n" + ordered.to_markdown(index=False)

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
