"""Short-rate FRA analytics page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.models.short_rate import HoLeeModel, convexity_adjustment_summary


def render(controls: dict[str, float | str | bool]) -> None:
    """Render FRA convexity adjustment summary from short-rate analytics."""

    st.subheader("Short-rate FRA convexity")

    dom = float(controls["domestic_ois"])
    tenor = float(controls["tenor_years"])
    curve = pd.DataFrame(
        {
            "t": [0.25, 0.5, 1.0, 2.0, 5.0],
            "zero_rate": [dom - 0.002, dom - 0.001, dom, dom + 0.001, dom + 0.002],
        }
    )

    model = HoLeeModel(sigma=0.01)
    summary = convexity_adjustment_summary(
        model=model,
        curve=curve,
        tenors=[(max(0.25, tenor / 2.0), max(0.5, tenor))],
        vol_regimes=[0.005, 0.01, 0.02],
        n_paths=1_500,
        seed=42,
    )

    st.dataframe(summary)
