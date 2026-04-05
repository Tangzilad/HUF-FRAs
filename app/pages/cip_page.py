"""CIP basis analytics page."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.analytics import compute_raw_cip_deviation, point_in_time_and_panel
from src.explainers.cip import CIPExplainer

from app.calculation_windows import render_equation_window
from app.helpers import format_bp, to_panel_dataframe, validate_positive


def _is_learning(controls: Any) -> bool:
    mode = getattr(controls, "explanation_mode", None) or controls.get("explanation_mode", "basic")
    return str(mode).lower() == "learning"


def render(controls: dict[str, float | str | bool]) -> None:
    """Render CIP basis panel using analytics from ``src.analytics``."""

    st.subheader("CIP basis")
    learning = _is_learning(controls)
    st.caption("Role on path: parity / no-arbitrage entry check before basis decomposition.")

    if learning:
        with st.expander("How to read this page", expanded=False):
            st.markdown(
                "Start here to answer: **are spot, forward, and rate differentials coherent under no-arbitrage?** "
                "If the raw basis is persistent or large, move to **Cross-currency** next to diagnose whether the "
                "gap is structural basis, funding friction, or curve/quote inconsistency."
            )

    if learning:
        with st.expander("What is CIP basis?", expanded=False):
            explainer = CIPExplainer()
            st.markdown(
                "**Covered Interest Parity (CIP)** states that the cost of hedging FX risk through "
                "forwards should exactly offset the interest rate differential between two currencies. "
                "When this relationship breaks, the gap is called the **CIP basis**.\n\n"
                "A non-zero basis can signal:\n"
                "- Balance-sheet constraints at dealer banks\n"
                "- Collateral or funding stress\n"
                "- Credit risk differentials\n"
                "- Regulatory capital costs\n\n"
                "Below, we compute the raw CIP deviation in **basis points** from your inputs."
            )
        with st.expander("Deep dive — Full CIP explainer", expanded=False):
            st.markdown(explainer.render_full_markdown())

    tenor = float(controls["tenor_years"])
    spot = float(controls["spot"])
    forward = spot + float(controls["forward_points"])
    dom = float(controls["domestic_ois"])
    foreign = float(controls["foreign_ois"])

    validate_positive("Spot", spot)
    validate_positive("Forward", forward)
    validate_positive("Tenor", tenor)

    if learning:
        with st.expander("Current inputs explained", expanded=False):
            st.markdown(
                f"| Input | Value | Meaning |\n"
                f"|-------|-------|---------|\n"
                f"| Spot FX | {spot:.2f} | Current HUF/USD exchange rate |\n"
                f"| Forward FX | {forward:.2f} | Implied forward rate (spot + forward points) |\n"
                f"| Tenor | {tenor:.2f}y | Time horizon for the CIP calculation |\n"
                f"| Domestic OIS | {dom:.4f} | HUF risk-free rate proxy |\n"
                f"| Foreign OIS | {foreign:.4f} | USD risk-free rate proxy |\n"
            )

    spot_series, forward_df, dom_df, for_df = to_panel_dataframe(
        spot=spot,
        forward=forward,
        domestic_ois=dom,
        foreign_ois=foreign,
        tenor_years=[tenor],
    )
    panel = compute_raw_cip_deviation(spot_series, forward_df, dom_df, for_df)
    snapshot = point_in_time_and_panel(panel)["point_in_time"]
    raw_basis = float(snapshot[("raw_basis_bp", tenor)].iloc[0])

    st.metric("Raw CIP basis", format_bp(raw_basis))
    render_equation_window(
        title="How Raw CIP basis is calculated",
        equations=[
            r"F_{\mathrm{CIP}} = S \times \frac{1 + r_d T}{1 + r_f T}",
            r"\mathrm{Raw\ Basis}_{bp} = 10{,}000 \times \left(\frac{F_{\mathrm{mkt}}}{S}\times\frac{1 + r_f T}{1 + r_d T} - 1\right)",
        ],
        notes=[
            f"S = {spot:.6f}, F_mkt = {forward:.6f}, T = {tenor:.6f}",
            f"r_d = {dom:.6f}, r_f = {foreign:.6f}",
            f"Computed raw basis = {raw_basis:.4f} bp",
        ],
    )

    if learning:
        if abs(raw_basis) < 5:
            st.success("The basis is close to zero — CIP holds approximately. No significant funding stress detected at this tenor.")
        elif raw_basis > 0:
            st.warning(f"Positive basis ({raw_basis:.1f} bp) suggests USD funding is relatively cheap, or HUF lenders are demanding a premium.")
        else:
            st.warning(f"Negative basis ({raw_basis:.1f} bp) suggests HUF funding is relatively cheap, or USD borrowers face constraints.")

    if bool(controls["show_details"]):
        if learning:
            st.caption("The table below shows the full CIP deviation panel. Each column represents a tenor-metric combination.")
        st.dataframe(snapshot)
