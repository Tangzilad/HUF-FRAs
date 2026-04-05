"""CIP basis analytics page."""

from __future__ import annotations

import streamlit as st

from src.analytics import compute_raw_cip_deviation, point_in_time_and_panel

from app.helpers import format_bp, to_panel_dataframe, validate_positive


def render(controls: dict[str, float | str | bool]) -> None:
    """Render CIP basis panel using analytics from ``src.analytics``."""

    st.subheader("Covered Interest Parity (CIP) basis")

    tenor = float(controls["tenor_years"])
    spot = float(controls["spot"])
    forward = spot + float(controls["forward_points"])
    dom = float(controls["domestic_ois"])
    foreign = float(controls["foreign_ois"])

    validate_positive("Spot", spot)
    validate_positive("Forward", forward)
    validate_positive("Tenor", tenor)

    spot_series, forward_df, dom_df, for_df = to_panel_dataframe(
        spot=spot,
        forward=forward,
        domestic_ois=dom,
        foreign_ois=foreign,
        tenor_years=[tenor],
    )
    panel = compute_raw_cip_deviation(spot_series, forward_df, dom_df, for_df)
    snapshot = point_in_time_and_panel(panel)["point_in_time"]
    raw_basis = float(snapshot[("raw_basis_bp", tenor)].iloc[0])

    st.metric("Raw CIP basis", format_bp(raw_basis))
    if bool(controls["show_details"]):
        st.dataframe(snapshot)
