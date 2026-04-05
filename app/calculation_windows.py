from __future__ import annotations

from typing import Iterable

import streamlit as st


def render_equation_window(*, title: str, equations: Iterable[str], notes: Iterable[str] | None = None, expanded: bool = False) -> None:
    """Render a reusable collapsible calculation window."""

    with st.expander(title, expanded=expanded):
        st.markdown("### Calculation trail")
        for eq in equations:
            st.latex(eq)

        if notes:
            st.markdown("### Inputs → output")
            for note in notes:
                st.markdown(f"- {note}")
