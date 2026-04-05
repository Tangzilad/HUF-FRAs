import math

import numpy as np

from src.curves.cross_currency import (
    CrossCurrencyCurveBundle,
    CurveInstrumentSet,
    CurveInterpolator,
    InterpolationConfig,
    calibrate_cross_currency_bundle,
    calibrate_xccy_basis_curve,
    discount_factor,
    extract_fx_implied_basis,
)


def _base_market():
    tenors = [0.25, 0.5, 1.0, 2.0, 3.0]
    ois_huf = {t: 0.07 - 0.002 * t for t in tenors}
    ois_usd = {t: 0.05 - 0.0015 * t for t in tenors}
    ois_eur = {t: 0.03 - 0.001 * t for t in tenors}

    def df(curve, t):
        r = curve[t]
        return 1.0 / (1.0 + r * t)

    spot = 360.0
    true_basis = {t: 0.0010 + 0.0003 * t for t in tenors}
    fx_fwds = {
        t: spot * df(ois_huf, t) / (df(ois_usd, t) * math.exp(-true_basis[t] * t))
        for t in tenors
    }

    xccy_quotes = {t: true_basis[t] for t in tenors}
    return ois_huf, ois_usd, ois_eur, spot, fx_fwds, xccy_quotes


def test_joint_calibration_reprices_within_tolerance():
    ois_huf, ois_usd, _, spot, fwds, xccy_quotes = _base_market()
    dom_df = {t: 1.0 / (1.0 + r * t) for t, r in ois_huf.items()}
    for_df = {t: 1.0 / (1.0 + r * t) for t, r in ois_usd.items()}

    basis, diag = calibrate_xccy_basis_curve(
        pair="HUF/USD",
        spot=spot,
        forward_by_tenor=fwds,
        quoted_basis_by_tenor=xccy_quotes,
        domestic_discount_curve=dom_df,
        foreign_discount_curve=for_df,
        smooth_weight=0.0,
    )

    assert diag.rms_error < 1e-6
    assert diag.max_tenor_error < 1e-5
    for t, q in xccy_quotes.items():
        assert abs(basis[t] - q) < 2e-5


def test_interpolator_monotonic_discount_factors_and_linear_fallback():
    t = np.array([0.25, 0.5, 1.0, 2.0, 3.0])
    df = np.array([0.99, 0.985, 0.97, 0.94, 0.90])
    cubic = CurveInterpolator(t, df, InterpolationConfig(method="log_df", scheme="monotonic_cubic"))
    grid = np.linspace(0.25, 3.0, 40)
    vals = cubic.evaluate(grid)
    assert np.all(vals > 0.0)
    assert np.all(np.diff(vals) <= 1e-12)

    linear = CurveInterpolator(t[:2], df[:2], InterpolationConfig(method="log_df", scheme="monotonic_cubic"))
    v = linear.evaluate(np.array([0.3, 0.4]))
    assert np.all(v > 0.0)


def test_fx_implied_basis_and_no_arb_sanity():
    ois_huf, ois_usd, _, spot, fwds, _ = _base_market()
    dom_df = {t: 1.0 / (1.0 + r * t) for t, r in ois_huf.items()}
    for_df = {t: 1.0 / (1.0 + r * t) for t, r in ois_usd.items()}

    implied = extract_fx_implied_basis(spot, fwds, dom_df, for_df)
    for t, row in implied.items():
        assert row["implied_foreign_df"] > 0.0
        assert row["market_foreign_df"] > 0.0
        assert abs(row["basis_residual"]) < 0.01


def test_collateral_switch_changes_pv_direction_and_magnitude():
    ois_huf, ois_usd, ois_eur, spot, fwds, xccy_quotes = _base_market()
    instruments = CurveInstrumentSet(
        ois_by_ccy={"HUF": ois_huf, "USD": ois_usd, "EUR": ois_eur},
        irs_by_ccy={"HUF": ois_huf, "USD": ois_usd, "EUR": ois_eur},
        fx_spot={"HUF/USD": spot},
        fx_forwards={"HUF/USD": fwds},
        xccy_basis_by_pair={"HUF/USD": xccy_quotes},
    )
    bundle = calibrate_cross_currency_bundle(instruments)
    bundle.basis_term_structures["HUF-EUR"] = {t: -0.0008 for t in ois_huf}

    t = 2.0
    df_huf = discount_factor(bundle, "HUF", t, "HUF")
    df_usd_coll = discount_factor(bundle, "HUF", t, "USD")
    df_eur_coll = discount_factor(bundle, "HUF", t, "EUR")

    assert df_huf > 0.0
    assert df_usd_coll > 0.0
    assert df_eur_coll > 0.0

    cashflow = 100_000_000.0
    pv_huf = cashflow * df_huf
    pv_usd = cashflow * df_usd_coll
    pv_eur = cashflow * df_eur_coll

    assert pv_usd < pv_huf
    assert pv_eur > pv_huf
    assert abs(pv_usd - pv_huf) > 100.0
    assert abs(pv_eur - pv_huf) > 100.0
