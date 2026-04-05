import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.analytics.cip_premium import (
    TermPremiumModel,
    compute_purified_cip_deviation,
    compute_raw_cip_deviation,
    construct_credit_liquidity_adjustment_curve,
    decompose_local_yields,
    load_cds_term_structure,
    load_treasury_ois_spread,
)


def _sample_curves():
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    tenors = [1.0, 2.0, 5.0]
    domestic_ois = pd.DataFrame(0.03, index=dates, columns=tenors)
    foreign_ois = pd.DataFrame(0.02, index=dates, columns=tenors)
    spot = pd.Series(360.0, index=dates)

    forwards = pd.DataFrame(index=dates, columns=tenors, dtype=float)
    for t in tenors:
        forwards[t] = spot * (1 + domestic_ois[t] * t) / (1 + foreign_ois[t] * t)
    return spot, forwards, domestic_ois, foreign_ois


def test_raw_cip_near_zero_under_parity():
    spot, forwards, domestic_ois, foreign_ois = _sample_curves()
    raw = compute_raw_cip_deviation(spot, forwards, domestic_ois, foreign_ois)
    raw_bp = raw["raw_basis_bp"]
    assert np.allclose(raw_bp.to_numpy(), 0.0, atol=1e-9)


def test_decomposition_identity_exact_sum():
    tenors = pd.Index([1.0, 2.0, 5.0], name="tenor")
    observed = pd.Series([0.060, 0.065, 0.070], index=tenors)
    risk_free = pd.Series([0.030, 0.032, 0.035], index=tenors)
    credit_liq = pd.Series([0.015, 0.016, 0.018], index=tenors)

    dec = decompose_local_yields(observed, risk_free, credit_liq)
    reconstructed = dec["risk_free_component"] + dec["credit_liquidity_component"] + dec["residual_term_premium"]
    assert np.allclose(reconstructed.to_numpy(), dec["observed_yield"].to_numpy(), atol=1e-12)


def test_missing_data_robustness_for_curve_loaders_and_model():
    cds_df = pd.DataFrame(
        {
            "tenor_years": [1, 2, 5, 10],
            "cds_spread_bp": [80, np.nan, 120, 150],
        }
    )
    liq_df = pd.DataFrame(
        {
            "tenor_years": [1, 3, 5, 10],
            "tsy_ois_spread_bp": [15, 20, np.nan, 35],
        }
    )

    cds_curve = load_cds_term_structure(cds_df)
    liq_curve = load_treasury_ois_spread(liq_df)
    adj = construct_credit_liquidity_adjustment_curve(cds_curve, liq_curve, target_tenors=[1, 2, 5, 7, 10])

    assert adj.notna().all()
    assert len(adj) == 5

    # rolling model should gracefully skip initial/missing rows
    idx = pd.date_range("2024-01-01", periods=12, freq="MS")
    X = pd.DataFrame(
        {
            "vix_proxy": np.linspace(12, 22, 12),
            "usd_funding_proxy": np.linspace(5, 8, 12),
            "em_risk_index": np.linspace(100, 115, 12),
            "inflation_surprise": [0.1, np.nan, 0.0, -0.2, 0.05, 0.03, 0.02, np.nan, -0.1, 0.2, 0.0, 0.1],
            "policy_spread": np.linspace(0.2, 0.5, 12),
            "fx_volatility": np.linspace(8, 12, 12),
        },
        index=idx,
    )
    y = 0.002 * X["vix_proxy"].ffill() + 0.001 * X["fx_volatility"]

    model = TermPremiumModel()
    fit = model.rolling_window_estimation(X, y, window=6, min_obs=4)
    assert not fit["coefficients"].empty
    assert "oos_prediction" in fit["tracking"].columns


def test_purified_reduces_stress_credit_noise_scale():
    dates = pd.date_range("2024-09-01", periods=3, freq="D")
    tenors = [1.0, 5.0]

    raw_basis = pd.DataFrame([[35.0, 45.0], [120.0, 140.0], [40.0, 50.0]], index=dates, columns=tenors)
    # stress date middle row: domestic sovereign-local credit widens sharply
    dom_sov = pd.DataFrame([[0.05, 0.055], [0.09, 0.10], [0.051, 0.056]], index=dates, columns=tenors)
    for_sov = pd.DataFrame([[0.03, 0.035], [0.031, 0.036], [0.03, 0.035]], index=dates, columns=tenors)
    dom_sup = pd.DataFrame([[0.045, 0.05], [0.055, 0.06], [0.046, 0.051]], index=dates, columns=tenors)
    for_sup = pd.DataFrame([[0.028, 0.033], [0.029, 0.034], [0.028, 0.033]], index=dates, columns=tenors)

    purified = compute_purified_cip_deviation(raw_basis, dom_sov, for_sov, dom_sup, for_sup)
    raw_stress = purified["raw_basis_bp"].iloc[1].mean()
    purified_stress = purified["purified_basis_bp"].iloc[1].mean()

    assert purified_stress < raw_stress
    assert raw_stress - purified_stress > 200
