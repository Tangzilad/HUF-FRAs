from __future__ import annotations

from app.helpers import build_curve_table, run_cip_path, run_pricing_engine, run_risk_engine


def test_curve_build_pipeline_returns_non_empty_schema(app_payload: dict) -> None:
    out = build_curve_table(app_payload)
    assert not out.empty
    assert {"currency", "tenor_years", "discount_factor"}.issubset(out.columns)


def test_pricing_pipeline_returns_result_without_raising(app_payload: dict) -> None:
    out = run_pricing_engine(app_payload)
    assert not out.empty
    assert {"n_paths", "fra_pnl_mean", "fra_pnl_std", "fra_forward_mean", "futures_rate_mean"}.issubset(out.columns)
    assert int(out.loc[0, "n_paths"]) > 0


def test_risk_pipeline_returns_result_without_raising(app_payload: dict) -> None:
    out = run_risk_engine(app_payload)
    assert {"trade_pnl", "instrument", "factor_bucket", "hedge_overlay"}.issubset(out.keys())
    assert not out["trade_pnl"].empty
    assert {"trade_id", "instrument", "pnl_total"}.issubset(out["trade_pnl"].columns)


def test_cip_pipeline_returns_non_empty_schema(app_payload_with_shifted_spot: dict) -> None:
    out = run_cip_path(app_payload_with_shifted_spot)
    assert not out.empty
    assert {"date", "tenor_years", "raw_basis_bp"}.issubset(out.columns)
