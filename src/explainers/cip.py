"""Narrative explainer for Covered Interest Parity (CIP) premium diagnostics.

This module provides a compact, reusable explainer that translates CIP inputs and
outputs into desk-facing language in Queen's English while retaining quantitative
terminology.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class CIPConventions:
    """Market conventions required to interpret CIP inputs correctly.

    Attributes:
        fx_quote: FX quote direction. Expected: ``domestic per foreign``.
        compounding: Covered-parity mapping convention. Expected: ``simple annual``.
        tenor_unit: Unit for tenor maturity. Expected: ``years``.
        rate_unit: Unit for domestic and foreign rates. Expected: ``decimal``.
    """

    fx_quote: str = "domestic per foreign"
    compounding: str = "simple annual"
    tenor_unit: str = "years"
    rate_unit: str = "decimal"


@dataclass(frozen=True)
class CIPExplainer:
    """Generate a structured interpretation of CIP premium and basis dislocations.

    The explainer focuses on four layers:
    1. Formula and premium decomposition.
    2. Input requirements and quality controls.
    3. Statistical interpretation of persistence/regime behaviour.
    4. Output interpretation for funding pressure and implementation choices.
    """

    conventions: CIPConventions = CIPConventions()

    def explain(
        self,
        *,
        spot: float,
        forward_points: float,
        tenor_years: float,
        domestic_rate: float,
        foreign_rate: float,
        premium_bp: Optional[float] = None,
        raw_basis_bp: Optional[float] = None,
        purified_basis_bp: Optional[float] = None,
        persistence_half_life_days: Optional[float] = None,
        regime_label: Optional[str] = None,
        regime_probability: Optional[float] = None,
        diagnostics: Optional[Mapping[str, float]] = None,
    ) -> str:
        """Return a human-readable CIP narrative.

        Args:
            spot: Spot FX level quoted domestic-per-foreign.
            forward_points: Forward points in spot quote units (F - S).
            tenor_years: Forward maturity in years.
            domestic_rate: Domestic benchmark funding rate in decimal terms.
            foreign_rate: Foreign benchmark funding rate in decimal terms.
            premium_bp: Optional CIP premium in basis points.
            raw_basis_bp: Optional raw basis estimate in basis points.
            purified_basis_bp: Optional purified basis estimate in basis points.
            persistence_half_life_days: Optional half-life estimate for premium mean reversion.
            regime_label: Optional inferred market regime (e.g., "stress", "normal").
            regime_probability: Optional model probability for the active regime.
            diagnostics: Optional extra diagnostics (name -> value).
        """

        if spot <= 0:
            raise ValueError("spot must be strictly positive")
        if tenor_years <= 0:
            raise ValueError("tenor_years must be strictly positive")

        forward = spot + forward_points
        if forward <= 0:
            raise ValueError("spot + forward_points must be strictly positive")

        fx_implied_domestic = (((forward / spot) * (1.0 + foreign_rate * tenor_years)) - 1.0) / tenor_years
        implied_premium_bp = (fx_implied_domestic - domestic_rate) * 10_000.0

        effective_premium_bp = premium_bp if premium_bp is not None else implied_premium_bp

        lines = [
            "CIP formula and premium decomposition",
            "- Covered parity mapping (simple annual compounding):",
            "  r_dom,implied = (((F/S) * (1 + r_for * T)) - 1) / T.",
            f"- With S={spot:.6g}, forward points={forward_points:.6g}, T={tenor_years:.6g},",
            f"  the implied domestic rate is {fx_implied_domestic:.6%} versus observed domestic rate {domestic_rate:.6%}.",
            f"- CIP premium = (r_dom,implied - r_dom,observed) × 10,000 = {effective_premium_bp:+.2f} bp.",
        ]

        if raw_basis_bp is not None and purified_basis_bp is not None:
            credit_liquidity_contamination = raw_basis_bp - purified_basis_bp
            lines.extend(
                [
                    "- Raw versus purified basis decomposition:",
                    f"  raw basis {raw_basis_bp:+.2f} bp, purified basis {purified_basis_bp:+.2f} bp,",
                    f"  implying {credit_liquidity_contamination:+.2f} bp attributable to local credit/liquidity contamination.",
                ]
            )

        lines.extend(
            [
                "",
                "Input requirements",
                "- Spot and forwards must share the same quote direction: domestic currency per unit of foreign currency.",
                "- Forward input should be provided as outright or forward points in the same quote units as spot.",
                "- Domestic and foreign rates should be tenor-matched, annualised, and expressed in decimal form (0.05 = 5%).",
                "- Tenor must be measured in years and aligned with the compounding convention (simple annual here).",
            ]
        )

        if persistence_half_life_days is not None or regime_label or regime_probability is not None:
            lines.extend(["", "Statistical interpretation"])
            if persistence_half_life_days is not None:
                if persistence_half_life_days > 60:
                    persistence_text = "high persistence"
                elif persistence_half_life_days > 20:
                    persistence_text = "moderate persistence"
                else:
                    persistence_text = "fast mean reversion"
                lines.append(
                    f"- Estimated half-life is {persistence_half_life_days:.1f} days, consistent with {persistence_text} in the premium process."
                )
            if regime_label:
                if regime_probability is not None:
                    lines.append(
                        f"- Regime classifier indicates '{regime_label}' with probability {regime_probability:.1%}."
                    )
                else:
                    lines.append(f"- Regime classifier indicates '{regime_label}'.")

        lines.extend(["", "Output interpretation"])

        sign = "positive" if effective_premium_bp > 0 else "negative" if effective_premium_bp < 0 else "flat"
        if sign == "negative":
            lines.extend(
                [
                    "- Negative premium/basis indicates a basis dislocation where synthetic domestic funding is cheaper than cash funding.",
                    "- This often aligns with USD shortage dynamics or cross-currency swap receiving pressure in the foreign leg.",
                    "- Trade/hedge implication: hedgers may lock in cheaper synthetic funding, while relative-value desks may position for basis normalisation.",
                ]
            )
        elif sign == "positive":
            lines.extend(
                [
                    "- Positive premium/basis indicates synthetic domestic funding is rich versus cash funding.",
                    "- This can signal balance-sheet scarcity in dealers providing basis warehousing or one-sided hedge demand.",
                    "- Trade/hedge implication: funding desks may prefer cash borrowing, while macro books may fade extreme richness if carry and risk limits permit.",
                ]
            )
        else:
            lines.append("- Near-zero premium suggests limited observable basis dislocation at the selected horizon.")

        if diagnostics:
            lines.extend(["", "Supplementary diagnostics"])
            for key, value in diagnostics.items():
                lines.append(f"- {key}: {value:.6g}")

        lines.extend(
            [
                "",
                "Assumptions and limitations",
                "- Quote timing must be aligned: asynchronous spot/forward/rate timestamps can generate spurious basis prints.",
                "- Day-count, holiday calendars, spot-lag, and broken-date interpolation mismatches can bias inferred parity gaps.",
                "- Convention mismatches (quote direction, compounding, or rate units) may invert the economic interpretation.",
                "- Statistical regime labels are model-dependent and should be treated as probabilistic diagnostics rather than certainties.",
            ]
        )

        return "\n".join(lines)
