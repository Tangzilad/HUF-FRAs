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
from app.app import run_app
from app.helpers import ensure_pipeline_outputs
from app.state import (
    STATE_KEY_COMPUTE_FINGERPRINT,
    STATE_KEY_FRA_PAIR,
    STATE_KEY_INITIALIZED,
    STATE_KEY_NOTIONAL,
    compute_fingerprint_from_state,
    init_state,
)


def test_init_state_called_once() -> None:
    state = {}
    init_state(state)
    first_fp = state[STATE_KEY_COMPUTE_FINGERPRINT]
    assert state[STATE_KEY_INITIALIZED]

    state[STATE_KEY_NOTIONAL] = 123.0
    init_state(state)
    assert state[STATE_KEY_NOTIONAL] == 123.0
    assert state[STATE_KEY_COMPUTE_FINGERPRINT] == first_fp


def test_compute_fingerprint_deterministic() -> None:
    s1 = {}
    s2 = {}
    init_state(s1)
    init_state(s2)
    assert compute_fingerprint_from_state(s1) == compute_fingerprint_from_state(s2)


def test_pipeline_cache_invalidates_on_input_change() -> None:
    state = {}
    init_state(state)

    outputs_a = ensure_pipeline_outputs(state)
    fp_a = state[STATE_KEY_COMPUTE_FINGERPRINT]

    outputs_b = ensure_pipeline_outputs(state)
    assert outputs_a is outputs_b
    assert state[STATE_KEY_COMPUTE_FINGERPRINT] == fp_a

    state[STATE_KEY_FRA_PAIR] = "6x9"
    outputs_c = ensure_pipeline_outputs(state)
    fp_c = state[STATE_KEY_COMPUTE_FINGERPRINT]

    assert fp_c != fp_a
    assert outputs_c["pricing"]["fra_pair"] == "6x9"


def test_run_app_returns_precomputed_page_payloads() -> None:
    payload = run_app({})
    assert {"valuation", "risk", "xccy"}.issubset(payload)
    assert "pv" in payload["valuation"]
    assert "scenario" in payload["risk"]
    assert "cip_mean_bp" in payload["xccy"]
