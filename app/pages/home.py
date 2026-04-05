"""Trader-facing landing page for the Streamlit workbench."""

from __future__ import annotations

from typing import Any

import streamlit as st


def _is_learning(controls: Any) -> bool:
    mode = getattr(controls, "explanation_mode", None) or controls.get("explanation_mode", "basic")
    return str(mode).lower() == "learning"


def render(controls: dict[str, float | str | bool]) -> None:
    """Render concise onboarding guidance for traders."""

    learning = _is_learning(controls)

    st.subheader("Start here")
    st.write(
        "This desk-facing workbench helps you test consistency across HUF FRA, cross-currency basis, and short-rate "
        "interpretation so you can separate curve shape, funding dislocation, and model convexity from headline moves."
    )

    st.info("**Suggested path:** CIP basis → Cross-currency → Short-rate FRA", icon="🧭")

    st.write(
        "Work in sequence rather than jumping between pages. Start with **CIP basis** to check whether FX forwards "
        "and rate differentials are coherent, then move to **Cross-currency** to inspect residual basis, and use "
        "**Short-rate FRA** once market structure is clear and the task is pricing or convexity comparison."
    )
    st.write(
        "**CIP basis** is the fastest rich/cheap parity check. **Cross-currency** is the diagnostic view for funding, "
        "basis, and quote consistency. **Short-rate FRA** is the valuation view for model choice, volatility "
        "assumptions, and the forward/futures gap."
    )
    st.write(
        "Use synthetic inputs first to understand mechanics, then switch to uploaded data only after tenor labels, "
        "quote units, and conventions are clean. Change one driver at a time so each output move is interpretable."
    )
    st.write(
        "Read outputs by sign, magnitude, and persistence. Near-zero basis typically means inputs are broadly "
        "coherent; persistent residuals are more likely to matter for funding, hedge design, or relative-value views."
    )
    st.write(
        "Use **Learning** mode when forming a trade idea or reviewing an unfamiliar linkage; switch to **Basic** mode "
        "for faster repeat checks once your question is clear."
    )
    st.caption(
        "Analytical support only: this workbench is not production execution infrastructure. Results depend on quote "
        "hygiene, conventions, and model simplifications."
    )

    if learning:
        with st.expander("How to use this workbench", expanded=False):
            st.markdown(
                "Start each session by checking data coherence before valuation detail. If a discrepancy appears, "
                "validate inputs first (tenor alignment, quote units, conventions), then revisit model assumptions. "
                "Use page-level explainers for depth only when the trading question requires it."
            )
