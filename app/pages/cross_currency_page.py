"""Cross-currency curve diagnostics page."""

from __future__ import annotations

import streamlit as st

from src.curves import build_discount_curve, extract_fx_implied_basis

from app.helpers import format_bp, validate_positive


def render(controls: dict[str, float | str | bool]) -> None:
    """Render one-tenor FX-implied basis diagnostics."""

    st.subheader("Cross-currency diagnostics")

    tenor = float(controls["tenor_years"])
    spot = float(controls["spot"])
    forward = spot + float(controls["forward_points"])
    dom = float(controls["domestic_ois"])
    foreign = float(controls["foreign_ois"])

    validate_positive("Spot", spot)
    validate_positive("Forward", forward)
    validate_positive("Tenor", tenor)

    domestic_df = build_discount_curve({tenor: dom})
    foreign_df = build_discount_curve({tenor: foreign})
    implied = extract_fx_implied_basis(
        spot=spot,
        forward_by_tenor={tenor: forward},
        domestic_df_curve=domestic_df,
        foreign_ois_df_curve=foreign_df,
    )
    basis_residual = implied[tenor]["basis_residual"]

    st.metric("FX-implied basis residual", format_bp(basis_residual * 1e4))
    if bool(controls["show_details"]):
        st.json(implied)
