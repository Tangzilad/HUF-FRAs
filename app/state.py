"""Canonical app-state schema and cache fingerprint helpers."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

# Core valuation/configuration inputs.
STATE_KEY_VALUATION_DATE = "valuation_date"
STATE_KEY_CURVE_SOURCE = "curve_source"
STATE_KEY_FRA_PAIR = "fra_pair"
STATE_KEY_NOTIONAL = "notional"
STATE_KEY_PAYER_RECEIVER = "payer_receiver"
STATE_KEY_DAY_COUNT = "day_count"
STATE_KEY_COMPOUNDING = "compounding"
STATE_KEY_MODEL_CHOICE = "model_choice"

# Scenario + stress and hedge settings.
STATE_KEY_SELECTED_SCENARIO = "selected_scenario"
STATE_KEY_CUSTOM_SHOCK_PARAMS = "custom_shock_params"
STATE_KEY_HEDGE_SETTINGS = "hedge_settings"
STATE_KEY_EXPLANATION_MODE = "explanation_mode"

# Uploaded/attached external handles.
STATE_KEY_UPLOADED_HANDLES = "uploaded_data_handles"

# Pipeline/caching support.
STATE_KEY_COMPUTE_FINGERPRINT = "compute_fingerprint"
STATE_KEY_PIPELINE_OUTPUTS = "pipeline_outputs"
STATE_KEY_INITIALIZED = "_initialized"

CANONICAL_INPUT_KEYS: tuple[str, ...] = (
    STATE_KEY_VALUATION_DATE,
    STATE_KEY_CURVE_SOURCE,
    STATE_KEY_FRA_PAIR,
    STATE_KEY_NOTIONAL,
    STATE_KEY_PAYER_RECEIVER,
    STATE_KEY_DAY_COUNT,
    STATE_KEY_COMPOUNDING,
    STATE_KEY_MODEL_CHOICE,
    STATE_KEY_SELECTED_SCENARIO,
    STATE_KEY_CUSTOM_SHOCK_PARAMS,
    STATE_KEY_HEDGE_SETTINGS,
    STATE_KEY_EXPLANATION_MODE,
    STATE_KEY_UPLOADED_HANDLES,
)


DEFAULT_STATE: Dict[str, Any] = {
    STATE_KEY_VALUATION_DATE: date.today().isoformat(),
    STATE_KEY_CURVE_SOURCE: "synthetic",
    STATE_KEY_FRA_PAIR: "3x6",
    STATE_KEY_NOTIONAL: 100_000_000.0,
    STATE_KEY_PAYER_RECEIVER: "payer",
    STATE_KEY_DAY_COUNT: "ACT/360",
    STATE_KEY_COMPOUNDING: "simple",
    STATE_KEY_MODEL_CHOICE: "hull_white_1f",
    STATE_KEY_SELECTED_SCENARIO: "capital_outflow_shock",
    STATE_KEY_CUSTOM_SHOCK_PARAMS: {"front_bp": 100.0, "back_bp": 50.0},
    STATE_KEY_HEDGE_SETTINGS: {
        "enabled": True,
        "target": "dv01",
        "max_notional": 5.0,
    },
    STATE_KEY_EXPLANATION_MODE: "desk",
    STATE_KEY_UPLOADED_HANDLES: {
        "curve_df": None,
        "options_df": None,
        "domestic_ois": None,
        "foreign_ois": None,
        "fx_forwards": None,
    },
    STATE_KEY_COMPUTE_FINGERPRINT: None,
    STATE_KEY_PIPELINE_OUTPUTS: {},
    STATE_KEY_INITIALIZED: False,
}


def init_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize app state exactly once."""

    if state.get(STATE_KEY_INITIALIZED):
        return state

    for key, value in DEFAULT_STATE.items():
        state.setdefault(key, value.copy() if isinstance(value, dict) else value)

    state[STATE_KEY_INITIALIZED] = True
    state[STATE_KEY_COMPUTE_FINGERPRINT] = compute_fingerprint_from_state(state)
    return state


def canonicalize_for_fingerprint(value: Any) -> Any:
    """Convert state values to deterministic JSON-serializable objects."""

    if isinstance(value, Mapping):
        return {str(k): canonicalize_for_fingerprint(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple, set)):
        return [canonicalize_for_fingerprint(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except TypeError:
            pass
    return value


def extract_compute_inputs(state: Mapping[str, Any], *, include_keys: Iterable[str] = CANONICAL_INPUT_KEYS) -> Dict[str, Any]:
    """Return the canonical subset of state used in compute cache keys."""

    return {k: canonicalize_for_fingerprint(state.get(k)) for k in include_keys}


def fingerprint_payload(payload: Mapping[str, Any]) -> str:
    """Hash a canonical payload in a deterministic way."""

    blob = json.dumps(canonicalize_for_fingerprint(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compute_fingerprint_from_state(state: Mapping[str, Any]) -> str:
    """Build the compute fingerprint from canonical state inputs."""

    return fingerprint_payload(extract_compute_inputs(state))
