"""Cross-currency curve diagnostics page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.curves import build_discount_curve, extract_fx_implied_basis
from src.explainers.cross_currency import CrossCurrencyExplainer

from app.calculation_windows import render_equation_window
from app.helpers import format_bp, validate_positive


def _is_learning(controls: Any) -> bool:
    mode = getattr(controls, "explanation_mode", None) or controls.get("explanation_mode", "basic")
    return str(mode).lower() == "learning"


def render(controls: dict[str, float | str | bool]) -> None:
    """Render one-tenor FX-implied basis diagnostics."""

    st.subheader("Cross-currency diagnostics")
    learning = _is_learning(controls)
    st.caption("Role on path: basis / structural consistency check after CIP.")

    if learning:
        with st.expander("How to read this page", expanded=False):
            st.markdown(
                "Use this page to test whether rates curves and FX forwards are structurally aligned once the "
                "headline CIP gap is known. Treat the residual as a **consistency diagnostic**, then move to "
                "**Short-rate FRA** to interpret valuation impact through model and convexity assumptions."
            )

    if learning:
        with st.expander("What is cross-currency basis?", expanded=False):
            st.markdown(
                "When you combine domestic and foreign interest rate curves with FX forwards, "
                "the resulting **implied basis residual** tells you whether all three markets are "
                "internally consistent.\n\n"
                "**How it works:**\n"
                "1. Build discount curves from domestic (HUF) and foreign (USD) OIS rates\n"
                "2. Use spot and forward FX to compute what the basis *should* be under no-arbitrage\n"
                "3. The residual is the gap — a non-zero value reveals funding frictions, credit effects, "
                "or market segmentation\n\n"
                "A large residual may indicate opportunities for basis traders or signal stress in FX funding markets."
            )
        with st.expander("Deep dive — Cross-currency curve construction", expanded=False):
            st.markdown(CrossCurrencyExplainer().render_full_markdown())

    tenor = float(controls["tenor_years"])
    spot = float(controls["spot"])
    forward = spot + float(controls["forward_points"])
    dom = float(controls["domestic_ois"])
    foreign = float(controls["foreign_ois"])

    validate_positive("Spot", spot)
    validate_positive("Forward", forward)
    validate_positive("Tenor", tenor)

    if learning:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Domestic (HUF) side**")
            st.markdown(f"- OIS rate: `{dom:.4f}` ({dom*100:.2f}%)")
            st.markdown(f"- Spot FX: `{spot:.2f}` HUF per USD")
        with col2:
            st.markdown("**Foreign (USD) side**")
            st.markdown(f"- OIS rate: `{foreign:.4f}` ({foreign*100:.2f}%)")
            st.markdown(f"- Forward FX: `{forward:.2f}` HUF per USD")

    domestic_df = build_discount_curve({tenor: dom})
    foreign_df = build_discount_curve({tenor: foreign})
    implied = extract_fx_implied_basis(
        spot=spot,
        forward_by_tenor={tenor: forward},
        domestic_df_curve=domestic_df,
        foreign_ois_df_curve=foreign_df,
    )
    basis_residual = implied[tenor]["basis_residual"]
    basis_bp = basis_residual * 1e4

    st.metric("FX-implied basis residual", format_bp(basis_bp))
    render_equation_window(
        title="How FX-implied basis residual is calculated",
        equations=[
            r"P_d(T) = e^{-r_d T},\quad P_f(T) = e^{-r_f T}",
            r"F_{\mathrm{theory}} = S \times \frac{P_f(T)}{P_d(T)}",
            r"\mathrm{Basis\ Residual}_{bp} = 10{,}000 \times \left(\frac{F_{\mathrm{mkt}}}{F_{\mathrm{theory}}} - 1\right)",
        ],
        notes=[
            f"S = {spot:.6f}, F_mkt = {forward:.6f}, T = {tenor:.6f}",
            f"r_d = {dom:.6f}, r_f = {foreign:.6f}",
            f"Computed residual = {basis_bp:.4f} bp",
        ],
    )

    if learning:
        if abs(basis_bp) < 3:
            st.success("Residual is near zero — curves and FX forwards are consistent. No significant basis dislocation.")
        else:
            direction = "wider" if basis_bp > 0 else "tighter"
            st.warning(
                f"Residual of {basis_bp:.1f} bp suggests the implied basis is {direction} than what "
                f"the OIS curves and FX forwards jointly predict. This could reflect funding stress, "
                f"credit effects, or quote staleness."
            )

    if bool(controls["show_details"]):
        if learning:
            st.caption(
                "The JSON below shows the full decomposition for each tenor: discount factors, "
                "implied forward, theoretical forward, and the basis residual."
            )
        st.json(implied)
