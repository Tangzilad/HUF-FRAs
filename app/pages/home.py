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

    st.subheader("HUF FRA Analytics — Start here")
    st.write(
        "Desk tool for linking parity checks, basis diagnostics, FRA valuation, portfolio risk attribution, and stress "
        "testing so you can separate structure from noise."
    )

    st.info(
        "**Suggested path:** CIP basis -> Cross-currency -> Short-rate FRA -> Risk P&L -> Stress Lab",
        icon="🧭",
    )

    st.write(
        "Run pages in order. **CIP basis** checks parity coherence, **Cross-currency** isolates funding dislocation, "
        "**Short-rate FRA** prices and compares model sensitivity, **Risk P&L** maps exposures into explainable "
        "carry/curve/vol buckets, and **Stress Lab** tests hedge robustness under shocks."
    )
    st.write(
        "Use synthetic scenarios first for intuition and sign checks. Move to uploads only after tenor mapping, quote "
        "units, calendars, and day-count conventions are validated."
    )
    st.write(
        "Interpretation guardrails: confirm sign before magnitude, require persistence before conviction, and treat "
        "single-point anomalies as potential data or convention breaks until verified."
    )
    st.write(
        "Use **Learning** mode for setup, linkage review, and first-pass diagnostics; use **Basic** mode for fast "
        "repeat monitoring once the framework is set."
    )
    st.caption(
        "Analytical support only — not execution advice or production pricing infrastructure. Outputs depend on data "
        "quality, conventions, and model assumptions."
    )

    if learning:
        with st.expander("Pedagogy progression", expanded=False):
            st.markdown(
                "**Parity** (CIP) → **basis** (cross-currency residuals) → **model** (FRA valuation choices) → "
                "**portfolio** (risk/P&L attribution) → **hedge** (stress-tested robustness)."
            )
