"""Post-simulation explanation generator.

Produces human-readable narratives that explain *why* P&L, roll-down,
carry, convexity, and hedge residuals came out the way they did after
any scenario or FRA simulation run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class ScenarioContext:
    """Captures everything needed to explain a risk-scenario run."""

    scenario_name: str
    scenario_description: str = ""
    rates_bp: Dict[str, float] = field(default_factory=dict)
    fx_pct: Dict[str, float] = field(default_factory=dict)
    basis_bp: Dict[str, float] = field(default_factory=dict)


@dataclass
class FRASimContext:
    """Captures everything needed to explain a Monte-Carlo FRA simulation."""

    model_name: str = "Ho-Lee"
    sigma: float = 0.01
    n_paths: int = 1_500
    tenor_label: str = ""
    start: float = 0.0
    end: float = 0.0
    fra_pnl: np.ndarray | None = None
    fra_forward: np.ndarray | None = None
    futures_rate: np.ndarray | None = None


# ---------------------------------------------------------------------------
# Core narrative engine
# ---------------------------------------------------------------------------

class SimulationNarrativeGenerator:
    """Generate plain-English explanations for simulation outputs.

    Usage::

        gen = SimulationNarrativeGenerator()
        md = gen.explain_scenario(pnl_df, decomp, scenario_ctx)
        md = gen.explain_fra_simulation(fra_ctx, convexity_summary)
    """

    # -- public API ---------------------------------------------------------

    def explain_scenario(
        self,
        trade_pnl: pd.DataFrame,
        decomposition: Dict[str, pd.DataFrame],
        context: ScenarioContext,
    ) -> str:
        """Return markdown narrative for a risk-scenario run."""

        sections: list[str] = []
        sections.append(self._scenario_header(context))
        sections.append(self._total_pnl_summary(trade_pnl))
        sections.append(self._factor_attribution(trade_pnl))
        sections.append(self._bucket_attribution(decomposition))
        sections.append(self._instrument_attribution(decomposition))
        sections.append(self._carry_vs_shock(trade_pnl))
        sections.append(self._hedge_effectiveness(trade_pnl))
        sections.append(self._dominant_driver(trade_pnl, context))
        sections.append(self._actionable_takeaways(trade_pnl, context))
        return "\n\n".join(s for s in sections if s)

    def explain_fra_simulation(
        self,
        context: FRASimContext,
        convexity_summary: pd.DataFrame | None = None,
    ) -> str:
        """Return markdown narrative for a Monte-Carlo FRA simulation."""

        sections: list[str] = []
        sections.append(self._fra_header(context))
        sections.append(self._fra_distribution(context))
        if convexity_summary is not None and not convexity_summary.empty:
            sections.append(self._convexity_narrative(convexity_summary, context))
        sections.append(self._fra_risk_interpretation(context))
        return "\n\n".join(s for s in sections if s)

    # -- scenario helpers ---------------------------------------------------

    def _scenario_header(self, ctx: ScenarioContext) -> str:
        name = ctx.scenario_name.replace("_", " ").title()
        lines = [f"## Simulation Explanation: {name}"]
        if ctx.scenario_description:
            lines.append(f"*{ctx.scenario_description}*")
        return "\n".join(lines)

    def _total_pnl_summary(self, df: pd.DataFrame) -> str:
        total = df["pnl_total"].sum()
        direction = "loss" if total < 0 else "gain"
        return (
            f"### Total P&L\n\n"
            f"The portfolio experienced a net **{direction}** of **{total:,.0f}** "
            f"under this scenario."
        )

    def _factor_attribution(self, df: pd.DataFrame) -> str:
        factors = {
            "pnl_rate": "Interest-rate moves",
            "pnl_fx": "FX spot move",
            "pnl_basis": "Basis spread change",
            "carry": "Carry / roll-down",
        }
        rows: list[str] = ["| Factor | P&L | % of gross |", "|--------|----:|----------:|"]
        gross = sum(abs(df[col].sum()) for col in factors if col in df.columns)
        if gross < 1e-12:
            gross = 1.0
        for col, label in factors.items():
            if col not in df.columns:
                continue
            val = df[col].sum()
            pct = abs(val) / gross * 100
            rows.append(f"| {label} | {val:,.0f} | {pct:.1f}% |")
        return "### P&L by risk factor\n\n" + "\n".join(rows)

    def _bucket_attribution(self, decomp: Dict[str, pd.DataFrame]) -> str:
        fb = decomp.get("factor_bucket")
        if fb is None or fb.empty:
            return ""
        lines = ["### P&L by tenor bucket\n"]
        for _, row in fb.iterrows():
            bucket = row.get("tenor_bucket", "?")
            total = row.get("pnl_total", 0.0)
            tag = "loss" if total < 0 else "gain"
            lines.append(f"- **{bucket}**: {total:,.0f} ({tag})")
        worst = fb.loc[fb["pnl_total"].idxmin()]
        lines.append(
            f"\nThe **{worst['tenor_bucket']}** bucket drove the largest loss because "
            f"scenario shocks were most severe at that part of the curve."
        )
        return "\n".join(lines)

    def _instrument_attribution(self, decomp: Dict[str, pd.DataFrame]) -> str:
        inst = decomp.get("instrument")
        if inst is None or inst.empty:
            return ""
        lines = ["### P&L by instrument\n"]
        for _, row in inst.iterrows():
            name = row.get("instrument", "?")
            total = row.get("pnl_total", 0.0)
            lines.append(f"- **{name}**: {total:,.0f}")
        return "\n".join(lines)

    def _carry_vs_shock(self, df: pd.DataFrame) -> str:
        carry_total = df["carry"].sum() if "carry" in df.columns else 0.0
        shock_total = sum(
            df[c].sum() for c in ["pnl_rate", "pnl_fx", "pnl_basis"] if c in df.columns
        )
        if abs(carry_total) < 1e-12:
            return ""
        ratio = abs(shock_total / carry_total) if abs(carry_total) > 1e-12 else 0
        lines = [
            "### Carry vs. shock impact\n",
            f"- **Carry income**: {carry_total:,.0f}",
            f"- **Shock losses**: {shock_total:,.0f}",
        ]
        if ratio > 1:
            lines.append(
                f"- Shock losses are **{ratio:.1f}x** carry income — "
                f"the scenario overwhelms the portfolio's carry buffer."
            )
        else:
            lines.append(
                f"- Carry covers **{1/ratio:.0f}%** of shock losses — "
                f"the carry buffer partially offsets the scenario impact."
            )
        return "\n".join(lines)

    def _hedge_effectiveness(self, df: pd.DataFrame) -> str:
        if "hedge_overlay" not in df.columns:
            return ""
        hedged = df[df["hedge_overlay"] == True]  # noqa: E712
        core = df[df["hedge_overlay"] == False]  # noqa: E712
        if hedged.empty:
            return ""
        core_pnl = core["pnl_total"].sum()
        hedge_pnl = hedged["pnl_total"].sum()
        net = core_pnl + hedge_pnl
        pct_offset = abs(hedge_pnl / core_pnl * 100) if abs(core_pnl) > 1e-12 else 0
        lines = [
            "### Hedge effectiveness\n",
            f"- **Core portfolio P&L**: {core_pnl:,.0f}",
            f"- **Hedge overlay P&L**: {hedge_pnl:,.0f}",
            f"- **Net P&L after hedges**: {net:,.0f}",
            f"- Hedges offset **{pct_offset:.0f}%** of core losses.",
        ]
        if pct_offset > 80:
            lines.append("- Hedges are highly effective under this scenario.")
        elif pct_offset > 40:
            lines.append("- Partial hedge coverage — residual risk remains material.")
        else:
            lines.append(
                "- Hedges provide limited protection — the scenario hits exposures "
                "not well-covered by current overlay."
            )
        return "\n".join(lines)

    def _dominant_driver(self, df: pd.DataFrame, ctx: ScenarioContext) -> str:
        factors = {"pnl_rate": "rate", "pnl_fx": "FX", "pnl_basis": "basis"}
        abs_vals = {
            label: abs(df[col].sum())
            for col, label in factors.items()
            if col in df.columns
        }
        if not abs_vals:
            return ""
        dominant = max(abs_vals, key=abs_vals.get)  # type: ignore[arg-type]
        explanations = {
            "rate": (
                f"Rate moves dominate because the scenario applied large parallel/tilt shocks "
                f"({_fmt_shocks(ctx.rates_bp, 'bp')}) against positions with significant DV01."
            ),
            "FX": (
                f"FX is the dominant driver because spot moved {ctx.fx_pct.get('spot', 0):.1f}% "
                f"and the portfolio has material unhedged FX delta."
            ),
            "basis": (
                f"Basis spread changes dominate because the scenario widened cross-currency basis "
                f"({_fmt_shocks(ctx.basis_bp, 'bp')}) and the portfolio has basis01 exposure."
            ),
        }
        return (
            f"### Why this result?\n\n"
            f"**Dominant driver: {dominant} moves.**\n\n"
            f"{explanations.get(dominant, '')}"
        )

    def _actionable_takeaways(self, df: pd.DataFrame, ctx: ScenarioContext) -> str:
        total = df["pnl_total"].sum()
        factors = {
            "pnl_rate": ("rate", "DV01"),
            "pnl_fx": ("FX", "FX delta"),
            "pnl_basis": ("basis", "basis01"),
        }
        worst_col = min(
            (c for c in factors if c in df.columns),
            key=lambda c: df[c].sum(),
            default=None,
        )
        tips: list[str] = ["### Actionable takeaways\n"]
        if total < 0:
            tips.append("- The portfolio lost money — consider whether existing hedges are sized correctly.")
        if worst_col:
            label, sens = factors[worst_col]
            tips.append(
                f"- **{label.title()} exposure** is the biggest loss source. "
                f"Review {sens} across tenor buckets and consider adding targeted hedges."
            )
        carry = df["carry"].sum() if "carry" in df.columns else 0
        if carry > 0 and total < 0:
            days = abs(total / carry) if carry > 0 else float("inf")
            if days < 365:
                tips.append(
                    f"- At current carry ({carry:,.0f}/day), it would take ~**{days:.0f} days** "
                    f"to recover the scenario loss."
                )
            else:
                tips.append(
                    "- Carry alone cannot recover this loss within a reasonable horizon — "
                    "active risk reduction may be needed."
                )
        return "\n".join(tips)

    # -- FRA simulation helpers ---------------------------------------------

    def _fra_header(self, ctx: FRASimContext) -> str:
        return (
            f"## FRA Simulation Explanation\n\n"
            f"Model: **{ctx.model_name}** | Vol (sigma): **{ctx.sigma:.4f}** | "
            f"Paths: **{ctx.n_paths:,}** | Tenor: **{ctx.tenor_label or f'{ctx.start:.2f}-{ctx.end:.2f}y'}**"
        )

    def _fra_distribution(self, ctx: FRASimContext) -> str:
        if ctx.fra_pnl is None or len(ctx.fra_pnl) == 0:
            return "### P&L distribution\n\nNo simulation data available."

        pnl = ctx.fra_pnl
        fwd = ctx.fra_forward
        fut = ctx.futures_rate

        lines = ["### P&L distribution\n"]
        mean_pnl = float(np.mean(pnl))
        std_pnl = float(np.std(pnl))
        p05 = float(np.quantile(pnl, 0.05))
        p95 = float(np.quantile(pnl, 0.95))

        lines.append(f"| Statistic | Value |")
        lines.append(f"|-----------|------:|")
        lines.append(f"| Mean P&L | {mean_pnl:,.2f} |")
        lines.append(f"| Std Dev | {std_pnl:,.2f} |")
        lines.append(f"| 5th percentile | {p05:,.2f} |")
        lines.append(f"| 95th percentile | {p95:,.2f} |")

        lines.append("")
        if mean_pnl > 0:
            lines.append(
                f"The FRA has a **positive expected P&L** ({mean_pnl:,.2f}), meaning the "
                f"forward rate implied by the model is above the FRA strike on average."
            )
        elif mean_pnl < 0:
            lines.append(
                f"The FRA has a **negative expected P&L** ({mean_pnl:,.2f}), meaning the "
                f"forward rate implied by the model is below the FRA strike on average."
            )
        else:
            lines.append("The FRA is approximately **at fair value** — expected P&L is near zero.")

        skew_ratio = abs(p05) / abs(p95) if abs(p95) > 1e-12 else 1.0
        if skew_ratio > 1.5:
            lines.append(
                f"The distribution is **left-skewed** — downside tail ({p05:,.2f}) is "
                f"larger than upside ({p95:,.2f}). Tail risk is asymmetric."
            )
        elif skew_ratio < 0.67:
            lines.append(
                f"The distribution is **right-skewed** — upside tail ({p95:,.2f}) exceeds "
                f"downside ({p05:,.2f})."
            )

        if fwd is not None and len(fwd):
            lines.append(
                f"\n**Forward rate**: mean {float(np.mean(fwd)):.4%}, "
                f"range [{float(np.quantile(fwd, 0.05)):.4%}, {float(np.quantile(fwd, 0.95)):.4%}]"
            )
        if fut is not None and len(fut):
            lines.append(
                f"**Futures rate**: mean {float(np.mean(fut)):.4%}"
            )

        return "\n".join(lines)

    def _convexity_narrative(self, summary: pd.DataFrame, ctx: FRASimContext) -> str:
        lines = ["### Convexity adjustment explained\n"]

        if "convexity_adjustment" not in summary.columns:
            return ""

        for _, row in summary.iterrows():
            vol = row.get("vol_regime", ctx.sigma)
            conv = row.get("convexity_adjustment", 0.0)
            tenor = row.get("tenor", ctx.tenor_label)
            conv_bp = conv * 10_000

            if abs(conv_bp) < 0.5:
                magnitude = "negligible"
                advice = "FRA and futures pricing are effectively equivalent."
            elif abs(conv_bp) < 3:
                magnitude = "modest"
                advice = "Account for this in precision pricing but it won't materially affect hedge ratios."
            else:
                magnitude = "material"
                advice = "This gap matters — using futures to hedge FRAs without adjusting for convexity will introduce systematic P&L leakage."

            lines.append(
                f"- **{tenor}** at vol={vol:.3f}: convexity = **{conv_bp:.2f} bp** ({magnitude}). {advice}"
            )

        mean_pnl_col = "fra_pnl_mean"
        std_pnl_col = "fra_pnl_std"
        if mean_pnl_col in summary.columns and std_pnl_col in summary.columns:
            lines.append("\n**Why does P&L vary across volatility regimes?**")
            lines.append(
                "Higher volatility increases the range of simulated rate paths. This widens the "
                "P&L distribution (higher std dev) and amplifies the convexity adjustment because "
                "the daily-settlement asymmetry of futures becomes more pronounced."
            )

        return "\n".join(lines)

    def _fra_risk_interpretation(self, ctx: FRASimContext) -> str:
        if ctx.fra_pnl is None or len(ctx.fra_pnl) == 0:
            return ""
        pnl = ctx.fra_pnl
        std_pnl = float(np.std(pnl))
        mean_pnl = float(np.mean(pnl))
        sharpe_proxy = mean_pnl / std_pnl if std_pnl > 1e-12 else 0

        lines = ["### Risk interpretation\n"]
        lines.append(f"- **Risk/reward proxy** (mean / std): {sharpe_proxy:.3f}")
        if abs(sharpe_proxy) < 0.1:
            lines.append("  - Near zero — the expected P&L is small relative to the risk taken.")
        elif sharpe_proxy > 0.3:
            lines.append("  - Positive and meaningful — the position has favorable expected return per unit risk.")
        elif sharpe_proxy < -0.3:
            lines.append("  - Negative — the position is expected to lose money relative to the risk.")

        p01 = float(np.quantile(pnl, 0.01))
        lines.append(f"- **1% tail loss (VaR proxy)**: {p01:,.2f}")
        lines.append(
            f"- In the worst 1% of simulated paths, you would lose at least **{abs(p01):,.2f}**. "
            f"Size your position so this tail loss is within your risk budget."
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_shocks(shocks: Dict[str, float], unit: str) -> str:
    if not shocks:
        return "no shocks specified"
    return ", ".join(f"{k}: +{v:.0f} {unit}" for k, v in shocks.items())
