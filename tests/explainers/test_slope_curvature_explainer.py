"""Tests for the SlopeCurvatureExplainer."""

from __future__ import annotations

import pandas as pd

from src.explainers.slope_curvature import SlopeCurvatureExplainer
from src.risk.pnl_decomposition import CurveShockComponents


class TestSlopeCurvatureExplainerBase:
    """Verify BaseExplainer contract is satisfied."""

    def test_explain_returns_nonempty_markdown(self):
        text = SlopeCurvatureExplainer().explain()
        assert len(text) > 200

    def test_contains_level_slope_curvature_concepts(self):
        text = SlopeCurvatureExplainer().explain()
        assert "Level" in text or "level" in text
        assert "Slope" in text or "slope" in text
        assert "Curvature" in text or "curvature" in text

    def test_contains_trading_implications(self):
        text = SlopeCurvatureExplainer().explain()
        assert "duration" in text.lower() or "hedge" in text.lower()


class TestSlopeCurvatureNarrate:
    def _steepening_components(self) -> CurveShockComponents:
        return CurveShockComponents(level_bp=95.0, slope_bp=-50.0, curvature_bp=10.0)

    def _sample_aggregate(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"factor": "Level", "pnl": -50000.0, "dv01_contribution": -3000.0, "pct_of_total": 60.0},
            {"factor": "Slope", "pnl": -25000.0, "dv01_contribution": -1500.0, "pct_of_total": 30.0},
            {"factor": "Curvature", "pnl": -8000.0, "dv01_contribution": -500.0, "pct_of_total": 10.0},
        ])

    def test_narrate_returns_markdown(self):
        md = SlopeCurvatureExplainer().narrate(
            self._steepening_components(), self._sample_aggregate(),
        )
        assert isinstance(md, str)
        assert "## Yield-curve P&L decomposition" in md

    def test_narrate_contains_shock_profile(self):
        md = SlopeCurvatureExplainer().narrate(
            self._steepening_components(), self._sample_aggregate(),
        )
        assert "Scenario shock profile" in md
        assert "Level" in md

    def test_narrate_contains_pnl_table(self):
        md = SlopeCurvatureExplainer().narrate(
            self._steepening_components(), self._sample_aggregate(),
        )
        assert "P&L attribution" in md
        assert "% of gross" in md

    def test_narrate_identifies_dominant_factor(self):
        md = SlopeCurvatureExplainer().narrate(
            self._steepening_components(), self._sample_aggregate(),
        )
        assert "level dominates" in md.lower()

    def test_narrate_contains_macro_context(self):
        md = SlopeCurvatureExplainer().narrate(
            self._steepening_components(), self._sample_aggregate(),
        )
        assert "Macro interpretation" in md

    def test_narrate_empty_aggregate(self):
        empty = pd.DataFrame(columns=["factor", "pnl", "dv01_contribution", "pct_of_total"])
        md = SlopeCurvatureExplainer().narrate(
            CurveShockComponents(0, 0, 0), empty,
        )
        assert "No rate P&L" in md

    def test_bear_steepener_narrative(self):
        """Bear steepener: level positive, slope positive."""
        c = CurveShockComponents(level_bp=80.0, slope_bp=60.0, curvature_bp=5.0)
        agg = pd.DataFrame([
            {"factor": "Level", "pnl": -30000, "dv01_contribution": -2000, "pct_of_total": 35},
            {"factor": "Slope", "pnl": -50000, "dv01_contribution": -3000, "pct_of_total": 58},
            {"factor": "Curvature", "pnl": -6000, "dv01_contribution": -400, "pct_of_total": 7},
        ])
        md = SlopeCurvatureExplainer().narrate(c, agg)
        assert "steepening" in md.lower()
        assert "Bear steepener" in md or "bear steepener" in md.lower()

    def test_bull_flattener_narrative(self):
        """Bull flattener: level negative, slope negative."""
        c = CurveShockComponents(level_bp=-40.0, slope_bp=-30.0, curvature_bp=2.0)
        agg = pd.DataFrame([
            {"factor": "Level", "pnl": 20000, "dv01_contribution": 1500, "pct_of_total": 55},
            {"factor": "Slope", "pnl": 15000, "dv01_contribution": 1000, "pct_of_total": 40},
            {"factor": "Curvature", "pnl": 2000, "dv01_contribution": 150, "pct_of_total": 5},
        ])
        md = SlopeCurvatureExplainer().narrate(c, agg)
        assert "flattener" in md.lower() or "flatten" in md.lower()
