"""
HUF FRA scenario simulation for sell-side STIR desk.

This script builds synthetic HUF and USD money-market curves, prices FRAs up to 1Y,
computes PV / DV01 / scenario P&L, models roll-down, and sizes a USD hedge to reduce
residual risk.

Empirical shock defaults encoded in `DEFAULT_CONFIG`:
- tariff_liberation: -50bp parallel move (flight-to-safety style)
- war_shock: +50bp parallel move
- debt_crisis: short-end +60bp, long-end +140bp (tilted stress)

These defaults can be changed by editing `DEFAULT_CONFIG` or passing an override.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st


sns.set_style("whitegrid")


@dataclass
class SimulationConfig:
    notional_huf: float = 100_000_000.0
    notional_usd: float = 1_000_000.0
    seed: int = 42
    huf_level_1m: float = 0.065
    huf_level_12m: float = 0.060
    usd_level_1m: float = 0.050
    usd_level_12m: float = 0.047
    noise_std: float = 0.0008
    act_basis: float = 360.0
    payer: bool = True
    hedge_target: str = "dv01"  # dv01 or pnl
    roll_down_months: int = 1
    custom_shock_front_bp: float = 100.0
    custom_shock_back_bp: float = 50.0
    # Curve tilt controls in bp from 1M to 12M
    steepening_front_bp: float = 10.0
    steepening_back_bp: float = 50.0
    flattening_front_bp: float = 50.0
    flattening_back_bp: float = 10.0


DEFAULT_CONFIG = SimulationConfig()


def _month_nodes() -> np.ndarray:
    return np.arange(1, 13, dtype=float)


def _tenor_pairs() -> List[Tuple[int, int]]:
    """Generate FRA tenor pairs up to 12M and key STIR anchors."""
    anchors = {(1, 3), (1, 6), (1, 9), (1, 12), (3, 6), (6, 9), (9, 12)}
    all_pairs = set()
    for start in range(1, 12):
        for end in range(start + 1, 13):
            all_pairs.add((start, end))
    all_pairs |= anchors
    return sorted(all_pairs)


def generate_base_curves(config: SimulationConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """
    Build synthetic monthly HUF and USD zero curves (1M..12M) with small Gaussian noise.
    """
    rng = np.random.default_rng(config.seed)
    months = _month_nodes()

    huf_base = np.linspace(config.huf_level_1m, config.huf_level_12m, len(months))
    usd_base = np.linspace(config.usd_level_1m, config.usd_level_12m, len(months))

    huf = huf_base + rng.normal(0.0, config.noise_std, size=len(months))
    usd = usd_base + rng.normal(0.0, config.noise_std * 0.8, size=len(months))

    curve = pd.DataFrame(
        {
            "month": months.astype(int),
            "t": months / 12.0,
            "huf_zero": huf,
            "usd_zero": usd,
        }
    )
    curve["huf_df"] = np.exp(-curve["huf_zero"] * curve["t"])
    curve["usd_df"] = np.exp(-curve["usd_zero"] * curve["t"])
    return curve


def build_forward_curve(curve_df: pd.DataFrame, ccy_prefix: str = "huf") -> pd.DataFrame:
    """Compute 1M-forward rates from discount factors for a currency curve."""
    df_col = f"{ccy_prefix}_df"
    out = curve_df[["month", "t", df_col]].copy()
    fwd_rates = [np.nan]

    for m in range(2, 13):
        d0 = out.loc[out["month"] == m - 1, df_col].iloc[0]
        d1 = out.loc[out["month"] == m, df_col].iloc[0]
        tau = 1.0 / 12.0
        fwd = (d0 / d1 - 1.0) / tau
        fwd_rates.append(fwd)

    out[f"{ccy_prefix}_1m_fwd"] = fwd_rates
    return out


def build_fra_instruments(
    curve_df: pd.DataFrame,
    notional: float,
    fra_pairs: Optional[Iterable[Tuple[int, int]]] = None,
    ccy_prefix: str = "huf",
) -> pd.DataFrame:
    """Construct FRA table with implied strike = current forward for each start/end."""
    if fra_pairs is None:
        fra_pairs = _tenor_pairs()

    rows: List[Dict[str, float]] = []
    for start_m, end_m in fra_pairs:
        t1 = start_m / 12.0
        t2 = end_m / 12.0
        tau = t2 - t1
        p1 = curve_df.loc[curve_df["month"] == start_m, f"{ccy_prefix}_df"].iloc[0]
        p2 = curve_df.loc[curve_df["month"] == end_m, f"{ccy_prefix}_df"].iloc[0]
        fwd = (p1 / p2 - 1.0) / tau
        rows.append(
            {
                "fra": f"{start_m}x{end_m}",
                "start_m": start_m,
                "end_m": end_m,
                "tau": tau,
                "notional": notional,
                "strike": fwd,
            }
        )
    return pd.DataFrame(rows)


def price_fra(
    fra_df: pd.DataFrame,
    curve_df: pd.DataFrame,
    payer: bool = True,
    ccy_prefix: str = "huf",
) -> pd.DataFrame:
    """
    Price FRAs from a shocked/current curve.

    Payoff convention (discounted to start date then back to valuation date via P(0,t1)):
      PV = N * tau * (F - K) * P(0,t2)
    payer: long rates, positive when F > K.
    receiver is sign-flipped.
    """
    out = fra_df.copy()
    pv_list: List[float] = []
    dv01_list: List[float] = []
    fwd_list: List[float] = []
    df_end_list: List[float] = []

    for _, r in out.iterrows():
        p1 = curve_df.loc[curve_df["month"] == int(r.start_m), f"{ccy_prefix}_df"].iloc[0]
        p2 = curve_df.loc[curve_df["month"] == int(r.end_m), f"{ccy_prefix}_df"].iloc[0]
        tau = r.tau
        fwd = (p1 / p2 - 1.0) / tau
        sign = 1.0 if payer else -1.0
        pv = sign * r.notional * tau * (fwd - r.strike) * p2

        bump = 1e-4
        p1_b = p1 * np.exp(-bump * (r.start_m / 12.0))
        p2_b = p2 * np.exp(-bump * (r.end_m / 12.0))
        fwd_b = (p1_b / p2_b - 1.0) / tau
        pv_b = sign * r.notional * tau * (fwd_b - r.strike) * p2_b
        dv01 = pv_b - pv

        pv_list.append(pv)
        dv01_list.append(dv01)
        fwd_list.append(fwd)
        df_end_list.append(p2)

    out[f"{ccy_prefix}_fwd"] = fwd_list
    out[f"{ccy_prefix}_df_end"] = df_end_list
    out[f"{ccy_prefix}_{'payer' if payer else 'receiver'}_pv"] = pv_list
    out[f"{ccy_prefix}_dv01"] = dv01_list
    out[f"{ccy_prefix}_orientation"] = "payer" if payer else "receiver"
    return out


def _tilt(months: pd.Series, front_bp: float, back_bp: float) -> np.ndarray:
    return np.interp(months, [1, 12], [front_bp, back_bp]) / 10_000.0


def apply_shock(
    curve_df: pd.DataFrame,
    regime: str = "base",
    parallel_bp: float = 0.0,
    steepening: bool = False,
    flattening: bool = False,
    config: SimulationConfig = DEFAULT_CONFIG,
) -> pd.DataFrame:
    """Apply macro regime and optional steepening/flattening shifts to HUF and USD curves."""
    shocked = curve_df.copy()

    regime = regime.lower()
    if regime == "base":
        shift_huf = np.zeros(len(shocked))
        shift_usd = np.zeros(len(shocked))
    elif regime == "tariff_liberation":
        shift_huf = np.full(len(shocked), -50.0 / 10_000.0)
        shift_usd = np.full(len(shocked), -50.0 / 10_000.0)
    elif regime == "war_shock":
        shift_huf = np.full(len(shocked), 50.0 / 10_000.0)
        shift_usd = np.full(len(shocked), 35.0 / 10_000.0)
    elif regime == "debt_crisis":
        shift_huf = _tilt(shocked["month"], 60.0, 140.0)
        shift_usd = _tilt(shocked["month"], 30.0, 90.0)
    elif regime == "high_inflation":
        shift_huf = _tilt(shocked["month"], config.custom_shock_front_bp, config.custom_shock_back_bp)
        shift_usd = _tilt(shocked["month"], config.custom_shock_front_bp * 0.7, config.custom_shock_back_bp * 0.7)
    else:
        raise ValueError(f"Unsupported regime: {regime}")

    parallel = parallel_bp / 10_000.0
    shift_huf += parallel
    shift_usd += parallel * 0.8

    if steepening:
        shift_huf += _tilt(shocked["month"], config.steepening_front_bp, config.steepening_back_bp)
        shift_usd += _tilt(shocked["month"], config.steepening_front_bp * 0.7, config.steepening_back_bp * 0.7)
    if flattening:
        shift_huf += _tilt(shocked["month"], config.flattening_front_bp, config.flattening_back_bp)
        shift_usd += _tilt(shocked["month"], config.flattening_front_bp * 0.7, config.flattening_back_bp * 0.7)

    shocked["huf_zero"] = shocked["huf_zero"] + shift_huf
    shocked["usd_zero"] = shocked["usd_zero"] + shift_usd
    shocked["huf_df"] = np.exp(-shocked["huf_zero"] * shocked["t"])
    shocked["usd_df"] = np.exp(-shocked["usd_zero"] * shocked["t"])
    return shocked


def roll_down_curve(curve_df: pd.DataFrame, months: int = 1) -> pd.DataFrame:
    """Simulate passage of time with no market move: left-shift the curve by `months`."""
    out = curve_df.copy()
    for col in ["huf_zero", "usd_zero"]:
        arr = out[col].to_numpy()
        rolled = np.empty_like(arr)
        if months >= len(arr):
            rolled[:] = arr[-1]
        else:
            rolled[:-months] = arr[months:]
            rolled[-months:] = arr[-1]
        out[col] = rolled
    out["huf_df"] = np.exp(-out["huf_zero"] * out["t"])
    out["usd_df"] = np.exp(-out["usd_zero"] * out["t"])
    return out


def compute_pnl_dv01(
    base_priced: pd.DataFrame,
    scenario_priced: pd.DataFrame,
    ccy_prefix: str = "huf",
    payer: bool = True,
) -> pd.DataFrame:
    """Compute scenario P&L and summarize DV01 at FRA granularity and bucket level."""
    key_col = f"{ccy_prefix}_{'payer' if payer else 'receiver'}_pv"
    dv01_col = f"{ccy_prefix}_dv01"

    merged = base_priced[["fra", key_col, dv01_col]].merge(
        scenario_priced[["fra", key_col, dv01_col]], on="fra", suffixes=("_base", "_scn")
    )
    merged["pnl"] = merged[f"{key_col}_scn"] - merged[f"{key_col}_base"]
    merged["dv01_change"] = merged[f"{dv01_col}_scn"] - merged[f"{dv01_col}_base"]

    se = merged["fra"].str.split("x", expand=True).astype(int)
    merged["start_m"] = se[0]
    merged["end_m"] = se[1]
    merged["bucket"] = pd.cut(
        merged["end_m"],
        bins=[0, 3, 6, 9, 12],
        labels=["<=3M", "3-6M", "6-9M", "9-12M"],
        include_lowest=True,
    )

    bucket = merged.groupby("bucket", observed=True)[["pnl", f"{dv01_col}_scn"]].sum().reset_index()
    bucket = bucket.rename(columns={f"{dv01_col}_scn": "bucket_dv01"})
    return merged, bucket


def hedge_usd_residual(
    huf_results: pd.DataFrame,
    usd_results: pd.DataFrame,
    target: str = "dv01",
) -> Dict[str, float]:
    """
    Size a USD FRA hedge ratio that neutralizes aggregate DV01 or P&L.

    Returns hedge ratio and residuals. Ratio scales USD notionals relative to current USD book.
    """
    target = target.lower()
    if target not in {"dv01", "pnl"}:
        raise ValueError("target must be 'dv01' or 'pnl'")

    if target == "dv01":
        h = float(np.asarray(huf_results["huf_dv01_scn"]).sum())
        u = float(np.asarray(usd_results["usd_dv01_scn"]).sum())
    else:
        h = float(np.asarray(huf_results["pnl"]).sum())
        u = float(np.asarray(usd_results["pnl"]).sum())

    ratio = 0.0 if abs(u) < 1e-12 else -h / u

    hedged_dv01 = float(np.asarray(huf_results["huf_dv01_scn"]).sum() + ratio * np.asarray(usd_results["usd_dv01_scn"]).sum())
    hedged_pnl = float(np.asarray(huf_results["pnl"]).sum() + ratio * np.asarray(usd_results["pnl"]).sum())

    return {
        "target": target,
        "hedge_ratio_usd": ratio,
        "huf_metric": h,
        "usd_metric": u,
        "net_dv01_after_hedge": hedged_dv01,
        "net_pnl_after_hedge": hedged_pnl,
    }


def plot_curves(base_curve: pd.DataFrame, shocked_curve: pd.DataFrame, title: str) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharex=True)

    ax[0].plot(base_curve["month"], base_curve["huf_zero"] * 10_000, label="HUF Base", lw=2)
    ax[0].plot(shocked_curve["month"], shocked_curve["huf_zero"] * 10_000, label="HUF Shocked", lw=2)
    ax[0].set_title(f"HUF Curve - {title}")
    ax[0].set_ylabel("Rate (bp)")
    ax[0].set_xlabel("Month")
    ax[0].legend()

    ax[1].plot(base_curve["month"], base_curve["usd_zero"] * 10_000, label="USD Base", lw=2)
    ax[1].plot(shocked_curve["month"], shocked_curve["usd_zero"] * 10_000, label="USD Shocked", lw=2)
    ax[1].set_title(f"USD Curve - {title}")
    ax[1].set_xlabel("Month")
    ax[1].legend()

    fig.tight_layout()


def plot_results(bucket_df: pd.DataFrame, title: str, value_col: str = "pnl") -> None:
    plt.figure(figsize=(7, 4))
    sns.barplot(data=bucket_df, x="bucket", y=value_col, hue="bucket", legend=False, palette="viridis")
    plt.title(f"{value_col.upper()} by Bucket - {title}")
    plt.xlabel("Tenor Bucket")
    plt.ylabel(value_col.upper())
    plt.tight_layout()


def _format_bp(value: float) -> str:
    return f"{value * 10_000:,.1f} bp"


def _streamlit_header() -> None:
    st.title("HUF FRA Dynamics Learning Lab")
    st.caption(
        "Interactive scenario explorer for understanding how curve shifts propagate into FRA forwards, "
        "PV, DV01, bucket risk, roll-down, and USD hedge overlays."
    )
    st.markdown(
        """
        ### How to use this page for learning
        1. **Start with the curve chart** to see the shape of the shock itself.
        2. **Move to bucket P&L and DV01** to see where risk concentrates by maturity.
        3. **Inspect FRA-level table** to connect one bar on the chart to individual contracts (e.g., 1x3, 6x9).
        4. **Check roll-down** to separate *time carry effects* from *macro shock effects*.
        5. **Use hedge panel** to understand what USD ratio offsets the selected HUF risk objective.
        """
    )


def _streamlit_controls() -> Tuple[SimulationConfig, Dict[str, object]]:
    st.sidebar.header("Scenario Controls")

    regime = st.sidebar.selectbox(
        "Macro regime",
        ["base", "tariff_liberation", "war_shock", "debt_crisis", "high_inflation"],
        index=1,
    )
    payer = st.sidebar.radio("Position orientation", ["Payer (long rates)", "Receiver (short rates)"], index=0) == "Payer (long rates)"
    hedge_target = st.sidebar.selectbox("Hedge target", ["dv01", "pnl"], index=0)
    parallel_bp = st.sidebar.slider("Parallel shock (bp)", min_value=-200, max_value=200, value=0, step=5)
    steepening = st.sidebar.checkbox("Apply extra steepening tilt", value=False)
    flattening = st.sidebar.checkbox("Apply extra flattening tilt", value=False)
    roll_months = st.sidebar.slider("Roll-down horizon (months)", min_value=1, max_value=6, value=1)

    st.sidebar.markdown("### Book and curve assumptions")
    notional_huf = st.sidebar.number_input("HUF notional", min_value=1_000_000.0, value=100_000_000.0, step=5_000_000.0, format="%.0f")
    notional_usd = st.sidebar.number_input("USD notional", min_value=10_000.0, value=1_000_000.0, step=50_000.0, format="%.0f")
    huf_1m = st.sidebar.slider("HUF 1M zero (%)", min_value=0.0, max_value=20.0, value=6.5, step=0.1) / 100.0
    huf_12m = st.sidebar.slider("HUF 12M zero (%)", min_value=0.0, max_value=20.0, value=6.0, step=0.1) / 100.0
    usd_1m = st.sidebar.slider("USD 1M zero (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.1) / 100.0
    usd_12m = st.sidebar.slider("USD 12M zero (%)", min_value=0.0, max_value=15.0, value=4.7, step=0.1) / 100.0
    seed = int(st.sidebar.number_input("Random seed", min_value=0, max_value=10_000, value=42, step=1))

    cfg = SimulationConfig(
        notional_huf=notional_huf,
        notional_usd=notional_usd,
        seed=seed,
        huf_level_1m=huf_1m,
        huf_level_12m=huf_12m,
        usd_level_1m=usd_1m,
        usd_level_12m=usd_12m,
        payer=payer,
        hedge_target=hedge_target,
        roll_down_months=roll_months,
    )

    opts: Dict[str, object] = {
        "regime": regime,
        "parallel_bp": float(parallel_bp),
        "steepening": steepening,
        "flattening": flattening,
    }
    return cfg, opts


def _streamlit_curve_panel(results: Dict[str, pd.DataFrame], regime: str) -> None:
    st.subheader("1) Curve Shock Visualization")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharex=True)
    base_curve = results["base_curve"]
    shocked_curve = results["shocked_curve"]

    ax[0].plot(base_curve["month"], base_curve["huf_zero"] * 10_000, label="HUF Base", lw=2)
    ax[0].plot(shocked_curve["month"], shocked_curve["huf_zero"] * 10_000, label="HUF Shocked", lw=2)
    ax[0].set_title("HUF zero curve")
    ax[0].set_ylabel("Rate (bp)")
    ax[0].set_xlabel("Month")
    ax[0].legend()

    ax[1].plot(base_curve["month"], base_curve["usd_zero"] * 10_000, label="USD Base", lw=2)
    ax[1].plot(shocked_curve["month"], shocked_curve["usd_zero"] * 10_000, label="USD Shocked", lw=2)
    ax[1].set_title("USD zero curve")
    ax[1].set_xlabel("Month")
    ax[1].legend()
    fig.suptitle(f"Scenario: {regime}")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    huf_shift = (shocked_curve["huf_zero"] - base_curve["huf_zero"]).mean()
    usd_shift = (shocked_curve["usd_zero"] - base_curve["usd_zero"]).mean()
    st.info(
        f"Reading the chart: On average, HUF moved {_format_bp(huf_shift)} and USD moved {_format_bp(usd_shift)}. "
        "A steeper separation at long months implies bigger sensitivity in longer-end FRA buckets."
    )


def _streamlit_bucket_panel(results: Dict[str, pd.DataFrame]) -> None:
    st.subheader("2) Bucket P&L and DV01 Concentration")
    col1, col2 = st.columns(2)
    with col1:
        fig_pnl = plt.figure(figsize=(6, 3.5))
        sns.barplot(data=results["huf_bucket"], x="bucket", y="pnl", hue="bucket", legend=False, palette="viridis")
        plt.title("HUF bucket P&L")
        plt.xlabel("Tenor bucket")
        plt.ylabel("P&L")
        plt.tight_layout()
        st.pyplot(fig_pnl)
        plt.close(fig_pnl)

    with col2:
        fig_dv01 = plt.figure(figsize=(6, 3.5))
        sns.barplot(data=results["huf_bucket"], x="bucket", y="bucket_dv01", hue="bucket", legend=False, palette="magma")
        plt.title("HUF scenario DV01")
        plt.xlabel("Tenor bucket")
        plt.ylabel("DV01")
        plt.tight_layout()
        st.pyplot(fig_dv01)
        plt.close(fig_dv01)

    top_bucket = results["huf_bucket"].iloc[results["huf_bucket"]["pnl"].abs().idxmax()]
    st.success(
        f"Largest absolute HUF P&L bucket: **{top_bucket['bucket']}** with {top_bucket['pnl']:,.0f}. "
        "This is usually where your scenario shock and book exposure align most strongly."
    )


def _streamlit_fra_table_panel(results: Dict[str, pd.DataFrame]) -> None:
    st.subheader("3) FRA-level Drill-down")
    ranked = results["huf_gran"].copy()
    ranked["abs_pnl"] = ranked["pnl"].abs()
    ranked = ranked.sort_values("abs_pnl", ascending=False)
    st.dataframe(
        ranked[["fra", "pnl", "huf_dv01_scn", "dv01_change", "bucket"]].head(20),
        use_container_width=True,
    )
    st.markdown(
        """
        **How to interpret the table**
        - `pnl`: scenario profit/loss versus base valuation.
        - `huf_dv01_scn`: new first-order rate sensitivity after the shock.
        - `dv01_change`: how convexity/discounting changed sensitivity versus base.
        - `bucket`: maturity grouping used in the charts above.
        """
    )


def _streamlit_hedge_roll_panel(results: Dict[str, pd.DataFrame], roll_months: int) -> None:
    st.subheader("4) Hedge Overlay and Roll-down Learning View")
    hedge = results["hedge"].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("USD hedge ratio", f"{hedge['hedge_ratio_usd']:.3f}x")
    c2.metric("Net DV01 after hedge", f"{hedge['net_dv01_after_hedge']:,.0f}")
    c3.metric("Net P&L after hedge", f"{hedge['net_pnl_after_hedge']:,.0f}")

    st.markdown(
        f"""
        The hedge ratio tells you how much USD FRA risk (relative to the configured USD book) offsets the selected HUF objective.
        A **negative ratio** means hedge in the opposite direction of the existing USD exposure.
        """
    )

    fig_roll = plt.figure(figsize=(7, 3.5))
    sns.barplot(data=results["roll_bucket"], x="bucket", y="pnl", hue="bucket", legend=False, palette="crest")
    plt.title(f"HUF roll-down P&L over {roll_months}M (no shock)")
    plt.xlabel("Tenor bucket")
    plt.ylabel("Roll-down P&L")
    plt.tight_layout()
    st.pyplot(fig_roll)
    plt.close(fig_roll)
    st.warning(
        "Roll-down isolates the passage-of-time effect. Compare this to scenario P&L to distinguish carry from macro repricing."
    )


def streamlit_app() -> None:
    _streamlit_header()
    cfg, opts = _streamlit_controls()
    regime = str(opts["regime"])
    parallel_bp = float(opts["parallel_bp"])
    steepening = bool(opts["steepening"])
    flattening = bool(opts["flattening"])

    results = run_scenario(
        regime=regime,
        config=cfg,
        payer=cfg.payer,
        steepening=steepening,
        flattening=flattening,
        parallel_bp=parallel_bp,
    )

    _streamlit_curve_panel(results, regime)
    _streamlit_bucket_panel(results)
    _streamlit_fra_table_panel(results)
    _streamlit_hedge_roll_panel(results, cfg.roll_down_months)


def run_scenario(
    regime: str,
    config: SimulationConfig = DEFAULT_CONFIG,
    payer: Optional[bool] = None,
    steepening: bool = False,
    flattening: bool = False,
    parallel_bp: float = 0.0,
) -> Dict[str, pd.DataFrame]:
    """Run end-to-end FRA scenario for one macro regime and return detailed tables."""
    payer = config.payer if payer is None else payer

    base_curve = generate_base_curves(config)
    fra_huf = build_fra_instruments(base_curve, config.notional_huf, ccy_prefix="huf")
    fra_usd = build_fra_instruments(base_curve, config.notional_usd, ccy_prefix="usd")

    base_huf = price_fra(fra_huf, base_curve, payer=payer, ccy_prefix="huf")
    base_usd = price_fra(fra_usd, base_curve, payer=payer, ccy_prefix="usd")

    shocked_curve = apply_shock(
        base_curve,
        regime=regime,
        parallel_bp=parallel_bp,
        steepening=steepening,
        flattening=flattening,
        config=config,
    )

    scn_huf = price_fra(fra_huf, shocked_curve, payer=payer, ccy_prefix="huf")
    scn_usd = price_fra(fra_usd, shocked_curve, payer=payer, ccy_prefix="usd")

    huf_gran, huf_bucket = compute_pnl_dv01(base_huf, scn_huf, ccy_prefix="huf", payer=payer)
    usd_gran, usd_bucket = compute_pnl_dv01(base_usd, scn_usd, ccy_prefix="usd", payer=payer)

    # compute_pnl_dv01 already carries scenario DV01 columns (huf_dv01_scn / usd_dv01_scn)
    hedge = hedge_usd_residual(huf_gran, usd_gran, target=config.hedge_target)

    rolled_curve = roll_down_curve(base_curve, months=config.roll_down_months)
    roll_huf = price_fra(fra_huf, rolled_curve, payer=payer, ccy_prefix="huf")
    roll_gran, roll_bucket = compute_pnl_dv01(base_huf, roll_huf, ccy_prefix="huf", payer=payer)

    return {
        "base_curve": base_curve,
        "shocked_curve": shocked_curve,
        "huf_base": base_huf,
        "huf_scn": scn_huf,
        "huf_gran": huf_gran,
        "huf_bucket": huf_bucket,
        "usd_gran": usd_gran,
        "usd_bucket": usd_bucket,
        "hedge": pd.DataFrame([hedge]),
        "roll_gran": roll_gran,
        "roll_bucket": roll_bucket,
    }


def demo() -> None:
    """Demonstrate base-case, tariff, war, and debt-crisis scenarios with plots/tables."""
    cfg = DEFAULT_CONFIG

    scenarios = [
        ("tariff_liberation", False, False),
        ("war_shock", True, False),
        ("debt_crisis", False, True),
    ]

    for regime, steep, flat in scenarios:
        results = run_scenario(regime, cfg, steepening=steep, flattening=flat)

        print(f"\n=== Scenario: {regime} ===")
        cols = ["fra", "pnl", "huf_dv01_scn", "dv01_change", "bucket"]
        print(results["huf_gran"][cols].head(12).to_string(index=False))
        print("\nBucket Summary:")
        print(results["huf_bucket"].to_string(index=False))
        print("\nUSD Hedge Summary:")
        print(results["hedge"].to_string(index=False))

        plot_curves(results["base_curve"], results["shocked_curve"], title=regime)
        plot_results(results["huf_bucket"], title=regime, value_col="pnl")
        plot_results(results["huf_bucket"], title=regime, value_col="bucket_dv01")

        print("\nRoll-down Bucket (HUF):")
        print(results["roll_bucket"].to_string(index=False))

    plt.show()


def _is_streamlit_runtime() -> bool:
    runtime = getattr(st, "runtime", None)
    if runtime is None:
        return False
    exists = getattr(runtime, "exists", None)
    return bool(exists()) if callable(exists) else False


if __name__ == "__main__":
    if _is_streamlit_runtime():
        streamlit_app()
    else:
        demo()
