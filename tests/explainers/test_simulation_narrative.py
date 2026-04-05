"""Tests for the post-simulation explanation generator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.explainers.simulation_narrative import (
    FRASimContext,
    ScenarioContext,
    SimulationNarrativeGenerator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sample_trade_pnl() -> pd.DataFrame:
    return pd.DataFrame([
        {"trade_id": "T1", "instrument": "FRA", "tenor_bucket": "front",
         "hedge_overlay": False, "pnl_rate": -5_000.0, "pnl_fx": 0.0,
         "pnl_basis": 0.0, "carry": 1_800.0, "pnl_total": -3_200.0},
        {"trade_id": "T2", "instrument": "Swap", "tenor_bucket": "belly",
         "hedge_overlay": False, "pnl_rate": -9_000.0, "pnl_fx": 0.0,
         "pnl_basis": -1_000.0, "carry": 3_200.0, "pnl_total": -6_800.0},
        {"trade_id": "T3", "instrument": "XCCY_BasisSwap", "tenor_bucket": "back",
         "hedge_overlay": True, "pnl_rate": 2_000.0, "pnl_fx": 0.0,
         "pnl_basis": 3_000.0, "carry": 850.0, "pnl_total": 5_850.0},
    ])


def _sample_decomposition() -> dict[str, pd.DataFrame]:
    return {
        "instrument": pd.DataFrame([
            {"instrument": "FRA", "pnl_rate": -5000, "pnl_fx": 0, "pnl_basis": 0, "carry": 1800, "pnl_total": -3200},
            {"instrument": "Swap", "pnl_rate": -9000, "pnl_fx": 0, "pnl_basis": -1000, "carry": 3200, "pnl_total": -6800},
            {"instrument": "XCCY_BasisSwap", "pnl_rate": 2000, "pnl_fx": 0, "pnl_basis": 3000, "carry": 850, "pnl_total": 5850},
        ]),
        "factor_bucket": pd.DataFrame([
            {"tenor_bucket": "front", "pnl_rate": -5000, "pnl_fx": 0, "pnl_basis": 0, "pnl_total": -3200},
            {"tenor_bucket": "belly", "pnl_rate": -9000, "pnl_fx": 0, "pnl_basis": -1000, "pnl_total": -6800},
            {"tenor_bucket": "back", "pnl_rate": 2000, "pnl_fx": 0, "pnl_basis": 3000, "pnl_total": 5850},
        ]),
    }


def _sample_scenario_ctx() -> ScenarioContext:
    return ScenarioContext(
        scenario_name="capital_outflow_shock",
        scenario_description="Foreign capital exits EM local markets.",
        rates_bp={"front": 120.0, "belly": 95.0, "back": 70.0},
        fx_pct={"spot": 8.0, "vol": 20.0},
        basis_bp={"front": 35.0, "belly": 30.0, "back": 25.0},
    )


# ---------------------------------------------------------------------------
# Scenario explanation tests
# ---------------------------------------------------------------------------

class TestScenarioExplanation:
    def test_returns_nonempty_markdown(self):
        gen = SimulationNarrativeGenerator()
        md = gen.explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert isinstance(md, str)
        assert len(md) > 100

    def test_contains_scenario_name(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Capital Outflow Shock" in md

    def test_contains_total_pnl(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Total P&L" in md

    def test_contains_factor_attribution(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Interest-rate moves" in md
        assert "Carry / roll-down" in md

    def test_contains_bucket_attribution(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "tenor bucket" in md.lower()

    def test_contains_hedge_effectiveness(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Hedge effectiveness" in md
        assert "Core portfolio" in md

    def test_contains_dominant_driver(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Dominant driver" in md

    def test_contains_actionable_takeaways(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Actionable takeaways" in md

    def test_carry_vs_shock_section(self):
        md = SimulationNarrativeGenerator().explain_scenario(
            _sample_trade_pnl(), _sample_decomposition(), _sample_scenario_ctx(),
        )
        assert "Carry vs. shock" in md


# ---------------------------------------------------------------------------
# FRA simulation explanation tests
# ---------------------------------------------------------------------------

class TestFRAExplanation:
    def _make_ctx(self) -> FRASimContext:
        rng = np.random.default_rng(42)
        pnl = rng.normal(500, 2000, size=1000)
        fwd = rng.normal(0.065, 0.005, size=1000)
        fut = fwd + 0.0002
        return FRASimContext(
            model_name="Ho-Lee", sigma=0.01, n_paths=1000,
            tenor_label="3x6", start=0.25, end=0.5,
            fra_pnl=pnl, fra_forward=fwd, futures_rate=fut,
        )

    def test_returns_nonempty_markdown(self):
        md = SimulationNarrativeGenerator().explain_fra_simulation(self._make_ctx())
        assert isinstance(md, str)
        assert len(md) > 100

    def test_contains_model_info(self):
        md = SimulationNarrativeGenerator().explain_fra_simulation(self._make_ctx())
        assert "Ho-Lee" in md
        assert "3x6" in md

    def test_contains_pnl_distribution(self):
        md = SimulationNarrativeGenerator().explain_fra_simulation(self._make_ctx())
        assert "Mean P&L" in md
        assert "Std Dev" in md
        assert "5th percentile" in md

    def test_contains_risk_interpretation(self):
        md = SimulationNarrativeGenerator().explain_fra_simulation(self._make_ctx())
        assert "Risk interpretation" in md
        assert "VaR proxy" in md

    def test_with_convexity_summary(self):
        summary = pd.DataFrame([
            {"tenor": "3x6", "vol_regime": 0.005, "convexity_adjustment": 0.0001,
             "fra_pnl_mean": 100.0, "fra_pnl_std": 500.0},
            {"tenor": "3x6", "vol_regime": 0.01, "convexity_adjustment": 0.0004,
             "fra_pnl_mean": 100.0, "fra_pnl_std": 1000.0},
            {"tenor": "3x6", "vol_regime": 0.02, "convexity_adjustment": 0.0016,
             "fra_pnl_mean": 100.0, "fra_pnl_std": 2000.0},
        ])
        md = SimulationNarrativeGenerator().explain_fra_simulation(
            self._make_ctx(), convexity_summary=summary,
        )
        assert "Convexity adjustment explained" in md
        assert "bp" in md

    def test_empty_pnl_handled(self):
        ctx = FRASimContext(model_name="Ho-Lee", sigma=0.01, n_paths=0)
        md = SimulationNarrativeGenerator().explain_fra_simulation(ctx)
        assert "No simulation data available" in md
