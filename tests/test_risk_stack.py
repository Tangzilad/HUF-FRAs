from __future__ import annotations

import numpy as np
import pandas as pd

from src.risk.backtesting import constraint_binding_report
from src.risk.factor_models import PCAPreprocessConfig, prepare_pca_inputs
from src.risk.hedging_optimizer import OptimizerConfig, optimize_hedges
from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import em_scenario_library
from src.risk.tail_risk import expected_shortfall, historical_var, marginal_component_var_es, parametric_var


def test_macro_mixed_frequency_pca_inputs_are_standardized() -> None:
    rates = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=20, freq="D"),
            "huf_2y": np.linspace(0.06, 0.08, 20),
            "huf_5y": np.linspace(0.065, 0.082, 20),
        }
    )
    macro = pd.DataFrame(
        {
            "date": pd.date_range("2023-12-01", periods=4, freq="MS"),
            "inflation_expectation": [4.2, 4.4, 4.7, 5.0],
            "fx_level": [360, 363, 367, 372],
            "fx_vol": [8.0, 8.5, 9.0, 10.0],
            "risk_off_indicator": [18, 17, 21, 25],
        }
    )
    out = prepare_pca_inputs(rates, macro, config=PCAPreprocessConfig(target_freq="D", standardize=True))
    assert not out.empty
    assert np.allclose(out.mean().abs().to_numpy() < 1e-6, True)


def test_em_scenario_propagation_and_decomposition() -> None:
    scn = em_scenario_library()[0]
    portfolio = [
        Trade("T1", "FRA", 10_000_000, "front", dv01=-2500),
        Trade("T2", "Swap", 15_000_000, "belly", dv01=-4200),
        Trade("T3", "XCCY_BasisSwap", 8_000_000, "back", basis01=-1800, hedge_overlay=True),
        Trade("T4", "FX_Forward", 5_000_000, "front", fx_delta=-3_000_000, hedge_overlay=True),
    ]
    pnl = propagate_scenario(portfolio, scn)
    dec = decompose_pnl(pnl)
    assert set(dec.keys()) == {"instrument", "factor_bucket", "hedge_overlay"}
    assert pnl["pnl_total"].sum() != 0


def test_optimizer_generates_constraint_explainability_report() -> None:
    exposure = np.array([100.0, -50.0, 20.0])
    hedge_matrix = np.array(
        [
            [-0.8, -0.1, -0.2],
            [0.2, -0.9, -0.1],
            [-0.1, -0.2, -0.6],
        ]
    )
    carry = np.array([0.5, 0.2, 0.3])
    liq = np.array([0.4, 0.3, 0.9])
    out = optimize_hedges(
        exposure,
        hedge_matrix,
        carry,
        liq,
        instruments=["IRS", "XCCY", "FXFWD"],
        tenor_bucket=["front", "belly", "front"],
        config=OptimizerConfig(max_notional=1.0),
    )
    report = constraint_binding_report(out["solution"])
    assert "binding_constraints" in report.columns
    assert "rationale" in report.columns


def test_tail_risk_outputs_non_negative_values() -> None:
    returns = pd.Series(np.array([-0.01, 0.002, -0.015, 0.005, -0.02, 0.003]))
    assert parametric_var(returns, 0.95) >= 0
    assert historical_var(returns, 0.95) >= 0
    assert expected_shortfall(returns, 0.95, method="historical") >= historical_var(returns, 0.95)

    pnl = pd.DataFrame(
        {
            "rates": [-100, 25, -60, 10, -45],
            "fx": [-40, 5, -20, 8, -15],
            "basis": [-30, 2, -18, 4, -10],
        }
    )
    pnl["total"] = pnl.sum(axis=1)
    out = marginal_component_var_es(pnl, total_col="total")
    assert "decomposition" in out
