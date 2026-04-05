from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.short_rate import HoLeeModel, HullWhite1FModel, convexity_adjustment_summary


def flat_curve(rate: float = 0.03) -> pd.DataFrame:
    t = np.linspace(1 / 12, 5.0, 60)
    return pd.DataFrame({"t": t, "zero_rate": np.full_like(t, rate)})


def test_ho_lee_moment_validation() -> None:
    model = HoLeeModel(sigma=0.015)
    curve = flat_curve()
    model.fit_initial_curve(curve)
    sim = model.simulate_paths(n_paths=20_000, time_grid=np.linspace(0.05, 3.0, 61), seed=7)
    chk = model.validate_moments(sim)
    last = chk.iloc[-1]
    assert abs(last["sim_mean"] - last["theory_mean"]) < 2e-3
    assert abs(last["sim_var"] - last["theory_var"]) < 2e-3


def test_hull_white_calibration_recovery_constant_params() -> None:
    expiry = np.array([0.5, 1.0, 2.0, 3.0, 5.0])
    true_a, true_sigma = 0.25, 0.013
    normal_vol = true_sigma * (1 - np.exp(-true_a * expiry)) / (true_a * np.sqrt(expiry))
    market = pd.DataFrame({"expiry": expiry, "normal_vol": normal_vol})

    model = HullWhite1FModel(a=0.1, sigma=0.02)
    result = model.calibrate_to_options(market)

    assert result["rmse"] < 1e-4
    assert abs(model.a - true_a) < 5e-2
    assert abs(model.sigma - true_sigma) < 5e-3


def test_stability_small_and_large_mean_reversion() -> None:
    curve = flat_curve()
    tgrid = np.linspace(0.0, 2.0, 49)
    for a in [1e-4, 3.0]:
        model = HullWhite1FModel(a=a, sigma=0.01)
        model.fit_initial_curve(curve)
        sim = model.simulate_paths(n_paths=1_000, time_grid=tgrid, seed=1)
        assert np.isfinite(sim.short_rates).all()


def test_seed_reproducibility() -> None:
    curve = flat_curve()
    model = HoLeeModel(sigma=0.01)
    model.fit_initial_curve(curve)

    s1 = model.simulate_paths(256, np.linspace(0.0, 1.0, 13), seed=123).short_rates
    s2 = model.simulate_paths(256, np.linspace(0.0, 1.0, 13), seed=123).short_rates
    s3 = model.simulate_paths(256, np.linspace(0.0, 1.0, 13), seed=124).short_rates

    assert np.allclose(s1, s2)
    assert not np.allclose(s1, s3)


def test_convexity_summary_outputs() -> None:
    curve = flat_curve(0.04)
    model = HoLeeModel(sigma=0.01)
    out = convexity_adjustment_summary(
        model,
        curve,
        tenors=[(0.25, 0.5), (0.5, 1.0)],
        vol_regimes=[0.005, 0.02],
        n_paths=2000,
        seed=9,
    )
    assert len(out) == 4
    assert {"convexity_adjustment", "fra_pnl_std"}.issubset(out.columns)
