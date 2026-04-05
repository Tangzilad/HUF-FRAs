from __future__ import annotations

from typing import Any, Callable

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


def _render_home(controls: Any) -> None:
    from app.pages import render_home_page

    render_home_page(controls)


def _render_cip(controls: Any) -> None:
    from app.pages import render_cip_page

    render_cip_page(controls)


def _render_cross_currency(controls: Any) -> None:
    from app.pages import render_cross_currency_page

    render_cross_currency_page(controls)


def _render_short_rate(controls: Any) -> None:
    from app.pages import render_short_rate_page

    render_short_rate_page(controls)


def _render_risk_pnl(controls: Any) -> None:
    from app.pages import render_risk_pnl_page

    render_risk_pnl_page(controls)


def _render_stress_lab(controls: Any) -> None:
    from app.pages import render_stress_lab_page

    render_stress_lab_page(controls)


def build_routes() -> dict[str, Callable[[Any], None]]:
    return {
        "Start here": _render_home,
        "CIP basis": _render_cip,
        "Cross-currency": _render_cross_currency,
        "Short-rate FRA": _render_short_rate,
        "Risk P&L": _render_risk_pnl,
        "Stress Lab": _render_stress_lab,
    }


PAGE_ROUTES = build_routes()


def main() -> None:
    """Main Streamlit entrypoint for analytics UI."""

    import streamlit as st

    from app.state import initialize_state
    from app.widgets import render_sidebar_controls

    PAGE_DESCRIPTIONS = {
        "CIP basis": "Explore how covered interest parity links FX forwards to interest rate differentials, and detect funding stress through basis deviations.",
        "Cross-currency": "Inspect FX-implied basis residuals that reveal whether cross-currency curves are internally consistent with observed forwards.",
        "Short-rate FRA": "Price FRA contracts using stochastic short-rate models (Ho-Lee / Hull-White) and analyse convexity adjustments across volatility regimes.",
        "Risk P&L": "Decompose scenario P&L into rates, FX, and basis drivers while surfacing roll-down and convexity effects by tenor bucket.",
        "Stress Lab": "Prototype stress shocks, blend custom rates/FX/basis moves, and evaluate hedge what-if optimization outcomes.",
    }

    st.set_page_config(page_title="HUF FRA Analytics", page_icon="📈", layout="wide")
    st.title("HUF FRA Analytics")
    initialize_state()
    controls = render_sidebar_controls()

    is_learning = getattr(controls, "explanation_mode", "basic") == "learning"

    page = str(getattr(controls, "active_page", "Start here"))

    if is_learning and page in PAGE_DESCRIPTIONS:
        st.info(PAGE_DESCRIPTIONS.get(page, ""), icon="💡")

    PAGE_ROUTES[page](controls)


if __name__ == "__main__":
    main()
