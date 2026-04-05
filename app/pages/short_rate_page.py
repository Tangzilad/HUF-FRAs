"""Short-rate FRA analytics page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.models.short_rate import HoLeeModel, convexity_adjustment_summary
from src.explainers.short_rate import ShortRateExplainer, summarize_convexity_table


def _is_learning(controls: Any) -> bool:
    mode = getattr(controls, "explanation_mode", None) or controls.get("explanation_mode", "basic")
    return str(mode).lower() == "learning"


def render(controls: dict[str, float | str | bool]) -> None:
    """Render FRA convexity adjustment summary from short-rate analytics."""

    st.subheader("Short-rate FRA convexity")
    learning = _is_learning(controls)

    if learning:
        with st.expander("What is a convexity adjustment?", expanded=False):
            st.markdown(
                "**FRA rates and futures rates are not the same**, even though they reference the same "
                "underlying interest rate period. The difference is the **convexity adjustment**.\n\n"
                "**Why?** Futures settle daily (mark-to-market), while FRAs settle once at maturity. "
                "Daily settlement creates a reinvestment correlation with rates:\n"
                "- When rates rise, futures margins must be posted at higher rates\n"
                "- When rates fall, margins are received at lower rates\n\n"
                "This asymmetry means futures rates are systematically *higher* than FRA forward rates. "
                "The gap grows with:\n"
                "- **Longer tenors** (more time for the effect to compound)\n"
                "- **Higher volatility** (bigger rate moves amplify the asymmetry)\n\n"
                "Below, we simulate this adjustment using the **Ho-Lee model** across different volatility regimes."
            )
        with st.expander("Deep dive — Short-rate model details", expanded=False):
            st.markdown(ShortRateExplainer().explain(model_name="Ho-Lee"))

    dom = float(controls["domestic_ois"])
    tenor = float(controls["tenor_years"])

    if learning:
        st.markdown(
            f"**Setup:** Building a synthetic zero curve anchored at domestic OIS = `{dom:.4f}` "
            f"({dom*100:.2f}%), with tenor = `{tenor:.2f}y`. "
            f"Three volatility regimes (0.50%, 1.00%, 2.00%) are tested to show how "
            f"the convexity adjustment scales with rate uncertainty."
        )

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

    if learning:
        st.caption(
            "Each row shows the convexity adjustment (futures rate minus FRA forward) "
            "for a given volatility regime. Higher vol = larger adjustment."
        )

    st.dataframe(summary, use_container_width=True)

    if learning:
        st.markdown("---")
        st.markdown("**How to read these results:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                "**Low vol (0.50%)**\n\n"
                "Convexity effect is small. FRA and futures rates are nearly identical — "
                "hedging with either instrument is roughly equivalent."
            )
        with col2:
            st.markdown(
                "**Base vol (1.00%)**\n\n"
                "Moderate adjustment. Traders should account for this when comparing "
                "FRA pricing against futures-implied rates."
            )
        with col3:
            st.markdown(
                "**High vol (2.00%)**\n\n"
                "Material adjustment. Ignoring convexity at this vol level could "
                "cause mispricing in hedging and relative value trades."
            )
