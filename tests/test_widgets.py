from __future__ import annotations

import pandas as pd

from app.widgets import PAGES, render_sidebar_controls


EXPECTED_PAGES = ["Start here", "CIP basis", "Cross-currency", "Short-rate FRA", "Risk P&L", "Stress Lab"]


def test_navigation_page_list_exact_and_ordered() -> None:
    assert PAGES == EXPECTED_PAGES


def test_render_sidebar_controls_normalizes_outputs() -> None:
    controls = render_sidebar_controls(
        defaults={
            "valuation_date": "2026-01-15",
            "curve_source": "Upload",
            "fra_labels": ["1x3", "9x12"],
            "notional": 2_500_000,
            "direction": "Receiver",
            "day_count": "30/360",
            "compounding": "Continuous",
            "model": "Hull-White",
            "scenario": "Currency Devaluation Shock",
            "hedge_instruments": ["USD FRA", "XCCY Basis Swap"],
            "explanation_mode": "Learning",
        },
        uploaded_curve=pd.DataFrame({"t": [0.25, 0.5, 1.0], "zero_rate": [0.04, 0.042, 0.045]}),
    )

    assert controls.curve_source == "uploaded"
    assert controls.fra_tenors_years == [(1 / 12.0, 3 / 12.0), (9 / 12.0, 12 / 12.0)]
    assert controls.direction == "receiver"
    assert controls.day_count == "30_360"
    assert controls.compounding == "continuous"
    assert controls.model == "hull_white"
    assert controls.scenario == "currency_devaluation_shock"
    assert controls.hedge_instruments == ["FRA", "XCCY_BasisSwap"]
    assert controls.explanation_mode == "learning"
    assert controls.uploaded_curve is not None
    assert controls.warnings == []


def test_render_sidebar_controls_warns_and_falls_back_for_bad_upload() -> None:
    controls = render_sidebar_controls(
        defaults={
            "curve_source": "Upload",
            "fra_labels": [],
            "notional": -100,
            "hedge_instruments": [],
        },
        uploaded_curve=pd.DataFrame({"maturity": [0.25], "rate": [0.04]}),
    )

    assert controls.curve_source == "synthetic"
    assert controls.notional == 1_000_000.0
    assert controls.fra_labels == ["3x6"]
    assert controls.hedge_instruments == ["FRA"]
    assert any("missing required fields" in w.lower() for w in controls.warnings)
    assert any("reverted to synthetic" in w.lower() for w in controls.warnings)


def test_render_sidebar_controls_defaults_to_start_here() -> None:
    controls = render_sidebar_controls(defaults={})
    assert controls.active_page == "Start here"
