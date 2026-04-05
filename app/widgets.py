"""Sidebar/form controls for the Streamlit app."""

from __future__ import annotations

import streamlit as st

from .state import sync_state

PAGES = ["CIP basis", "Cross-currency", "Short-rate FRA"]


def render_sidebar_controls() -> dict[str, float | str | bool]:
    """Render sidebar controls and synchronize with session state."""

    with st.sidebar:
        st.header("Controls")
        active_page = st.radio("Page", options=PAGES, index=PAGES.index(st.session_state.active_page))
        tenor_years = st.selectbox("Tenor (years)", options=[0.5, 1.0, 2.0, 5.0], index=1)
        spot = st.number_input("Spot FX", min_value=0.0001, value=float(st.session_state.spot), step=0.5)
        forward_points = st.number_input(
            "Forward points", min_value=-100.0, max_value=100.0, value=float(st.session_state.forward_points), step=0.1
        )
        domestic_ois = st.slider("Domestic OIS", min_value=0.0, max_value=0.2, value=float(st.session_state.domestic_ois))
        foreign_ois = st.slider("Foreign OIS", min_value=0.0, max_value=0.2, value=float(st.session_state.foreign_ois))
        show_details = st.checkbox("Show details", value=bool(st.session_state.show_details))

    updates = {
        "active_page": active_page,
        "tenor_years": tenor_years,
        "spot": spot,
        "forward_points": forward_points,
        "domestic_ois": domestic_ois,
        "foreign_ois": foreign_ois,
        "show_details": show_details,
    }
    sync_state(updates)
    return updates
