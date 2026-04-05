from __future__ import annotations

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

    from app.pages import render_cip_page, render_cross_currency_page, render_short_rate_page
    from app.state import initialize_state
    from app.widgets import render_sidebar_controls

    routes = {
        "CIP basis": render_cip_page,
        "Cross-currency": render_cross_currency_page,
        "Short-rate FRA": render_short_rate_page,
    }

    st.set_page_config(page_title="HUF FRA Analytics", page_icon="📈", layout="wide")
    st.title("HUF FRA Analytics")
    initialize_state()
    controls = render_sidebar_controls()
    page = str(getattr(controls, "active_page", "CIP basis"))
    routes[page](controls)


if __name__ == "__main__":
    main()
