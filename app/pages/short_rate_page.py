"""Short-rate FRA analytics page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.models.short_rate import HoLeeModel, convexity_adjustment_summary
from src.models.short_rate.fra import simulate_fra_distribution
from src.explainers.short_rate import ShortRateExplainer, summarize_convexity_table
from src.explainers.simulation_narrative import FRASimContext, SimulationNarrativeGenerator

from app.calculation_windows import render_equation_window


def _is_learning(controls: Any) -> bool:
    mode = getattr(controls, "explanation_mode", None) or controls.get("explanation_mode", "basic")
    return str(mode).lower() == "learning"


def render(controls: dict[str, float | str | bool]) -> None:
    """Render FRA convexity adjustment summary from short-rate analytics."""

    st.subheader("Short-rate FRA")
    learning = _is_learning(controls)
    st.caption("Role on path: model / convexity interpretation for FRA-vs-futures valuation.")

    if learning:
        with st.expander("How to read this page", expanded=False):
            st.markdown(
                "Read this page as the **valuation interpretation layer**: after parity and basis checks, ask how "
                "model volatility and settlement mechanics translate into FRA pricing differences. Then move to "
                "**Risk P&L** to see what those assumptions do to portfolio outcomes under scenarios."
            )

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
    t1 = max(0.25, tenor / 2.0)
    t2 = max(0.5, tenor)
    convexity_bp = float(summary["convexity_adjustment"].iloc[0] * 1e4)
    render_equation_window(
        title="How convexity adjustment is calculated",
        equations=[
            r"\mathrm{Convexity\ Adjustment} = \mathbb{E}[R_{\mathrm{futures}}] - \mathbb{E}[R_{\mathrm{FRA}}]",
            r"\mathrm{Convexity\ Adjustment}_{bp} = 10{,}000 \times \left(\mathbb{E}[R_{\mathrm{futures}}] - \mathbb{E}[R_{\mathrm{FRA}}]\right)",
        ],
        notes=[
            f"Window = {t1:.4f}y to {t2:.4f}y; paths = 1500; sigma regimes = 0.5%, 1.0%, 2.0%",
            f"Base displayed adjustment = {convexity_bp:.4f} bp",
            "Values come from Monte Carlo FRA vs futures rates using Ho-Lee dynamics.",
        ],
    )

    # --- FRA simulation with auto-generated explanation ---
    sim_model = HoLeeModel(sigma=0.01)
    fra_result = simulate_fra_distribution(
        sim_model, curve, start=t1, end=t2, n_paths=1_500, seed=42,
    )

    st.markdown("---")
    fra_ctx = FRASimContext(
        model_name="Ho-Lee",
        sigma=0.01,
        n_paths=1_500,
        tenor_label=f"{int(t1*12)}x{int(t2*12)}",
        start=t1,
        end=t2,
        fra_pnl=fra_result.pnl,
        fra_forward=fra_result.fra_forward,
        futures_rate=fra_result.futures_rate,
    )
    narrative = SimulationNarrativeGenerator().explain_fra_simulation(
        context=fra_ctx,
        convexity_summary=summary,
    )
    if learning:
        with st.expander("Auto-generated simulation explanation", expanded=True):
            st.markdown(narrative)

    if learning:
        st.markdown("---")
        st.markdown("**How to read the convexity table:**")
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
