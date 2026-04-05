"""Explainer for level / slope / curvature P&L decomposition.

Produces plain-English narratives that describe how parallel shifts,
steepening/flattening, and butterfly/curvature moves impact portfolio P&L.
Macro triggers are cited to help learners connect analytics to real-world events.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseExplainer
from ..risk.pnl_decomposition import CurveShockComponents


@dataclass(frozen=True)
class SlopeCurvatureExplainer(BaseExplainer):
    """Interpret level/slope/curvature decomposition results."""

    title: str = "Yield-Curve Decomposition: Level, Slope, and Curvature"

    def explain_concepts(self) -> str:
        return (
            "Any yield-curve move can be decomposed into three orthogonal components:\n\n"
            "- **Level (parallel shift)**: the average change across all maturities. "
            "A +50 bp level move means every tenor shifted up by roughly 50 bp.\n"
            "- **Slope (steepening/flattening)**: the difference between long-term and "
            "short-term rate changes. Positive slope = steepening (long rates rose more). "
            "A curve steepener trade profits when the spread between long- and short-term "
            "yields widens.\n"
            "- **Curvature (butterfly/skew)**: the second difference — how the mid-segment "
            "moved relative to the wings. Positive curvature means the belly cheapened "
            "(rose more) relative to front and back. Butterfly trades exploit changes in "
            "mid-segment rates relative to the wings.\n\n"
            "Together these three factors explain nearly all variation in a parallel + tilt "
            "+ bend shock framework."
        )

    def explain_inputs(self) -> str:
        return (
            "- Scenario rate shocks by tenor bucket (front, belly, back) in basis points.\n"
            "- Trade-level DV01 sensitivities mapped to the same tenor buckets.\n"
            "- Optional: basis01 and FX delta for non-rate components (handled separately)."
        )

    def explain_calibration(self) -> str:
        return (
            "**Level** = mean of all bucket shocks.\n"
            "**Slope** = back shock minus front shock (positive ⇒ steepening).\n"
            "**Curvature** = front + back − 2 × belly (positive ⇒ concave / wings up).\n\n"
            "Each trade's DV01 is multiplied by bucket-specific loadings on these three "
            "factors to attribute P&L."
        )

    def explain_outputs(self) -> str:
        return (
            "The decomposition table shows per-trade and aggregate P&L attributed to level, "
            "slope, and curvature factors, plus each factor's percentage contribution to "
            "total rate P&L and its DV01 contribution."
        )

    def explain_trading_implications(self) -> str:
        return (
            "- If **level** dominates: the portfolio is primarily exposed to parallel moves. "
            "Consider duration hedges.\n"
            "- If **slope** dominates: the portfolio is a directional steepener or flattener. "
            "Adjust relative long-vs-short positioning.\n"
            "- If **curvature** dominates: the portfolio is a butterfly trade. "
            "Review belly vs. wing exposures."
        )

    # ------------------------------------------------------------------
    # Narrative generator for specific results
    # ------------------------------------------------------------------

    def narrate(
        self,
        components: CurveShockComponents,
        aggregate_df: pd.DataFrame,
    ) -> str:
        """Build a context-specific narrative from actual decomposition results.

        Parameters
        ----------
        components:
            The level/slope/curvature shock decomposition from the scenario.
        aggregate_df:
            Output of :func:`src.risk.pnl_decomposition.aggregate_lsc` with
            columns ``factor, pnl, dv01_contribution, pct_of_total``.
        """
        lines: list[str] = ["## Yield-curve P&L decomposition\n"]

        # --- Shock characterisation ---
        lines.append("### Scenario shock profile\n")
        lines.append(self._characterise_shocks(components))

        # --- P&L attribution ---
        lines.append("\n### P&L attribution\n")
        if aggregate_df.empty:
            lines.append("No rate P&L to attribute.")
            return "\n".join(lines)

        lines.append("| Factor | P&L | DV01 contribution | % of gross |")
        lines.append("|--------|----:|------------------:|----------:|")
        for _, row in aggregate_df.iterrows():
            lines.append(
                f"| {row['factor']} | {row['pnl']:,.0f} | {row['dv01_contribution']:,.1f} | "
                f"{row['pct_of_total']:.1f}% |"
            )

        # --- Dominant factor interpretation ---
        dominant = aggregate_df.loc[aggregate_df["pct_of_total"].idxmax()]
        lines.append(f"\n### Why {dominant['factor'].lower()} dominates\n")
        lines.append(self._explain_dominant(dominant["factor"], components))

        # --- Macro context ---
        lines.append("\n### Macro interpretation\n")
        lines.append(self._macro_context(components))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _characterise_shocks(self, c: CurveShockComponents) -> str:
        parts: list[str] = []
        parts.append(f"- **Level**: {c.level_bp:+.1f} bp (parallel component)")

        if c.slope_bp > 5:
            parts.append(f"- **Slope**: {c.slope_bp:+.1f} bp (**steepening** — long rates rose more than short)")
        elif c.slope_bp < -5:
            parts.append(f"- **Slope**: {c.slope_bp:+.1f} bp (**flattening** — short rates rose more than long)")
        else:
            parts.append(f"- **Slope**: {c.slope_bp:+.1f} bp (roughly parallel)")

        if c.curvature_bp > 5:
            parts.append(f"- **Curvature**: {c.curvature_bp:+.1f} bp (belly cheapened relative to wings)")
        elif c.curvature_bp < -5:
            parts.append(f"- **Curvature**: {c.curvature_bp:+.1f} bp (belly richened relative to wings)")
        else:
            parts.append(f"- **Curvature**: {c.curvature_bp:+.1f} bp (minimal curvature shift)")

        return "\n".join(parts)

    def _explain_dominant(self, factor: str, c: CurveShockComponents) -> str:
        if factor == "Level":
            return (
                f"The scenario's average shock of {c.level_bp:+.1f} bp was large relative to "
                f"slope ({c.slope_bp:+.1f} bp) and curvature ({c.curvature_bp:+.1f} bp). "
                f"Most of the portfolio's DV01 is directional — it profits or loses primarily "
                f"from parallel rate moves."
            )
        if factor == "Slope":
            direction = "steepening" if c.slope_bp > 0 else "flattening"
            return (
                f"The {c.slope_bp:+.1f} bp {direction} move dominated because the portfolio "
                f"has asymmetric DV01 across tenors. Positions at opposite ends of the curve "
                f"experienced different shock magnitudes, amplifying the slope component."
            )
        # Curvature
        return (
            f"The {c.curvature_bp:+.1f} bp curvature shift dominated because the portfolio "
            f"has belly exposure that moved differently from the wings. Butterfly-like positioning "
            f"or mid-tenor concentration explains why curvature is the largest P&L driver."
        )

    def _macro_context(self, c: CurveShockComponents) -> str:
        parts: list[str] = []

        if c.level_bp > 20:
            parts.append(
                "**Bear move**: rates rose across the board. Possible triggers include "
                "hawkish central-bank guidance, higher-than-expected inflation, or EM risk "
                "repricing."
            )
        elif c.level_bp < -20:
            parts.append(
                "**Bull move**: rates fell broadly. Possible triggers include dovish policy "
                "pivot, growth slowdown, or flight-to-quality flows."
            )

        if c.slope_bp > 10:
            if c.level_bp > 0:
                parts.append(
                    "**Bear steepener**: long-term yields rose on inflation expectations or "
                    "rising term premium while the front end was partially anchored by "
                    "current policy rates."
                )
            else:
                parts.append(
                    "**Bull steepener**: front-end yields fell aggressively (rate-cut "
                    "expectations) while the long end lagged — consistent with aggressive "
                    "easing cycles."
                )
        elif c.slope_bp < -10:
            if c.level_bp > 0:
                parts.append(
                    "**Bear flattener**: short-end yields rose faster from central-bank "
                    "rate hikes, compressing the term spread."
                )
            else:
                parts.append(
                    "**Bull flattener**: long-end yields fell more than the front — "
                    "recession fears or flight-to-quality drove long-duration rallies."
                )

        if abs(c.curvature_bp) > 15:
            direction = "cheapened" if c.curvature_bp > 0 else "richened"
            parts.append(
                f"**Curvature shift**: the belly {direction} relative to the wings. "
                f"This often reflects supply/demand imbalances in intermediate maturities "
                f"or butterfly hedge rebalancing."
            )

        if not parts:
            parts.append(
                "The shock profile is relatively balanced across level, slope, and "
                "curvature — no single macro narrative dominates."
            )

        return "\n\n".join(parts)
