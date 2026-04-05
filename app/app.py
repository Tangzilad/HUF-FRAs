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

    PAGE_DESCRIPTIONS = {
        "CIP basis": "Explore how covered interest parity links FX forwards to interest rate differentials, and detect funding stress through basis deviations.",
        "Cross-currency": "Inspect FX-implied basis residuals that reveal whether cross-currency curves are internally consistent with observed forwards.",
        "Short-rate FRA": "Price FRA contracts using stochastic short-rate models (Ho-Lee / Hull-White) and analyse convexity adjustments across volatility regimes.",
    }

    st.set_page_config(page_title="HUF FRA Analytics", page_icon="📈", layout="wide")
    st.title("HUF FRA Analytics")
    initialize_state()
    controls = render_sidebar_controls()

    is_learning = getattr(controls, "explanation_mode", "basic") == "learning"

    if is_learning:
        with st.expander("Welcome — What is this toolkit?", expanded=False):
            st.markdown(
                "This interactive workbench lets you explore **Hungarian forint (HUF) forward rate agreement** "
                "analytics step by step. It covers three core areas:\n\n"
                "| Page | What you'll learn |\n"
                "|------|-------------------|\n"
                "| **CIP basis** | How covered interest parity works and what basis deviations signal |\n"
                "| **Cross-currency** | How domestic and foreign curves combine with FX to produce consistent pricing |\n"
                "| **Short-rate FRA** | How stochastic models price FRAs and why convexity adjustments matter |\n\n"
                "**Tip:** Use the sidebar controls on the left to change inputs. "
                "Hover over any control's **?** icon for a quick explanation. "
                "Switch to *Basic* mode in the sidebar to hide learning panels."
            )

    page = str(getattr(controls, "active_page", "CIP basis"))

    if is_learning:
        st.info(PAGE_DESCRIPTIONS.get(page, ""), icon="💡")

    routes[page](controls)


if __name__ == "__main__":
    main()
