"""CIP premium analytics module.

This module provides three layers:
1) Raw CIP deviation calculators.
2) Purified CIP calculators using supranational proxy curves.
3) Yield decomposition and term-premium analytics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


BP = 1e4


@dataclass(frozen=True)
class CurveBundle:
    """Container for tenor-aligned curves.

    All rate fields are decimal annualized rates (0.05 = 5%).
    Spread fields are in basis points unless noted.
    """

    tenors_years: Sequence[float]
    domestic_ois: Sequence[float]
    foreign_ois: Sequence[float]
    domestic_sovereign: Optional[Sequence[float]] = None
    foreign_sovereign: Optional[Sequence[float]] = None
    domestic_supranational: Optional[Sequence[float]] = None
    foreign_supranational: Optional[Sequence[float]] = None


# -----------------------------
# Layer 1: raw CIP deviations
# -----------------------------
def fx_implied_domestic_rate(spot: pd.Series, forward: pd.DataFrame, foreign_rate: pd.Series) -> pd.DataFrame:
    """Compute domestic rates implied by FX forwards under covered parity algebra.

    Formula (simple compounding):
        r_dom_implied = (((F/S) * (1 + r_for*T)) - 1) / T

    Args:
        spot: date-indexed spot FX series quoted domestic-per-foreign.
        forward: date-indexed forward levels with tenor columns in years.
        foreign_rate: date-indexed foreign benchmark rate for each tenor/date.
            If this is a panel (MultiIndex columns), callers should pass one tenor at a time.
    """

    implied = pd.DataFrame(index=forward.index, columns=forward.columns, dtype=float)
    for tenor in forward.columns:
        t = float(tenor)
        implied[tenor] = (((forward[tenor] / spot) * (1.0 + foreign_rate[tenor] * t)) - 1.0) / t
    return implied


def compute_raw_cip_deviation(
    spot: pd.Series,
    forward: pd.DataFrame,
    domestic_ois: pd.DataFrame,
    foreign_ois: pd.DataFrame,
) -> pd.DataFrame:
    """Raw CIP basis/deviation panel (date x tenor).

    Output columns use a pandas MultiIndex:
        - ("fx_implied_domestic", tenor)
        - ("benchmark_domestic", tenor)
        - ("raw_basis_bp", tenor)

    raw_basis_bp := (fx_implied_domestic - domestic_ois) * 10,000
    """

    implied = fx_implied_domestic_rate(spot=spot, forward=forward, foreign_rate=foreign_ois)
    raw_basis_bp = (implied - domestic_ois) * BP

    out = pd.concat(
        {
            "fx_implied_domestic": implied,
            "benchmark_domestic": domestic_ois,
            "raw_basis_bp": raw_basis_bp,
        },
        axis=1,
    )
    return out.sort_index(axis=1)


def point_in_time_and_panel(raw_panel: pd.DataFrame, as_of: Optional[pd.Timestamp] = None) -> Dict[str, pd.DataFrame]:
    """Return point-in-time and full-tenor panel deviations."""

    if as_of is None:
        as_of = raw_panel.index.max()
    point = raw_panel.loc[[as_of]]
    return {"point_in_time": point, "tenor_panel": raw_panel}


# ---------------------------------------------
# Layer 2: purified CIP (supranational proxies)
# ---------------------------------------------
def compute_purified_cip_deviation(
    raw_basis_bp: pd.DataFrame,
    domestic_sovereign: pd.DataFrame,
    foreign_sovereign: pd.DataFrame,
    domestic_supranational: pd.DataFrame,
    foreign_supranational: pd.DataFrame,
) -> pd.DataFrame:
    """Strip local credit effects from raw CIP basis using supranational proxies.

    local_credit_spread = sovereign - supranational
    credit_differential = local_credit_spread_domestic - local_credit_spread_foreign
    purified_basis_bp = raw_basis_bp - credit_differential * 10,000
    """

    local_credit_dom = domestic_sovereign - domestic_supranational
    local_credit_for = foreign_sovereign - foreign_supranational
    credit_differential_bp = (local_credit_dom - local_credit_for) * BP
    purified_basis_bp = raw_basis_bp - credit_differential_bp

    return pd.concat(
        {
            "raw_basis_bp": raw_basis_bp,
            "credit_diff_bp": credit_differential_bp,
            "purified_basis_bp": purified_basis_bp,
        },
        axis=1,
    ).sort_index(axis=1)


# ----------------------------------------------------------
# Layer 3: credit/liquidity + decomposition + term premium
# ----------------------------------------------------------
def load_cds_term_structure(df: pd.DataFrame, tenor_col: str = "tenor_years", spread_col: str = "cds_spread_bp") -> pd.Series:
    """Load CDS curve into a tenor-indexed series (bp)."""

    clean = df[[tenor_col, spread_col]].dropna().copy()
    clean[tenor_col] = clean[tenor_col].astype(float)
    clean = clean.sort_values(tenor_col).drop_duplicates(subset=tenor_col, keep="last")
    return clean.set_index(tenor_col)[spread_col].astype(float)


def load_treasury_ois_spread(df: pd.DataFrame, tenor_col: str = "tenor_years", spread_col: str = "tsy_ois_spread_bp") -> pd.Series:
    """Load treasury-OIS spread curve into a tenor-indexed series (bp)."""

    clean = df[[tenor_col, spread_col]].dropna().copy()
    clean[tenor_col] = clean[tenor_col].astype(float)
    clean = clean.sort_values(tenor_col).drop_duplicates(subset=tenor_col, keep="last")
    return clean.set_index(tenor_col)[spread_col].astype(float)


def map_curve_to_tenors(curve_bp: pd.Series, target_tenors: Iterable[float]) -> pd.Series:
    """Linearly interpolate a spread curve (bp) onto target tenors."""

    x = curve_bp.index.to_numpy(dtype=float)
    y = curve_bp.to_numpy(dtype=float)
    t = np.array(list(target_tenors), dtype=float)
    mapped = np.interp(t, x, y)
    return pd.Series(mapped, index=t, dtype=float)


def construct_credit_liquidity_adjustment_curve(
    cds_curve_bp: pd.Series,
    treasury_ois_curve_bp: pd.Series,
    target_tenors: Iterable[float],
    cds_weight: float = 0.7,
    liquidity_weight: float = 0.3,
) -> pd.Series:
    """Construct weighted credit/liquidity adjustment curve in decimal rates."""

    if not np.isclose(cds_weight + liquidity_weight, 1.0):
        raise ValueError("cds_weight + liquidity_weight must equal 1.0")

    cds_mapped_bp = map_curve_to_tenors(cds_curve_bp, target_tenors)
    liq_mapped_bp = map_curve_to_tenors(treasury_ois_curve_bp, target_tenors)
    combo_bp = cds_weight * cds_mapped_bp + liquidity_weight * liq_mapped_bp
    return combo_bp / BP


def decompose_local_yields(
    observed_local_yields: pd.Series,
    risk_free_curve: pd.Series,
    credit_liquidity_curve: pd.Series,
) -> pd.DataFrame:
    """Yield decomposition identity.

    observed_yield = risk_free + credit_liquidity + residual_term_premium
    """

    aligned = pd.concat(
        {
            "observed_yield": observed_local_yields,
            "risk_free_component": risk_free_curve,
            "credit_liquidity_component": credit_liquidity_curve,
        },
        axis=1,
    ).sort_index()
    aligned["residual_term_premium"] = (
        aligned["observed_yield"] - aligned["risk_free_component"] - aligned["credit_liquidity_component"]
    )
    return aligned


class TermPremiumModel:
    """Rolling-window factor regression interface for term-premium tracking.

    Supports global risk and domestic variables supplied in `X`.
    """

    def __init__(self, intercept: bool = True):
        self.intercept = intercept

    def _design(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.assign(const=1.0) if self.intercept else X.copy()

    def rolling_window_estimation(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        window: int = 60,
        min_obs: int = 24,
    ) -> Dict[str, pd.DataFrame | pd.Series]:
        """Fit rolling OLS and generate one-step-ahead out-of-sample predictions."""

        Xd = self._design(X).astype(float)
        joined = Xd.join(y.rename("target"), how="inner").dropna()

        coef_rows = []
        oos_pred = pd.Series(index=joined.index, dtype=float)

        for i in range(len(joined)):
            if i + 1 < min_obs:
                continue
            start = max(0, i + 1 - window)
            train = joined.iloc[start : i + 1]
            x_train = train.drop(columns=["target"]).to_numpy()
            y_train = train["target"].to_numpy()
            beta, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)

            coef_rows.append(pd.Series(beta, index=train.drop(columns=["target"]).columns, name=train.index[-1]))

            if i + 1 < len(joined):
                x_next = joined.drop(columns=["target"]).iloc[i + 1].to_numpy()
                oos_pred.iloc[i + 1] = float(np.dot(x_next, beta))

        coef_df = pd.DataFrame(coef_rows)
        tracking = pd.DataFrame({"actual": joined["target"], "oos_prediction": oos_pred})
        tracking["oos_error"] = tracking["actual"] - tracking["oos_prediction"]
        return {"coefficients": coef_df, "tracking": tracking}


def coefficient_sign_stability(coefficients: pd.DataFrame, expected_signs: Mapping[str, int]) -> pd.DataFrame:
    """Check coefficient sign consistency over time.

    expected_signs: +1 for positive expected sign, -1 for negative.
    """

    rows = []
    for factor, sign in expected_signs.items():
        if factor not in coefficients.columns:
            rows.append({"factor": factor, "coverage": 0.0, "sign_match_ratio": np.nan})
            continue

        series = coefficients[factor].dropna()
        if series.empty:
            rows.append({"factor": factor, "coverage": 0.0, "sign_match_ratio": np.nan})
            continue

        matches = ((np.sign(series) == sign)).mean()
        rows.append({"factor": factor, "coverage": len(series) / len(coefficients), "sign_match_ratio": matches})
    return pd.DataFrame(rows)


def regime_sensitivity(coefficients: pd.DataFrame, regime_flag: pd.Series) -> pd.DataFrame:
    """Compare mean coefficients across low/high regime states."""

    aligned = coefficients.join(regime_flag.rename("regime"), how="inner").dropna()
    low = aligned[aligned["regime"] == 0].drop(columns=["regime"]).mean()
    high = aligned[aligned["regime"] == 1].drop(columns=["regime"]).mean()
    out = pd.DataFrame({"low_regime_mean": low, "high_regime_mean": high})
    out["delta_high_minus_low"] = out["high_regime_mean"] - out["low_regime_mean"]
    return out


def attribution_by_tenor_date(decomposition_panel: pd.DataFrame) -> pd.DataFrame:
    """Return contribution shares by tenor/date from decomposition panel.

    Expects columns: observed_yield, risk_free_component, credit_liquidity_component,
    residual_term_premium and a MultiIndex [date, tenor] index.
    """

    required = {
        "observed_yield",
        "risk_free_component",
        "credit_liquidity_component",
        "residual_term_premium",
    }
    missing = required - set(decomposition_panel.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = decomposition_panel.copy()
    denom = out["observed_yield"].replace(0.0, np.nan)
    for c in ["risk_free_component", "credit_liquidity_component", "residual_term_premium"]:
        out[f"{c}_share"] = out[c] / denom
    return out


def stress_snapshot(
    decomposition_panel: pd.DataFrame,
    stress_dates: Iterable[pd.Timestamp],
    tenor_filter: Optional[Iterable[float]] = None,
) -> pd.DataFrame:
    """Get decomposition contribution snapshots during stress dates."""

    idx = decomposition_panel.index
    if not isinstance(idx, pd.MultiIndex) or idx.nlevels != 2:
        raise ValueError("decomposition_panel must be indexed by MultiIndex(date, tenor)")

    out = decomposition_panel.loc[(list(stress_dates), slice(None)), :]
    if tenor_filter is not None:
        out = out.loc[(slice(None), list(tenor_filter)), :]
    return out
