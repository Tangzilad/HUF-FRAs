from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def default_payload() -> Dict[str, Any]:
    """Return a deterministic representative payload for app engines."""

    tenors = [0.5, 1.0, 2.0]
    return {
        "ois_by_ccy": {
            "HUF": {0.5: 0.065, 1.0: 0.062, 2.0: 0.058},
            "USD": {0.5: 0.050, 1.0: 0.048, 2.0: 0.045},
        },
        "short_rate_curve": {
            "t": [0.25, 0.5, 1.0, 2.0],
            "zero_rate": [0.058, 0.06, 0.061, 0.059],
        },
        "portfolio": [
            {"trade_id": "FRA1", "instrument": "FRA", "notional": 10_000_000, "tenor_bucket": "front", "dv01": -1800.0},
            {"trade_id": "XCCY1", "instrument": "XCCY_BasisSwap", "notional": 7_500_000, "tenor_bucket": "belly", "basis01": -900.0},
            {"trade_id": "FXFWD1", "instrument": "FX_Forward", "notional": 5_000_000, "tenor_bucket": "front", "fx_delta": -1_200_000.0},
        ],
        "cip": {
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "tenors": tenors,
            "spot": [360.0, 361.0, 360.5],
            "domestic_ois": [[0.06, 0.061, 0.059], [0.06, 0.061, 0.059], [0.06, 0.061, 0.059]],
            "foreign_ois": [[0.05, 0.049, 0.047], [0.05, 0.049, 0.047], [0.05, 0.049, 0.047]],
        },
    }


def build_state(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build state payload with optional shallow overrides."""

    state = default_payload()
    if overrides:
        state.update(deepcopy(overrides))
    return state
"""Session-state defaults and synchronization helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st

DEFAULT_STATE: dict[str, Any] = {
    "active_page": "CIP basis",
    "tenor_years": 1.0,
    "spot": 365.0,
    "forward_points": 2.5,
    "domestic_ois": 0.065,
    "foreign_ois": 0.045,
    "show_details": True,
}


def initialize_state() -> None:
    """Ensure all expected keys exist in ``st.session_state``."""

    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)


def sync_state(updates: dict[str, Any]) -> None:
    """Apply state updates in one place for predictable synchronization."""

    for key, value in updates.items():
        st.session_state[key] = value
