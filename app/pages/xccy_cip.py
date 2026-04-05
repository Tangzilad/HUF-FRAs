"""Cross-currency CIP monitoring page for USD/HUF.

This module is designed as a Streamlit multipage app (`app/pages`) while remaining
importable in environments where Streamlit is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.analytics.cip_premium import compute_purified_cip_deviation, compute_raw_cip_deviation
from src.curves.cross_currency import build_discount_curve, extract_fx_implied_basis

BP = 1e4

try:
    import streamlit as st
except ImportError:  # pragma: no cover - optional dependency for UI runtime
    st = None


@dataclass(frozen=True)
class MarketState:
    """Container for a point-in-time USD/HUF market snapshot."""

    spot_huf_per_usd: float
    tenors: tuple[float, ...]
    usd_ois: Dict[float, float]
    huf_ois: Dict[float, float]
    forwards_huf_per_usd: Dict[float, float]
    usd_sovereign_spread_bp: Dict[float, float]
    huf_sovereign_spread_bp: Dict[float, float]
    usd_supra_spread_bp: Dict[float, float]
    huf_supra_spread_bp: Dict[float, float]


def _default_state() -> MarketState:
    tenors = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0)
    spot = 360.0
    usd_ois = {0.25: 0.049, 0.5: 0.047, 1.0: 0.044, 2.0: 0.040, 3.0: 0.037, 5.0: 0.034}
    huf_ois = {0.25: 0.072, 0.5: 0.070, 1.0: 0.067, 2.0: 0.062, 3.0: 0.058, 5.0: 0.053}

    forwards = {}
    for t in tenors:
        parity = spot * (1.0 + huf_ois[t] * t) / (1.0 + usd_ois[t] * t)
        basis_bump = 0.003 * t  # synthetic stress premium in forward points
        forwards[t] = parity * (1.0 + basis_bump)

    return MarketState(
        spot_huf_per_usd=spot,
        tenors=tenors,
        usd_ois=usd_ois,
        huf_ois=huf_ois,
        forwards_huf_per_usd=forwards,
        usd_sovereign_spread_bp={0.25: 20, 0.5: 22, 1.0: 25, 2.0: 30, 3.0: 34, 5.0: 40},
        huf_sovereign_spread_bp={0.25: 180, 0.5: 190, 1.0: 210, 2.0: 240, 3.0: 260, 5.0: 295},
        usd_supra_spread_bp={0.25: 8, 0.5: 9, 1.0: 10, 2.0: 12, 3.0: 14, 5.0: 18},
        huf_supra_spread_bp={0.25: 105, 0.5: 112, 1.0: 123, 2.0: 142, 3.0: 157, 5.0: 180},
    )


def _apply_shock(
    state: MarketState,
    huf_ois_bp: float,
    usd_ois_bp: float,
    fwd_bp: float,
    spot_pct: float,
) -> MarketState:
    huf_shift = huf_ois_bp / BP
    usd_shift = usd_ois_bp / BP
    fwd_shift = fwd_bp / BP

    return MarketState(
        spot_huf_per_usd=state.spot_huf_per_usd * (1.0 + spot_pct / 100.0),
        tenors=state.tenors,
        usd_ois={t: r + usd_shift for t, r in state.usd_ois.items()},
        huf_ois={t: r + huf_shift for t, r in state.huf_ois.items()},
        forwards_huf_per_usd={t: f * (1.0 + fwd_shift) for t, f in state.forwards_huf_per_usd.items()},
        usd_sovereign_spread_bp=state.usd_sovereign_spread_bp,
        huf_sovereign_spread_bp={t: s + 0.35 * huf_ois_bp for t, s in state.huf_sovereign_spread_bp.items()},
        usd_supra_spread_bp=state.usd_supra_spread_bp,
        huf_supra_spread_bp={t: s + 0.15 * huf_ois_bp for t, s in state.huf_supra_spread_bp.items()},
    )


def _as_frame(row: Mapping[float, float], index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame([row], index=index, columns=list(row.keys()), dtype=float)


def _analyze_state(state: MarketState) -> Dict[str, pd.DataFrame]:
    as_of = pd.Timestamp("2026-04-05")
    idx = pd.DatetimeIndex([as_of])

    tenors = list(state.tenors)
    spot_series = pd.Series([state.spot_huf_per_usd], index=idx, dtype=float)
    forwards = _as_frame(state.forwards_huf_per_usd, idx)
    huf_ois = _as_frame(state.huf_ois, idx)
    usd_ois = _as_frame(state.usd_ois, idx)

    raw_panel = compute_raw_cip_deviation(spot=spot_series, forward=forwards, domestic_ois=huf_ois, foreign_ois=usd_ois)
    raw_basis_only = raw_panel["raw_basis_bp"].copy()

    huf_sovereign = huf_ois + _as_frame({t: state.huf_sovereign_spread_bp[t] / BP for t in tenors}, idx)
    usd_sovereign = usd_ois + _as_frame({t: state.usd_sovereign_spread_bp[t] / BP for t in tenors}, idx)
    huf_supra = huf_ois + _as_frame({t: state.huf_supra_spread_bp[t] / BP for t in tenors}, idx)
    usd_supra = usd_ois + _as_frame({t: state.usd_supra_spread_bp[t] / BP for t in tenors}, idx)

    purified = compute_purified_cip_deviation(
        raw_basis_bp=raw_basis_only,
        domestic_sovereign=huf_sovereign,
        foreign_sovereign=usd_sovereign,
        domestic_supranational=huf_supra,
        foreign_supranational=usd_supra,
    )

    huf_df = build_discount_curve(state.huf_ois)
    usd_df = build_discount_curve(state.usd_ois)
    fx_implied = extract_fx_implied_basis(
        spot=state.spot_huf_per_usd,
        forward_by_tenor=state.forwards_huf_per_usd,
        domestic_df_curve=huf_df,
        foreign_ois_df_curve=usd_df,
    )

    raw_basis_curve = pd.Series(
        {t: values["basis_residual"] * BP for t, values in fx_implied.items()},
        name="raw_basis_bp_curve",
        dtype=float,
    )

    pv_rows = []
    exposure_rows = []
    notional_usd = 10_000_000.0
    for t in tenors:
        market_fwd = state.forwards_huf_per_usd[t]
        ois_fwd = state.spot_huf_per_usd * (1.0 + state.huf_ois[t] * t) / (1.0 + state.usd_ois[t] * t)
        usd_collat_pv = usd_df[t]
        huf_collat_pv = state.spot_huf_per_usd * huf_df[t] / market_fwd

        pv_rows.append(
            {
                "tenor_years": t,
                "pv_usd_collateral": usd_collat_pv,
                "pv_huf_collateral": huf_collat_pv,
                "collateral_pv_gap_bp": (huf_collat_pv / usd_collat_pv - 1.0) * BP,
            }
        )
        mispricing_huf = (market_fwd - ois_fwd) * notional_usd
        exposure_rows.append(
            {
                "tenor_years": t,
                "market_forward": market_fwd,
                "ois_parity_forward": ois_fwd,
                "forward_gap_huf": market_fwd - ois_fwd,
                "residual_huf_pv": mispricing_huf,
                "residual_usd_equiv": mispricing_huf / market_fwd,
                "raw_basis_bp": raw_basis_curve[t],
            }
        )

    purified_snapshot = purified.loc[as_of].T
    purified_snapshot.columns = ["value_bp"]
    purified_snapshot.index.name = "metric"

    return {
        "raw_basis_curve": raw_basis_curve.to_frame(),
        "purified_decomposition": purified_snapshot,
        "collateral_pv": pd.DataFrame(pv_rows).set_index("tenor_years"),
        "residual_exposure": pd.DataFrame(exposure_rows).set_index("tenor_years"),
    }


def _comparison_table(before: pd.DataFrame, after: pd.DataFrame, value_name: str) -> pd.DataFrame:
    left = before.copy().add_prefix("pre_")
    right = after.copy().add_prefix("post_")
    combo = left.join(right, how="outer")

    if before.shape[1] == 1 and after.shape[1] == 1:
        pre_col = combo.columns[0]
        post_col = combo.columns[1]
        combo[f"delta_{value_name}"] = combo[post_col] - combo[pre_col]
    return combo


def _render_streamlit_page() -> None:
    st.set_page_config(page_title="USD/HUF Cross-Currency CIP", layout="wide")
    st.title("USD/HUF Cross-Currency CIP Monitor")

    st.markdown(
        """
### Assumptions and conventions
- FX quote convention: **HUF per 1 USD** (domestic-per-foreign), consistent with CIP analytics docs.
- Covered parity mapping uses **simple annual compounding**.
- Rate inputs are **decimal annualized rates**; spreads are in **basis points** then converted as needed.
- Interpolation/extrapolation behavior follows `numpy.interp` where used in the analytics stack.
- Purified basis strips local credit effects via **sovereign minus supranational** differential.
"""
    )

    base_state = _default_state()
    with st.sidebar:
        st.header("Shock controls")
        compare_mode = st.toggle("Enable pre/post-shock comparison", value=True)
        huf_ois_bp = st.slider("HUF OIS shock (bp)", min_value=-200, max_value=300, value=75, step=5)
        usd_ois_bp = st.slider("USD OIS shock (bp)", min_value=-150, max_value=200, value=10, step=5)
        fwd_bp = st.slider("FX forward level shock (bp)", min_value=-300, max_value=300, value=40, step=5)
        spot_pct = st.slider("Spot shock (%)", min_value=-10.0, max_value=10.0, value=1.5, step=0.1)

    pre = _analyze_state(base_state)

    if compare_mode:
        post_state = _apply_shock(base_state, huf_ois_bp=huf_ois_bp, usd_ois_bp=usd_ois_bp, fwd_bp=fwd_bp, spot_pct=spot_pct)
        post = _analyze_state(post_state)
    else:
        post = pre

    st.subheader("Raw CIP basis")
    st.dataframe(_comparison_table(pre["raw_basis_curve"], post["raw_basis_curve"], "raw_basis_bp"), use_container_width=True)

    st.subheader("Purified basis decomposition")
    st.dataframe(
        _comparison_table(pre["purified_decomposition"], post["purified_decomposition"], "purified_bp"),
        use_container_width=True,
    )

    st.subheader("Collateralized PV comparisons")
    st.dataframe(_comparison_table(pre["collateral_pv"], post["collateral_pv"], "pv"), use_container_width=True)

    st.subheader("Residual USD/HUF exposure metrics")
    st.dataframe(_comparison_table(pre["residual_exposure"], post["residual_exposure"], "exposure"), use_container_width=True)


if __name__ == "__main__":
    if st is None:
        baseline = _analyze_state(_default_state())
        print("Streamlit is not installed. Generated baseline analytics tables:")
        for name, table in baseline.items():
            print(f"\n=== {name} ===")
            print(table)
    else:
        _render_streamlit_page()
