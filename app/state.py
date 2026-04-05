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
