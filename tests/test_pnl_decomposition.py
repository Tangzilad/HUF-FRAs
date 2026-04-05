"""Tests for level/slope/curvature P&L decomposition."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.risk.pnl_decomposition import (
    BUCKET_ORDER,
    CurveShockComponents,
    aggregate_lsc,
    decompose_portfolio_lsc,
    decompose_rate_shocks,
    decompose_trade_lsc,
)
from src.risk.portfolio_shocks import Trade
from src.risk.scenarios.em_scenarios import EMScenario, em_scenario_library


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _capital_outflow() -> EMScenario:
    return em_scenario_library()[0]


def _sample_portfolio() -> list[Trade]:
    return [
        Trade(trade_id="F1", instrument="FRA", notional=10_000_000,
              tenor_bucket="front", dv01=-1800.0),
        Trade(trade_id="S1", instrument="Swap", notional=15_000_000,
              tenor_bucket="belly", dv01=-4000.0),
        Trade(trade_id="X1", instrument="XCCY_BasisSwap", notional=8_000_000,
              tenor_bucket="back", dv01=-900.0, basis01=-1200.0),
    ]


# ---------------------------------------------------------------------------
# decompose_rate_shocks
# ---------------------------------------------------------------------------

class TestDecomposeRateShocks:
    def test_returns_correct_type(self):
        c = decompose_rate_shocks(_capital_outflow())
        assert isinstance(c, CurveShockComponents)

    def test_level_is_mean_of_buckets(self):
        scn = _capital_outflow()
        c = decompose_rate_shocks(scn)
        expected = sum(scn.rates_bp[b] for b in BUCKET_ORDER) / 3.0
        assert math.isclose(c.level_bp, expected, rel_tol=1e-9)

    def test_slope_is_back_minus_front(self):
        scn = _capital_outflow()
        c = decompose_rate_shocks(scn)
        assert math.isclose(c.slope_bp, scn.rates_bp["back"] - scn.rates_bp["front"])

    def test_curvature_formula(self):
        scn = _capital_outflow()
        c = decompose_rate_shocks(scn)
        expected = scn.rates_bp["front"] + scn.rates_bp["back"] - 2.0 * scn.rates_bp["belly"]
        assert math.isclose(c.curvature_bp, expected)

    def test_reconstruction_matches_original_shocks(self):
        """Verify that level + slope + curvature loadings reconstruct original bucket shocks."""
        scn = _capital_outflow()
        c = decompose_rate_shocks(scn)
        # Reconstruct using the exact inverse: f = L - S/2 + C/6, b = L - C/3, k = L + S/2 + C/6
        reconstructed_front = c.level_bp - c.slope_bp / 2.0 + c.curvature_bp / 6.0
        reconstructed_belly = c.level_bp - c.curvature_bp / 3.0
        reconstructed_back = c.level_bp + c.slope_bp / 2.0 + c.curvature_bp / 6.0
        assert math.isclose(reconstructed_front, scn.rates_bp["front"], rel_tol=1e-9)
        assert math.isclose(reconstructed_belly, scn.rates_bp["belly"], rel_tol=1e-9)
        assert math.isclose(reconstructed_back, scn.rates_bp["back"], rel_tol=1e-9)


# ---------------------------------------------------------------------------
# decompose_portfolio_lsc
# ---------------------------------------------------------------------------

class TestDecomposePortfolioLSC:
    def test_returns_dataframe_with_expected_columns(self):
        df = decompose_portfolio_lsc(_sample_portfolio(), _capital_outflow())
        expected_cols = {"trade_id", "instrument", "tenor_bucket", "dv01",
                         "pnl_level", "pnl_slope", "pnl_curvature", "pnl_total"}
        assert expected_cols.issubset(df.columns)

    def test_row_count_matches_portfolio_size(self):
        portfolio = _sample_portfolio()
        df = decompose_portfolio_lsc(portfolio, _capital_outflow())
        assert len(df) == len(portfolio)

    def test_components_sum_to_total_per_trade(self):
        df = decompose_portfolio_lsc(_sample_portfolio(), _capital_outflow())
        for _, row in df.iterrows():
            component_sum = row["pnl_level"] + row["pnl_slope"] + row["pnl_curvature"]
            assert math.isclose(component_sum, row["pnl_total"], rel_tol=1e-9), (
                f"Trade {row['trade_id']}: components sum to {component_sum}, expected {row['pnl_total']}"
            )

    def test_aggregate_components_sum_to_aggregate_total(self):
        df = decompose_portfolio_lsc(_sample_portfolio(), _capital_outflow())
        total = df["pnl_total"].sum()
        component_sum = df["pnl_level"].sum() + df["pnl_slope"].sum() + df["pnl_curvature"].sum()
        assert math.isclose(component_sum, total, rel_tol=1e-9)

    def test_empty_portfolio_returns_empty_frame(self):
        df = decompose_portfolio_lsc([], _capital_outflow())
        assert df.empty
        assert "pnl_level" in df.columns

    def test_parallel_shock_concentrates_in_level(self):
        """When all buckets get the same shock, slope and curvature should be zero."""
        parallel = EMScenario(
            name="parallel", description="",
            rates_bp={"front": 100.0, "belly": 100.0, "back": 100.0},
            fx_pct={"spot": 0.0, "vol": 0.0},
            basis_bp={"front": 0.0, "belly": 0.0, "back": 0.0},
            risk_off={},
        )
        df = decompose_portfolio_lsc(_sample_portfolio(), parallel)
        assert math.isclose(df["pnl_slope"].sum(), 0.0, abs_tol=1e-9)
        assert math.isclose(df["pnl_curvature"].sum(), 0.0, abs_tol=1e-9)
        assert not math.isclose(df["pnl_level"].sum(), 0.0, abs_tol=1e-3)


# ---------------------------------------------------------------------------
# aggregate_lsc
# ---------------------------------------------------------------------------

class TestAggregateLSC:
    def test_returns_three_rows(self):
        df = decompose_portfolio_lsc(_sample_portfolio(), _capital_outflow())
        agg = aggregate_lsc(df)
        assert len(agg) == 3
        assert set(agg["factor"]) == {"Level", "Slope", "Curvature"}

    def test_percentages_sum_to_100(self):
        df = decompose_portfolio_lsc(_sample_portfolio(), _capital_outflow())
        agg = aggregate_lsc(df)
        assert math.isclose(agg["pct_of_total"].sum(), 100.0, rel_tol=1e-6)

    def test_empty_input(self):
        empty = pd.DataFrame(columns=[
            "trade_id", "instrument", "tenor_bucket", "dv01",
            "pnl_level", "pnl_slope", "pnl_curvature", "pnl_total",
        ])
        agg = aggregate_lsc(empty)
        assert agg.empty
