from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.curves.cross_currency import (
    CurveInstrumentSet,
    calibrate_cross_currency_bundle,
    extract_fx_implied_basis,
)
from src.curves.parametric import fit_parametric_curve
from src.visualization.market_diagnostics import (
    plot_basis_term_premium_panel,
    plot_fitted_vs_observed,
)

CHART_CAPTIONS: dict[str, str] = {
    "huf_discount_projection": (
        "HUF projection and discount curves with optional stress overlays. "
        "Use this panel to compare projection-discount spread changes by tenor."
    ),
    "usd_discount_projection": (
        "USD projection and discount curves with optional stress overlays. "
        "Cross-check slope changes against HUF for relative value context."
    ),
    "huf_usd_basis": (
        "HUF-USD basis term structure under base and selected stress scenarios."
    ),
    "implied_forwards": (
        "FX forwards implied by CIP-consistent curves versus stressed adjustments."
    ),
}

SCENARIO_SHOCKS_BP: dict[str, tuple[float, float]] = {
    "parallel": (25.0, 25.0),
    "steepen": (35.0, 5.0),
    "flatten": (5.0, 35.0),
}


def _build_instruments() -> CurveInstrumentSet:
    tenors = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
    huf_ois = {0.25: 0.067, 0.5: 0.066, 1.0: 0.064, 2.0: 0.061, 3.0: 0.059, 5.0: 0.057}
    huf_irs = {0.25: 0.071, 0.5: 0.070, 1.0: 0.068, 2.0: 0.065, 3.0: 0.063, 5.0: 0.060}

    usd_ois = {0.25: 0.050, 0.5: 0.049, 1.0: 0.047, 2.0: 0.044, 3.0: 0.042, 5.0: 0.040}
    usd_irs = {0.25: 0.053, 0.5: 0.052, 1.0: 0.050, 2.0: 0.047, 3.0: 0.045, 5.0: 0.043}

    spot = 362.0
    fx_forwards = {
        0.25: 364.8,
        0.5: 367.1,
        1.0: 371.6,
        2.0: 380.9,
        3.0: 389.2,
        5.0: 406.8,
    }
    xccy_basis = {
        0.25: 0.0018,
        0.5: 0.0019,
        1.0: 0.0021,
        2.0: 0.0024,
        3.0: 0.0025,
        5.0: 0.0027,
    }

    return CurveInstrumentSet(
        ois_by_ccy={"HUF": huf_ois, "USD": usd_ois},
        irs_by_ccy={"HUF": huf_irs, "USD": usd_irs},
        fx_spot={"HUF/USD": spot},
        fx_forwards={"HUF/USD": fx_forwards},
        xccy_basis_by_pair={"HUF/USD": xccy_basis},
    )


def _node_table(curve: Mapping[float, float], stress_name: str | None = None) -> pd.DataFrame:
    tenors = np.array(sorted(curve), dtype=float)
    dfs = np.array([curve[t] for t in tenors], dtype=float)
    zero = -np.log(dfs) / tenors
    frame = pd.DataFrame({"tenor": tenors, "df": dfs, "zero": zero})

    if stress_name is None:
        frame["scenario"] = "base"
        return frame

    front_bp, back_bp = SCENARIO_SHOCKS_BP[stress_name]
    scale = np.linspace(front_bp, back_bp, tenors.size) / 10_000.0
    shocked_zero = zero + scale
    shocked_df = np.exp(-shocked_zero * tenors)
    frame["df"] = shocked_df
    frame["zero"] = shocked_zero
    frame["scenario"] = stress_name
    return frame


def _draw_curve_panel(base_curve: Mapping[float, float], title: str, overlays: list[str]) -> plt.Figure:
    frames = [_node_table(base_curve)]
    for name in overlays:
        frames.append(_node_table(base_curve, stress_name=name))
    curve_df = pd.concat(frames, ignore_index=True)

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    for scenario, grp in curve_df.groupby("scenario"):
        marker = "o" if scenario == "base" else None
        lw = 2.2 if scenario == "base" else 1.4
        ax.plot(grp["tenor"], grp["zero"] * 100.0, label=scenario, marker=marker, linewidth=lw)

    ax.set_title(title)
    ax.set_xlabel("Tenor (years)")
    ax.set_ylabel("Zero rate (%)")
    ax.grid(alpha=0.25)
    ax.legend(title="Scenario")
    fig.tight_layout()
    return fig


def _draw_basis_and_forwards(
    st: Any,
    base_bundle: Any,
    overlays: list[str],
    captions: Mapping[str, str],
) -> None:
    base_tenors = sorted(base_bundle.basis_term_structures["HUF-USD"])
    base_basis = np.array([base_bundle.basis_term_structures["HUF-USD"][t] for t in base_tenors], dtype=float)

    basis_data = {"tenor_years": base_tenors, "basis_bp": base_basis * 1e4, "term_premium_bp": base_basis * 1e4 * 0.2}
    basis_panel = pd.DataFrame(basis_data)

    with TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "basis_panel.png"
        plot_basis_term_premium_panel(basis_panel, out_path)
        st.image(str(out_path), use_container_width=True)

    st.caption(captions["huf_usd_basis"])

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.plot(base_tenors, base_basis * 1e4, marker="o", label="base", linewidth=2.2)

    for overlay in overlays:
        front_bp, back_bp = SCENARIO_SHOCKS_BP[overlay]
        shock = np.linspace(front_bp, back_bp, len(base_tenors)) / 10_000.0
        ax.plot(base_tenors, (base_basis + shock) * 1e4, label=overlay, linewidth=1.5)

    ax.set_title("HUF-USD Basis with Shock Overlays")
    ax.set_xlabel("Tenor (years)")
    ax.set_ylabel("Basis (bp)")
    ax.grid(alpha=0.25)
    ax.legend(title="Scenario")
    st.pyplot(fig)
    plt.close(fig)

    spot = 362.0
    huf_df = base_bundle.discount_curves["HUF"]
    usd_df = base_bundle.discount_curves["USD"]
    implied = extract_fx_implied_basis(
        spot=spot,
        forward_by_tenor={t: spot * huf_df[t] / usd_df[t] for t in base_tenors},
        domestic_df_curve=huf_df,
        foreign_ois_df_curve=usd_df,
    )

    fig2, ax2 = plt.subplots(figsize=(8.0, 4.2))
    implied_fwds = [spot * huf_df[t] / implied[t]["implied_foreign_df"] for t in base_tenors]
    ax2.plot(base_tenors, implied_fwds, marker="o", label="base", linewidth=2.2)

    for overlay in overlays:
        front_bp, back_bp = SCENARIO_SHOCKS_BP[overlay]
        stress_basis = np.linspace(front_bp, back_bp, len(base_tenors)) / 10_000.0
        stress_for_df = [implied[t]["implied_foreign_df"] * np.exp(-stress_basis[i] * t) for i, t in enumerate(base_tenors)]
        stress_fwds = [spot * huf_df[t] / stress_for_df[i] for i, t in enumerate(base_tenors)]
        ax2.plot(base_tenors, stress_fwds, label=overlay, linewidth=1.5)

    ax2.set_title("Implied HUF/USD Forward Curve")
    ax2.set_xlabel("Tenor (years)")
    ax2.set_ylabel("Forward FX")
    ax2.grid(alpha=0.25)
    ax2.legend(title="Scenario")
    st.pyplot(fig2)
    plt.close(fig2)
    st.caption(captions["implied_forwards"])


def render_curve_dashboard(
    st_module: Any | None = None,
    caption_overrides: Mapping[str, str] | None = None,
) -> None:
    st = st_module
    if st is None:
        import streamlit as st  # type: ignore

    captions = {**CHART_CAPTIONS, **(dict(caption_overrides or {}))}

    st.title("HUF/USD Curve Dashboard")
    st.write("Interactive diagnostics for projection/discount curves, basis term structures, and implied forwards.")

    selected = st.multiselect(
        "Shock overlays",
        options=list(SCENARIO_SHOCKS_BP),
        default=["parallel"],
        help="Apply stressed variants as parallel, steepening, or flattening shifts.",
    )

    instruments = _build_instruments()
    bundle = calibrate_cross_currency_bundle(instruments)

    col1, col2 = st.columns(2)

    huf_projection_fig = _draw_curve_panel(bundle.projection_curves["HUF"], "HUF Projection Curve", selected)
    huf_discount_fig = _draw_curve_panel(bundle.discount_curves["HUF"], "HUF Discount Curve", selected)

    with col1:
        st.pyplot(huf_projection_fig)
        plt.close(huf_projection_fig)
    with col2:
        st.pyplot(huf_discount_fig)
        plt.close(huf_discount_fig)

    st.caption(captions["huf_discount_projection"])

    usd_projection_fig = _draw_curve_panel(bundle.projection_curves["USD"], "USD Projection Curve", selected)
    usd_discount_fig = _draw_curve_panel(bundle.discount_curves["USD"], "USD Discount Curve", selected)

    with col1:
        st.pyplot(usd_projection_fig)
        plt.close(usd_projection_fig)
    with col2:
        st.pyplot(usd_discount_fig)
        plt.close(usd_discount_fig)

    st.caption(captions["usd_discount_projection"])

    tenors = np.array(sorted(bundle.projection_curves["HUF"]))
    huf_obs = -np.log([bundle.projection_curves["HUF"][t] for t in tenors]) / tenors
    huf_fit = fit_parametric_curve(tenors, huf_obs, model="svensson")

    with TemporaryDirectory() as tmp:
        fit_chart = Path(tmp) / "huf_fit.png"
        plot_fitted_vs_observed(
            tenors=tenors,
            observed=huf_obs,
            fitted=huf_fit.curve(tenors),
            output_path=fit_chart,
            title="HUF Projection: Observed vs Parametric Fit",
        )
        st.image(str(fit_chart), use_container_width=True)

    _draw_basis_and_forwards(st=st, base_bundle=bundle, overlays=selected, captions=captions)


if __name__ == "__main__":
    render_curve_dashboard()
