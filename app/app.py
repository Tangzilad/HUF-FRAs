from __future__ import annotations

from typing import Any, Dict

from .helpers import build_curve_table, run_cip_path, run_pricing_engine, run_risk_engine
from .state import build_state


def boot(state_overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Boot app engines and return their deterministic outputs."""

    payload = build_state(state_overrides)
    return {
        "curves": build_curve_table(payload),
        "pricing": run_pricing_engine(payload),
        "risk": run_risk_engine(payload),
        "cip": run_cip_path(payload),
    }
"""Main Streamlit entrypoint for analytics UI."""

from __future__ import annotations

import streamlit as st

from app.pages import render_cip_page, render_cross_currency_page, render_short_rate_page
from app.state import initialize_state
from app.widgets import render_sidebar_controls

ROUTES = {
    "CIP basis": render_cip_page,
    "Cross-currency": render_cross_currency_page,
    "Short-rate FRA": render_short_rate_page,
}


def main() -> None:
    """Bootstrap app state and dispatch to the selected page renderer."""

    st.set_page_config(page_title="HUF FRA Analytics", page_icon="📈", layout="wide")
    st.title("HUF FRA Analytics")
    initialize_state()
    controls = render_sidebar_controls()

    page = str(controls["active_page"])
    ROUTES[page](controls)


if __name__ == "__main__":
    main()
