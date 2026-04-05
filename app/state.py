from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any


STATE_KEY_INITIALIZED = "initialized"
STATE_KEY_NOTIONAL = "notional"
STATE_KEY_FRA_PAIR = "fra_pair"
STATE_KEY_COMPUTE_FINGERPRINT = "compute_fingerprint"
STATE_KEY_PIPELINE_OUTPUTS = "pipeline_outputs"


DEFAULT_STATE: dict[str, Any] = {
    "active_page": "CIP basis",
    "tenor_years": 1.0,
    "spot": 365.0,
    "forward_points": 2.5,
    "domestic_ois": 0.065,
    "foreign_ois": 0.045,
    "show_details": True,
}


def default_payload() -> dict[str, Any]:
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
            {
                "trade_id": "XCCY1",
                "instrument": "XCCY_BasisSwap",
                "notional": 7_500_000,
                "tenor_bucket": "belly",
                "basis01": -900.0,
            },
            {
                "trade_id": "FXFWD1",
                "instrument": "FX_Forward",
                "notional": 5_000_000,
                "tenor_bucket": "front",
                "fx_delta": -1_200_000.0,
            },
        ],
        "cip": {
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "tenors": tenors,
            "spot": [360.0, 361.0, 360.5],
            "domestic_ois": [[0.06, 0.061, 0.059], [0.06, 0.061, 0.059], [0.06, 0.061, 0.059]],
            "foreign_ois": [[0.05, 0.049, 0.047], [0.05, 0.049, 0.047], [0.05, 0.049, 0.047]],
        },
    }


def build_state(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build state payload with optional shallow overrides."""

    state = default_payload()
    if overrides:
        state.update(deepcopy(overrides))
    return state


def compute_fingerprint_from_state(state: dict[str, Any]) -> str:
    """Compute deterministic fingerprint from cache-driving inputs."""

    payload = {
        "fra_pair": state.get(STATE_KEY_FRA_PAIR),
        "notional": state.get(STATE_KEY_NOTIONAL),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def init_state(state: dict[str, Any]) -> None:
    """Initialize pure-python state container used by tests/pipeline caches."""

    if state.get(STATE_KEY_INITIALIZED):
        return

    state.setdefault(STATE_KEY_NOTIONAL, 1_000_000.0)
    state.setdefault(STATE_KEY_FRA_PAIR, "3x6")
    state[STATE_KEY_INITIALIZED] = True
    state[STATE_KEY_COMPUTE_FINGERPRINT] = compute_fingerprint_from_state(state)


def initialize_state() -> None:
    """Ensure all expected keys exist in ``st.session_state`` if Streamlit is installed."""

    try:
        import streamlit as st
    except Exception:
        return

    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)


def sync_state(updates: dict[str, Any]) -> None:
    """Apply state updates to ``st.session_state`` if Streamlit is installed."""

    try:
        import streamlit as st
    except Exception:
        return

    for key, value in updates.items():
        st.session_state[key] = value
