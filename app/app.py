"""Thin app bootstrap wiring state init + shared compute pipeline."""

from __future__ import annotations

from typing import Any, Dict

from app.helpers import ensure_pipeline_outputs
from app.pages import risk_page, valuation_page, xccy_page
from app.state import init_state


def run_app(session_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Entrypoint used by UI runtime (e.g., Streamlit) and tests.

    `init_state()` is called once and page payloads consume pipeline outputs rather
    than triggering local recomputation.
    """

    state = session_state if session_state is not None else {}
    init_state(state)
    outputs = ensure_pipeline_outputs(state)

    return {
        "valuation": valuation_page(outputs),
        "risk": risk_page(outputs),
        "xccy": xccy_page(outputs),
    }
