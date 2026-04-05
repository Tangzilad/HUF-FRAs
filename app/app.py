from __future__ import annotations

import inspect
from typing import Any

from .helpers import build_curve_table, ensure_pipeline_outputs, run_cip_path, run_pricing_engine, run_risk_engine
from .state import build_state, init_state


def boot(state_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Boot app engines and return deterministic outputs for integration tests."""

    payload = build_state(state_overrides)
    return {
        "curves": build_curve_table(payload),
        "pricing": run_pricing_engine(payload),
        "risk": run_risk_engine(payload),
        "cip": run_cip_path(payload),
    }


def run_app(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Initialize pipeline state and return memoized page payloads."""

    data = state if state is not None else {}
    init_state(data)
    return ensure_pipeline_outputs(data)


def main() -> None:
    """Main Streamlit entrypoint for analytics UI."""

    import streamlit as st

    from app.pages import (
        render_cip_page,
        render_cross_currency_page,
        render_home_page,
        render_risk_pnl_page,
        render_short_rate_page,
        render_stress_lab_page,
    )
    from app.state import initialize_state
    from app.widgets import render_sidebar_controls

    routes = {
        "Start here": render_home_page,
        "CIP basis": render_cip_page,
        "Cross-currency": render_cross_currency_page,
        "Short-rate FRA": render_short_rate_page,
        "Risk P&L": render_risk_pnl_page,
        "Stress Lab": render_stress_lab_page,
    }

    PAGE_DESCRIPTIONS = {
        "CIP basis": "Explore how covered interest parity links FX forwards to interest rate differentials, and detect funding stress through basis deviations.",
        "Cross-currency": "Inspect FX-implied basis residuals that reveal whether cross-currency curves are internally consistent with observed forwards.",
        "Short-rate FRA": "Price FRA contracts using stochastic short-rate models (Ho-Lee / Hull-White) and analyse convexity adjustments across volatility regimes.",
        "Risk P&L": "Decompose scenario P&L by instrument and tenor bucket, then inspect VaR/ES and ladder sensitivity.",
        "Stress Lab": "Build custom shocks and test hedge optimization constraints to compare unhedged versus hedged risk.",
    }

    st.set_page_config(page_title="HUF FRA Analytics", page_icon="📈", layout="wide")
    st.title("HUF FRA Analytics")
    initialize_state()
    controls = render_sidebar_controls()

    is_learning = getattr(controls, "explanation_mode", "basic") == "learning"

    page = str(getattr(controls, "active_page", "Start here"))

    if is_learning and page in PAGE_DESCRIPTIONS:
        st.info(PAGE_DESCRIPTIONS.get(page, ""), icon="💡")

    def render_in_shell(page_label: str) -> None:
        renderer = routes[page_label]
        params = inspect.signature(renderer).parameters
        if len(params) == 0:
            renderer()
            return
        renderer(controls)

    render_in_shell(page)


if __name__ == "__main__":
    main()
