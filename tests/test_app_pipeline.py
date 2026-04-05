from __future__ import annotations

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
