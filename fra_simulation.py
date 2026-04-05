"""
HUF FRA scenario simulation for sell-side STIR desk + structured learning workspace.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
HAS_PANDAS = importlib.util.find_spec("pandas") is not None

HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
HAS_SEABORN = importlib.util.find_spec("seaborn") is not None

if not HAS_NUMPY or not HAS_PANDAS:
    missing = []
    if not HAS_NUMPY:
        missing.append("numpy")
    if not HAS_PANDAS:
        missing.append("pandas")
    print(
        "Missing required dependencies: "
        + ", ".join(missing)
        + ". Install with: python -m pip install "
        + " ".join(missing),
        file=sys.stderr,
    )
    raise SystemExit(1)

np = importlib.import_module("numpy")
pd = importlib.import_module("pandas")
matplotlib = importlib.import_module("matplotlib") if HAS_MATPLOTLIB else None
plt = importlib.import_module("matplotlib.pyplot") if HAS_MATPLOTLIB else None
sns = importlib.import_module("seaborn") if HAS_SEABORN else None

if HAS_MATPLOTLIB and matplotlib is not None:
    matplotlib.use("Agg")
if HAS_SEABORN and sns is not None:
    sns.set_style("whitegrid")


THEORY_NOTES = """
========================
FRA RATE THEORY (ADVANCED)
========================

1. FRA valuation identity
-------------------------
Given discount factors P(0, t1), P(0, t2), year fraction tau = t2 - t1:
    F(0; t1, t2) = (P(0,t1)/P(0,t2) - 1) / tau

For notional N and strike K, a payer FRA PV (long rates) under simple compounding:
    PV(0) = N * tau * (F - K) * P(0, t2)

2. Curve construction intuition
-------------------------------
The model uses synthetic monthly zero rates and discount factors with continuous compounding:
    P(0,t) = exp(-r(t) * t)

3. Risk decomposition
---------------------
- DV01 is finite-difference sensitivity to a 1bp shift.
- Key-rate DV01 shocks one tenor node at a time.
- PCA decomposition summarizes factor risk from a shock matrix.
"""

PROJECT_ROADMAP = [
    {
        "name": "Multi-curve FRA engine (OIS discounting + IBOR projection)",
        "objective": "Separate discount and forward curves to mirror post-crisis pricing.",
        "deliverable": "Refactor pricing to accept projection curve and discount curve independently.",
    },
    {
        "name": "Historical scenario library",
        "objective": "Replace synthetic shocks with date-stamped historical stress windows.",
        "deliverable": "CSV-based scenario loader + replay report by episode and regime.",
    },
    {
        "name": "Key-rate DV01 / PCA risk",
        "objective": "Move beyond parallel DV01 into key-rate and factor risk decomposition.",
        "deliverable": "Tenor-key sensitivity matrix and PCA factor exposure dashboard.",
    },
    {
        "name": "Convexity and futures-vs-FRA analytics",
        "objective": "Understand FRA-futures convexity adjustment and hedge slippage.",
        "deliverable": "Report quantifying convexity under volatility assumptions.",
    },
    {
        "name": "Hedging optimizer under constraints",
        "objective": "Optimize hedge basket with liquidity and notional bounds.",
        "deliverable": "Constrained hedge optimizer CLI.",
    },
]

CODEX_STARTER_TASKS = [
    {
        "phase": "phase-0",
        "task": "Generate baseline outputs and sanity-check signs.",
        "command": "python fra_simulation.py --mode demo",
        "success_criteria": "Payer FRA P&L should generally rise in upward-rate shock scenario.",
    },
    {
        "phase": "phase-0",
        "task": "Print detailed theory notes before coding changes.",
        "command": "python fra_simulation.py --mode theory",
        "success_criteria": "Theory section prints without errors and matches desk conventions.",
    },
    {
        "phase": "phase-0",
        "task": "Create focused learning roadmap for next sprint.",
        "command": "python fra_simulation.py --mode roadmap",
        "success_criteria": "Roadmap shows at least five advanced project directions.",
    },
    {
        "phase": "phase-0",
        "task": "Draft implementation backlog with execution checklist.",
        "command": "python fra_simulation.py --mode tasks",
        "success_criteria": "Each task has command + success criteria for Codex execution.",
    },
    {
        "phase": "phase-1",
        "task": "Run dual-curve FRA comparison and inspect basis impact.",
        "command": "python fra_simulation.py --mode demo --dual-curve-spread-bp 25",
        "success_criteria": "Demo prints single-curve vs dual-curve PV deltas for 1x3, 3x6, 6x9, 9x12.",
    },
    {
        "phase": "phase-1",
        "task": "Replay historical scenario library from CSV.",
        "command": "python fra_simulation.py --mode historical --scenario-file scenarios.csv",
        "success_criteria": "Episode summary prints total P&L, bucket P&L, and hedge residual.",
    },
    {
        "phase": "phase-1",
        "task": "Produce key-rate DV01 matrix and PCA factor report.",
        "command": "python fra_simulation.py --mode risk",
        "success_criteria": "Top-3 PCA explained variance and factor exposures are printed.",
    },
    {
        "phase": "phase-1",
        "task": "Run convexity grid for futures-vs-FRA slippage.",
        "command": "python fra_simulation.py --mode convexity --save-plot convexity_grid.png",
        "success_criteria": "Report table includes tenor, vol_assumption, convexity_bp, hedge_slippage_pnl.",
    },
    {
        "phase": "phase-1",
        "task": "Optimize constrained hedge basket under bounds.",
        "command": "python fra_simulation.py --mode optimize --objective dv01",
        "success_criteria": "Output shows optimal notionals, objective value, and binding constraints.",
    },
]


def ensure_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_dataframe(df: pd.DataFrame, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    df.to_csv(path, index=False)
    return path


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
    payer: bool = True
    hedge_target: str = "dv01"
    roll_down_months: int = 1
    dual_curve_spread_bp: float = 25.0
    custom_shock_front_bp: float = 100.0
    custom_shock_back_bp: float = 50.0
    steepening_front_bp: float = 10.0
    steepening_back_bp: float = 50.0
    flattening_front_bp: float = 50.0
    flattening_back_bp: float = 10.0
    hedge_min_ratio: float = -3.0
    hedge_max_ratio: float = 3.0
    liquidity_penalty: float = 1e-6


DEFAULT_CONFIG = SimulationConfig()


def _month_nodes() -> np.ndarray:
    return np.arange(1, 13, dtype=float)


def _tenor_pairs() -> List[Tuple[int, int]]:
    anchors = {(1, 3), (1, 6), (1, 9), (1, 12), (3, 6), (6, 9), (9, 12)}
    all_pairs = set()
    for start in range(1, 12):
        for end in range(start + 1, 13):
            all_pairs.add((start, end))
    all_pairs |= anchors
    return sorted(all_pairs)


def generate_base_curves(config: SimulationConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed)
    months = _month_nodes()
    huf_base = np.linspace(config.huf_level_1m, config.huf_level_12m, len(months))
    usd_base = np.linspace(config.usd_level_1m, config.usd_level_12m, len(months))
    huf = huf_base + rng.normal(0.0, config.noise_std, size=len(months))
    usd = usd_base + rng.normal(0.0, config.noise_std * 0.8, size=len(months))
    curve = pd.DataFrame({"month": months.astype(int), "t": months / 12.0, "huf_zero": huf, "usd_zero": usd})
    curve["huf_df"] = np.exp(-curve["huf_zero"] * curve["t"])
    curve["usd_df"] = np.exp(-curve["usd_zero"] * curve["t"])
    return curve


def build_fra_instruments(
    curve_df: pd.DataFrame,
    notional: float,
    fra_pairs: Optional[Iterable[Tuple[int, int]]] = None,
    ccy_prefix: str = "huf",
) -> pd.DataFrame:
    fra_pairs = _tenor_pairs() if fra_pairs is None else fra_pairs
    rows: List[Dict[str, float]] = []
    for start_m, end_m in fra_pairs:
        t1, t2 = start_m / 12.0, end_m / 12.0
        tau = t2 - t1
        p1 = curve_df.loc[curve_df["month"] == start_m, f"{ccy_prefix}_df"].iloc[0]
        p2 = curve_df.loc[curve_df["month"] == end_m, f"{ccy_prefix}_df"].iloc[0]
        fwd = (p1 / p2 - 1.0) / tau
        rows.append({"fra": f"{start_m}x{end_m}", "start_m": start_m, "end_m": end_m, "tau": tau, "notional": notional, "strike": fwd})
    return pd.DataFrame(rows)


def price_fra_dual_curve(
    fra_df: pd.DataFrame,
    projection_curve_df: pd.DataFrame,
    discount_curve_df: Optional[pd.DataFrame] = None,
    payer: bool = True,
    projection_prefix: str = "huf",
    discount_prefix: Optional[str] = None,
) -> pd.DataFrame:
    out = fra_df.copy()
    discount_curve_df = projection_curve_df if discount_curve_df is None else discount_curve_df
    discount_prefix = projection_prefix if discount_prefix is None else discount_prefix

    single_curve_pv, dual_curve_pv, dv01, fwds, df_end = [], [], [], [], []
    sign = 1.0 if payer else -1.0
    for _, r in out.iterrows():
        p1 = projection_curve_df.loc[projection_curve_df["month"] == int(r.start_m), f"{projection_prefix}_df"].iloc[0]
        p2 = projection_curve_df.loc[projection_curve_df["month"] == int(r.end_m), f"{projection_prefix}_df"].iloc[0]
        p2_disc = discount_curve_df.loc[discount_curve_df["month"] == int(r.end_m), f"{discount_prefix}_df"].iloc[0]
        fwd = (p1 / p2 - 1.0) / r.tau
        sc_pv = sign * r.notional * r.tau * (fwd - r.strike) * p2
        dc_pv = sign * r.notional * r.tau * (fwd - r.strike) * p2_disc

        bump = 1e-4
        p1_b = p1 * np.exp(-bump * (r.start_m / 12.0))
        p2_b = p2 * np.exp(-bump * (r.end_m / 12.0))
        p2_disc_b = p2_disc * np.exp(-bump * (r.end_m / 12.0))
        fwd_b = (p1_b / p2_b - 1.0) / r.tau
        pv_b = sign * r.notional * r.tau * (fwd_b - r.strike) * p2_disc_b

        single_curve_pv.append(sc_pv)
        dual_curve_pv.append(dc_pv)
        dv01.append(pv_b - dc_pv)
        fwds.append(fwd)
        df_end.append(p2_disc)

    out[f"{projection_prefix}_fwd"] = fwds
    out[f"{projection_prefix}_df_end"] = df_end
    out[f"{projection_prefix}_{'payer' if payer else 'receiver'}_pv"] = dual_curve_pv
    out[f"{projection_prefix}_single_curve_pv"] = single_curve_pv
    out[f"{projection_prefix}_dual_curve_pv"] = dual_curve_pv
    out[f"{projection_prefix}_dv01"] = dv01
    out[f"{projection_prefix}_orientation"] = "payer" if payer else "receiver"
    return out


def price_fra(fra_df: pd.DataFrame, curve_df: pd.DataFrame, payer: bool = True, ccy_prefix: str = "huf") -> pd.DataFrame:
    return price_fra_dual_curve(
        fra_df=fra_df,
        projection_curve_df=curve_df,
        discount_curve_df=curve_df,
        payer=payer,
        projection_prefix=ccy_prefix,
        discount_prefix=ccy_prefix,
    )


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

    shocked["huf_zero"] += shift_huf
    shocked["usd_zero"] += shift_usd
    shocked["huf_df"] = np.exp(-shocked["huf_zero"] * shocked["t"])
    shocked["usd_df"] = np.exp(-shocked["usd_zero"] * shocked["t"])
    return shocked


def roll_down_curve(curve_df: pd.DataFrame, months: int = 1) -> pd.DataFrame:
    out = curve_df.copy()
    for col in ["huf_zero", "usd_zero"]:
        arr = out[col].to_numpy()
        rolled = np.empty_like(arr)
        rolled[:] = arr[-1] if months >= len(arr) else np.r_[arr[months:], np.repeat(arr[-1], months)]
        out[col] = rolled
    out["huf_df"] = np.exp(-out["huf_zero"] * out["t"])
    out["usd_df"] = np.exp(-out["usd_zero"] * out["t"])
    return out


def compute_pnl_dv01(base_priced: pd.DataFrame, scenario_priced: pd.DataFrame, ccy_prefix: str = "huf", payer: bool = True):
    key_col = f"{ccy_prefix}_{'payer' if payer else 'receiver'}_pv"
    dv01_col = f"{ccy_prefix}_dv01"
    merged = base_priced[["fra", key_col, dv01_col]].merge(
        scenario_priced[["fra", key_col, dv01_col]], on="fra", suffixes=("_base", "_scn")
    )
    merged["pnl"] = merged[f"{key_col}_scn"] - merged[f"{key_col}_base"]
    merged["dv01_change"] = merged[f"{dv01_col}_scn"] - merged[f"{dv01_col}_base"]
    se = merged["fra"].str.split("x", expand=True).astype(int)
    merged["start_m"], merged["end_m"] = se[0], se[1]
    merged["bucket"] = pd.cut(merged["end_m"], [0, 3, 6, 9, 12], labels=["<=3M", "3-6M", "6-9M", "9-12M"], include_lowest=True)
    bucket = merged.groupby("bucket", observed=True)[["pnl", f"{dv01_col}_scn"]].sum().reset_index()
    return merged, bucket.rename(columns={f"{dv01_col}_scn": "bucket_dv01"})


def hedge_usd_residual(huf_results: pd.DataFrame, usd_results: pd.DataFrame, target: str = "dv01") -> Dict[str, float]:
    target = target.lower()
    if target not in {"dv01", "pnl"}:
        raise ValueError("target must be 'dv01' or 'pnl'")
    h = float(huf_results["huf_dv01_scn"].sum()) if target == "dv01" else float(huf_results["pnl"].sum())
    u = float(usd_results["usd_dv01_scn"].sum()) if target == "dv01" else float(usd_results["pnl"].sum())
    ratio = 0.0 if abs(u) < 1e-12 else -h / u
    return {
        "target": target,
        "hedge_ratio_usd": ratio,
        "huf_metric": h,
        "usd_metric": u,
        "net_dv01_after_hedge": float(huf_results["huf_dv01_scn"].sum() + ratio * usd_results["usd_dv01_scn"].sum()),
        "net_pnl_after_hedge": float(huf_results["pnl"].sum() + ratio * usd_results["pnl"].sum()),
    }


def optimize_hedge_basket(
    huf_gran: pd.DataFrame,
    usd_gran: pd.DataFrame,
    objective: str = "dv01",
    min_ratio: float = -3.0,
    max_ratio: float = 3.0,
    liquidity_penalty: float = 1e-6,
) -> pd.DataFrame:
    buckets = ["<=3M", "3-6M", "6-9M", "9-12M"]
    huf_col = "huf_dv01_scn" if objective == "dv01" else "pnl"
    usd_col = "usd_dv01_scn" if objective == "dv01" else "pnl"
    b = huf_gran.groupby("bucket", observed=True)[huf_col].sum().reindex(buckets).fillna(0.0).to_numpy()
    a = usd_gran.groupby("bucket", observed=True)[usd_col].sum().reindex(buckets).fillna(0.0).to_numpy()
    x = np.zeros_like(a)
    for i in range(len(a)):
        denom = a[i] * a[i] + liquidity_penalty
        x_star = 0.0 if denom < 1e-12 else -(a[i] * b[i]) / denom
        x[i] = np.clip(x_star, min_ratio, max_ratio)
    residual = b + a * x
    objective_value = float(np.sum(residual * residual) + liquidity_penalty * np.sum(x * x))
    return pd.DataFrame(
        {
            "instrument_bucket": buckets,
            "optimal_notional_ratio": x,
            "binding_constraint": [abs(v - min_ratio) < 1e-9 or abs(v - max_ratio) < 1e-9 for v in x],
            "residual": residual,
            "objective": objective,
            "objective_value": objective_value,
        }
    )


def load_historical_scenarios(csv_path: str) -> pd.DataFrame:
    required = {"date", "regime", "tenor_month", "shock_bp"}
    df = pd.read_csv(csv_path)
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Historical scenario file missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["tenor_month"] = pd.to_numeric(df["tenor_month"], errors="coerce")
    df["shock_bp"] = pd.to_numeric(df["shock_bp"], errors="coerce")
    if df[["date", "tenor_month", "shock_bp"]].isna().any().any():
        raise ValueError("Malformed historical rows: date/tenor_month/shock_bp must be parseable.")
    df["tenor_month"] = df["tenor_month"].astype(int)
    if (~df["tenor_month"].between(1, 12)).any():
        raise ValueError("tenor_month must be in 1..12.")
    counts = df.groupby(["date", "regime"])["tenor_month"].nunique()
    if (counts < 12).any():
        bad = counts[counts < 12]
        details = ", ".join([f"{d.date()}|{r}:{c}" for (d, r), c in bad.items()])
        raise ValueError(f"Missing tenor rows in historical episodes: {details}")
    return df.sort_values(["date", "regime", "tenor_month"]).reset_index(drop=True)


def apply_historical_episode(base_curve: pd.DataFrame, episode_df: pd.DataFrame) -> pd.DataFrame:
    shocked = base_curve.copy()
    shock = episode_df.set_index("tenor_month")["shock_bp"] / 10_000.0
    shocked["huf_zero"] += shocked["month"].map(shock).fillna(0.0)
    shocked["usd_zero"] += shocked["month"].map(shock * 0.7).fillna(0.0)
    shocked["huf_df"] = np.exp(-shocked["huf_zero"] * shocked["t"])
    shocked["usd_df"] = np.exp(-shocked["usd_zero"] * shocked["t"])
    return shocked


def compute_key_rate_dv01_matrix(fra_df: pd.DataFrame, curve_df: pd.DataFrame, ccy_prefix: str = "huf", payer: bool = True) -> pd.DataFrame:
    base = price_fra(fra_df, curve_df, payer=payer, ccy_prefix=ccy_prefix)
    pv_col = f"{ccy_prefix}_{'payer' if payer else 'receiver'}_pv"
    mat = pd.DataFrame({"fra": fra_df["fra"]})
    for tenor in range(1, 13):
        bumped = curve_df.copy()
        bumped.loc[bumped["month"] == tenor, f"{ccy_prefix}_zero"] += 1e-4
        bumped[f"{ccy_prefix}_df"] = np.exp(-bumped[f"{ccy_prefix}_zero"] * bumped["t"])
        bumped_px = price_fra(fra_df, bumped, payer=payer, ccy_prefix=ccy_prefix)
        mat[f"key_{tenor}m"] = bumped_px[pv_col].to_numpy() - base[pv_col].to_numpy()
    return mat


def pca_decompose_shocks(shock_matrix: np.ndarray, n_factors: int = 3) -> Dict[str, np.ndarray]:
    x = shock_matrix - shock_matrix.mean(axis=0, keepdims=True)
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    ev = (s * s) / np.sum(s * s)
    return {"loadings": vt[:n_factors], "explained_variance": ev[:n_factors]}


def convexity_adjustment_bp(t1: float, t2: float, sigma: float, mean_reversion: float) -> float:
    return 0.5 * sigma * sigma * t1 * t2 * np.exp(-2.0 * mean_reversion * t1) * 10_000.0


def run_convexity_grid(config: SimulationConfig = DEFAULT_CONFIG, vol_assumptions: Optional[List[float]] = None, mean_reversion: float = 0.25) -> pd.DataFrame:
    vol_assumptions = [0.01, 0.015, 0.02] if vol_assumptions is None else vol_assumptions
    base_curve = generate_base_curves(config)
    rows = []
    for start_m, end_m in [(1, 3), (3, 6), (6, 9), (9, 12)]:
        tau = (end_m - start_m) / 12.0
        df_end = base_curve.loc[base_curve["month"] == end_m, "huf_df"].iloc[0]
        for vol in vol_assumptions:
            conv_bp = convexity_adjustment_bp(start_m / 12.0, end_m / 12.0, vol, mean_reversion)
            rows.append(
                {
                    "tenor": f"{start_m}x{end_m}",
                    "vol_assumption": vol,
                    "convexity_bp": conv_bp,
                    "hedge_slippage_pnl": config.notional_huf * tau * (conv_bp / 10_000.0) * df_end,
                }
            )
    return pd.DataFrame(rows)


def run_scenario(
    regime: str,
    config: SimulationConfig = DEFAULT_CONFIG,
    payer: Optional[bool] = None,
    steepening: bool = False,
    flattening: bool = False,
    parallel_bp: float = 0.0,
) -> Dict[str, pd.DataFrame]:
    payer = config.payer if payer is None else payer
    base_curve = generate_base_curves(config)
    fra_huf = build_fra_instruments(base_curve, config.notional_huf, ccy_prefix="huf")
    fra_usd = build_fra_instruments(base_curve, config.notional_usd, ccy_prefix="usd")

    base_disc = base_curve.copy()
    base_disc["huf_zero"] -= config.dual_curve_spread_bp / 10_000.0
    base_disc["huf_df"] = np.exp(-base_disc["huf_zero"] * base_disc["t"])

    base_huf = price_fra_dual_curve(fra_huf, base_curve, base_disc, payer=payer, projection_prefix="huf", discount_prefix="huf")
    base_usd = price_fra(fra_usd, base_curve, payer=payer, ccy_prefix="usd")

    shocked_curve = apply_shock(base_curve, regime=regime, parallel_bp=parallel_bp, steepening=steepening, flattening=flattening, config=config)
    shocked_disc = shocked_curve.copy()
    shocked_disc["huf_zero"] -= config.dual_curve_spread_bp / 10_000.0
    shocked_disc["huf_df"] = np.exp(-shocked_disc["huf_zero"] * shocked_disc["t"])

    scn_huf = price_fra_dual_curve(fra_huf, shocked_curve, shocked_disc, payer=payer, projection_prefix="huf", discount_prefix="huf")
    scn_usd = price_fra(fra_usd, shocked_curve, payer=payer, ccy_prefix="usd")

    huf_gran, huf_bucket = compute_pnl_dv01(base_huf, scn_huf, ccy_prefix="huf", payer=payer)
    huf_gran = huf_gran.merge(scn_huf[["fra", "huf_single_curve_pv", "huf_dual_curve_pv"]], on="fra", how="left")
    huf_gran = huf_gran.rename(columns={"huf_single_curve_pv": "single_curve_pv", "huf_dual_curve_pv": "dual_curve_pv"})
    usd_gran, usd_bucket = compute_pnl_dv01(base_usd, scn_usd, ccy_prefix="usd", payer=payer)

    hedge = hedge_usd_residual(huf_gran, usd_gran, target=config.hedge_target)
    hedge_opt = optimize_hedge_basket(
        huf_gran,
        usd_gran,
        objective=config.hedge_target,
        min_ratio=config.hedge_min_ratio,
        max_ratio=config.hedge_max_ratio,
        liquidity_penalty=config.liquidity_penalty,
    )

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
        "hedge_optimized": hedge_opt,
        "roll_gran": roll_gran,
        "roll_bucket": roll_bucket,
    }


def plot_curves(base_curve: pd.DataFrame, shocked_curve: pd.DataFrame, title: str) -> None:
    if not HAS_MATPLOTLIB or plt is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharex=True)
    ax[0].plot(base_curve["month"], base_curve["huf_zero"] * 10_000, label="HUF Base", lw=2)
    ax[0].plot(shocked_curve["month"], shocked_curve["huf_zero"] * 10_000, label="HUF Shocked", lw=2)
    ax[0].set_title(f"HUF Curve - {title}")
    ax[0].legend()
    ax[1].plot(base_curve["month"], base_curve["usd_zero"] * 10_000, label="USD Base", lw=2)
    ax[1].plot(shocked_curve["month"], shocked_curve["usd_zero"] * 10_000, label="USD Shocked", lw=2)
    ax[1].set_title(f"USD Curve - {title}")
    ax[1].legend()
    fig.tight_layout()


def plot_results(bucket_df: pd.DataFrame, title: str, value_col: str = "pnl") -> None:
    if not HAS_MATPLOTLIB or plt is None:
        return
    if not HAS_SEABORN or sns is None:
        return
    plt.figure(figsize=(7, 4))
    sns.barplot(data=bucket_df, x="bucket", y=value_col, hue="bucket", legend=False, palette="viridis")
    plt.title(f"{value_col.upper()} by Bucket - {title}")
    plt.tight_layout()


def demo(config: SimulationConfig = DEFAULT_CONFIG, output_dir: Optional[Path] = None) -> None:
    if not HAS_MATPLOTLIB or not HAS_SEABORN:
        print("Plotting libraries not installed; running demo in text-only mode.")
    demo_dir = None
    if output_dir is not None:
        demo_dir = output_dir / "demo"
        demo_dir.mkdir(parents=True, exist_ok=True)
    scenarios = [("tariff_liberation", False, False), ("war_shock", True, False), ("debt_crisis", False, True)]
    for regime, steep, flat in scenarios:
        results = run_scenario(regime, config, steepening=steep, flattening=flat)
        print(f"\n=== Scenario: {regime} ===")
        print(results["huf_gran"][["fra", "pnl", "huf_dv01_scn", "single_curve_pv", "dual_curve_pv", "bucket"]].head(12).to_string(index=False))
        print("\nUSD Hedge Summary:")
        print(results["hedge"].to_string(index=False))
        print("\nConstrained Hedge Optimizer:")
        print(results["hedge_optimized"].to_string(index=False))
        anchor = results["huf_gran"][results["huf_gran"]["fra"].isin(["1x3", "3x6", "6x9", "9x12"])][["fra", "single_curve_pv", "dual_curve_pv"]].copy()
        anchor["pv_diff_dual_minus_single"] = anchor["dual_curve_pv"] - anchor["single_curve_pv"]
        print("\nDual-Curve Validation:")
        print(anchor.to_string(index=False))
        if demo_dir is not None:
            save_dataframe(results["huf_gran"], demo_dir, f"{regime}_huf_granular.csv")
            save_dataframe(results["huf_bucket"], demo_dir, f"{regime}_huf_bucket.csv")
            save_dataframe(results["hedge"], demo_dir, f"{regime}_hedge_summary.csv")
            save_dataframe(results["hedge_optimized"], demo_dir, f"{regime}_hedge_optimized.csv")
            save_dataframe(anchor, demo_dir, f"{regime}_dual_curve_validation.csv")
        plot_curves(results["base_curve"], results["shocked_curve"], title=regime)
        plot_results(results["huf_bucket"], title=regime, value_col="pnl")
    if HAS_MATPLOTLIB and plt is not None:
        plt.show()


def print_theory_notes() -> None:
    print(THEORY_NOTES.strip())


def print_learning_roadmap() -> None:
    print("=== ADVANCED FRA LEARNING ROADMAP ===")
    for idx, item in enumerate(PROJECT_ROADMAP, start=1):
        print(f"\n{idx}. {item['name']}")
        print(f"   Objective  : {item['objective']}")
        print(f"   Deliverable: {item['deliverable']}")


def print_codex_starter_tasks() -> None:
    print("=== CODEX STARTER TASKS ===")
    for idx, item in enumerate(CODEX_STARTER_TASKS, start=1):
        print(f"\n{idx}. {item['task']}")
        print(f"   Phase: {item['phase']}")
        print(f"   Run: {item['command']}")
        print(f"   Done when: {item['success_criteria']}")
    print("\nRecommended execution order:")
    print("  1) phase-0 baseline/theory/roadmap/tasks")
    print("  2) dual-curve -> historical replay -> risk/PCA -> convexity -> optimization")


def run_historical_mode(args: argparse.Namespace) -> None:
    if not args.scenario_file:
        raise ValueError("historical mode requires --scenario-file")
    cfg = SimulationConfig(dual_curve_spread_bp=args.dual_curve_spread_bp, hedge_target=args.objective)
    hist = load_historical_scenarios(args.scenario_file)
    if args.regime_filter:
        hist = hist[hist["regime"] == args.regime_filter]
    if hist.empty:
        raise ValueError("No rows after applying regime filter")

    base_curve = generate_base_curves(cfg)
    fra_huf = build_fra_instruments(base_curve, cfg.notional_huf, ccy_prefix="huf")
    fra_usd = build_fra_instruments(base_curve, cfg.notional_usd, ccy_prefix="usd")
    base_huf = price_fra(fra_huf, base_curve, payer=cfg.payer, ccy_prefix="huf")
    base_usd = price_fra(fra_usd, base_curve, payer=cfg.payer, ccy_prefix="usd")

    rows = []
    for (date, regime), ep in hist.groupby(["date", "regime"], sort=True):
        shocked = apply_historical_episode(base_curve, ep)
        scn_huf = price_fra(fra_huf, shocked, payer=cfg.payer, ccy_prefix="huf")
        scn_usd = price_fra(fra_usd, shocked, payer=cfg.payer, ccy_prefix="usd")
        huf_gran, huf_bucket = compute_pnl_dv01(base_huf, scn_huf, ccy_prefix="huf", payer=cfg.payer)
        usd_gran, _ = compute_pnl_dv01(base_usd, scn_usd, ccy_prefix="usd", payer=cfg.payer)
        hedge = hedge_usd_residual(huf_gran, usd_gran, target=cfg.hedge_target)
        rows.append(
            {
                "date": date.date().isoformat(),
                "regime": regime,
                "total_pnl": huf_gran["pnl"].sum(),
                "bucket_pnl": " | ".join([f"{r.bucket}:{r.pnl:,.0f}" for r in huf_bucket.itertuples(index=False)]),
                "hedge_residual": hedge["net_pnl_after_hedge"],
            }
        )
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    save_dataframe(out, ensure_output_dir(args.output_dir), "historical_episode_summary.csv")


def run_risk_mode(args: argparse.Namespace) -> None:
    cfg = SimulationConfig(dual_curve_spread_bp=args.dual_curve_spread_bp, hedge_target=args.objective)
    base_curve = generate_base_curves(cfg)
    fra_huf = build_fra_instruments(base_curve, cfg.notional_huf, ccy_prefix="huf")
    key = compute_key_rate_dv01_matrix(fra_huf, base_curve, ccy_prefix="huf", payer=cfg.payer)
    print("=== Key-rate DV01 matrix (head) ===")
    print(key.head(12).to_string(index=False))
    net_vec = key.drop(columns=["fra"]).sum(axis=0)
    print("\nNet key-rate vector:")
    print(net_vec.to_string())

    shocks = []
    for regime in ["tariff_liberation", "war_shock", "debt_crisis", "high_inflation"]:
        scn = apply_shock(base_curve, regime=regime, config=cfg)
        shocks.append((scn["huf_zero"] - base_curve["huf_zero"]).to_numpy())
    pca = pca_decompose_shocks(np.vstack(shocks), n_factors=3)
    factors = pd.DataFrame(pca["loadings"], columns=[f"{i}M" for i in range(1, 13)])
    exp = pca["loadings"] @ net_vec.to_numpy()
    print("\nTop-3 PCA factors:")
    print(factors.to_string(index=False))
    print("\nExplained variance:", np.round(pca["explained_variance"], 4))
    print("Portfolio factor exposures:", np.round(exp, 4))
    out_dir = ensure_output_dir(args.output_dir)
    save_dataframe(key, out_dir, "risk_key_rate_dv01.csv")
    save_dataframe(factors, out_dir, "risk_pca_loadings.csv")
    pd.DataFrame(
        [{"factor": idx + 1, "explained_variance": val, "portfolio_exposure": exp[idx]} for idx, val in enumerate(pca["explained_variance"])]
    ).to_csv(out_dir / "risk_pca_summary.csv", index=False)


def run_convexity_mode(args: argparse.Namespace) -> None:
    cfg = SimulationConfig(dual_curve_spread_bp=args.dual_curve_spread_bp)
    table = run_convexity_grid(cfg)
    print("=== Convexity assumptions ===")
    print("Stylized Gaussian short-rate convexity; interpret as model-risk indicator, not executable quote.")
    print(table.to_string(index=False))
    out_dir = ensure_output_dir(args.output_dir)
    save_dataframe(table, out_dir, "convexity_grid.csv")
    if args.save_plot:
        if not HAS_MATPLOTLIB or plt is None or not HAS_SEABORN or sns is None:
            raise RuntimeError("Cannot save convexity plot because matplotlib/seaborn are not installed.")
        plt.figure(figsize=(7, 4))
        sns.lineplot(data=table, x="tenor", y="convexity_bp", hue="vol_assumption", marker="o")
        plt.tight_layout()
        plot_path = Path(args.save_plot)
        if not plot_path.is_absolute():
            plot_path = out_dir / plot_path
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(plot_path, dpi=150)
        print(f"Saved plot: {plot_path}")


def run_optimize_mode(args: argparse.Namespace) -> None:
    cfg = SimulationConfig(dual_curve_spread_bp=args.dual_curve_spread_bp, hedge_target=args.objective)
    results = run_scenario("war_shock", cfg)
    print("=== Legacy single-ratio hedge ===")
    print(results["hedge"].to_string(index=False))
    print("\n=== Optimizer diagnostics ===")
    print(results["hedge_optimized"].to_string(index=False))
    out_dir = ensure_output_dir(args.output_dir)
    save_dataframe(results["hedge"], out_dir, "optimize_legacy_hedge.csv")
    save_dataframe(results["hedge_optimized"], out_dir, "optimize_hedge_optimized.csv")


def _parse_mode() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HUF FRA simulator + theory/learning toolkit.")
    parser.add_argument("--mode", default="demo", choices=["demo", "theory", "roadmap", "tasks", "historical", "risk", "convexity", "optimize", "all"])
    parser.add_argument("--scenario-file", default=None, help="Historical scenarios CSV.")
    parser.add_argument("--regime-filter", default=None, help="Optional historical regime filter.")
    parser.add_argument("--objective", default="dv01", choices=["dv01", "pnl"], help="Hedge objective.")
    parser.add_argument("--dual-curve-spread-bp", type=float, default=DEFAULT_CONFIG.dual_curve_spread_bp)
    parser.add_argument("--save-plot", default=None)
    parser.add_argument("--output-dir", default="outputs", help="Central directory for generated output artifacts.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_mode()
    cfg = SimulationConfig(dual_curve_spread_bp=args.dual_curve_spread_bp, hedge_target=args.objective)
    out_dir = ensure_output_dir(args.output_dir)
    if args.mode == "demo":
        demo(cfg, output_dir=out_dir)
    elif args.mode == "theory":
        print_theory_notes()
        (out_dir / "theory_notes.txt").write_text(THEORY_NOTES.strip() + "\n", encoding="utf-8")
    elif args.mode == "roadmap":
        print_learning_roadmap()
        (out_dir / "roadmap.txt").write_text(
            "\n".join([f"{i+1}. {x['name']} | Objective: {x['objective']} | Deliverable: {x['deliverable']}" for i, x in enumerate(PROJECT_ROADMAP)]) + "\n",
            encoding="utf-8",
        )
    elif args.mode == "tasks":
        print_codex_starter_tasks()
        (out_dir / "tasks.txt").write_text(
            "\n".join([f"{i+1}. {x['task']} | Phase: {x['phase']} | Run: {x['command']} | Done when: {x['success_criteria']}" for i, x in enumerate(CODEX_STARTER_TASKS)]) + "\n",
            encoding="utf-8",
        )
    elif args.mode == "historical":
        run_historical_mode(args)
    elif args.mode == "risk":
        run_risk_mode(args)
    elif args.mode == "convexity":
        run_convexity_mode(args)
    elif args.mode == "optimize":
        run_optimize_mode(args)
    elif args.mode == "all":
        print_theory_notes()
        print()
        print_learning_roadmap()
        print()
        print_codex_starter_tasks()
