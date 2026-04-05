"""App-level compute pipeline.

Each stage is pure-ish and keyed by state fingerprint so UI pages can consume the
same precomputed payloads rather than recomputing ad hoc.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

import numpy as np
import pandas as pd

from app.state import (
    STATE_KEY_COMPOUNDING,
    STATE_KEY_COMPUTE_FINGERPRINT,
    STATE_KEY_CUSTOM_SHOCK_PARAMS,
    STATE_KEY_DAY_COUNT,
    STATE_KEY_FRA_PAIR,
    STATE_KEY_MODEL_CHOICE,
    STATE_KEY_NOTIONAL,
    STATE_KEY_PAYER_RECEIVER,
    STATE_KEY_PIPELINE_OUTPUTS,
    STATE_KEY_SELECTED_SCENARIO,
    STATE_KEY_UPLOADED_HANDLES,
    compute_fingerprint_from_state,
)
from fra_simulation import generate_base_curves
from src.analytics import compute_raw_cip_deviation
from src.models import HoLeeModel, HullWhite1FModel
from src.risk.hedging_optimizer import OptimizerConfig, optimize_hedges
from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import em_scenario_library


def _parse_fra_pair(fra_pair: str) -> tuple[int, int]:
    left, right = fra_pair.lower().split("x")
    return int(left), int(right)


def load_or_assemble_curves(state: Mapping[str, Any]) -> Dict[str, Any]:
    handles = state.get(STATE_KEY_UPLOADED_HANDLES, {})
    uploaded = handles.get("curve_df") if isinstance(handles, Mapping) else None

    if isinstance(uploaded, pd.DataFrame) and {"month", "t", "huf_df", "huf_zero"}.issubset(uploaded.columns):
        curve_df = uploaded.copy()
        source = "uploaded"
    else:
        curve_df = generate_base_curves()
        source = "synthetic"

    curve = pd.DataFrame({"t": curve_df["t"], "zero_rate": curve_df["huf_zero"]})

    dom_ois = handles.get("domestic_ois") if isinstance(handles.get("domestic_ois"), pd.Series) else pd.Series(curve_df["huf_zero"].to_numpy(), index=curve_df["t"].to_numpy())
    for_ois = handles.get("foreign_ois") if isinstance(handles.get("foreign_ois"), pd.Series) else pd.Series(curve_df["usd_zero"].to_numpy(), index=curve_df["t"].to_numpy())
    fx_forwards = handles.get("fx_forwards") if isinstance(handles.get("fx_forwards"), pd.Series) else pd.Series(np.ones(len(curve_df)) * 360.0, index=curve_df["t"].to_numpy())

    return {
        "curve_source_used": source,
        "curve_df": curve_df,
        "short_rate_curve": curve,
        "domestic_ois": dom_ois,
        "foreign_ois": for_ois,
        "fx_forwards": fx_forwards,
    }


def calibrate_selected_model(state: Mapping[str, Any], curves_payload: Mapping[str, Any]) -> Dict[str, Any]:
    model_choice = str(state.get(STATE_KEY_MODEL_CHOICE, "hull_white_1f")).lower()
    curve = curves_payload["short_rate_curve"]
    options_df = state.get(STATE_KEY_UPLOADED_HANDLES, {}).get("options_df")

    if model_choice in {"ho_lee", "holee"}:
        model = HoLeeModel()
    else:
        model = HullWhite1FModel()

    model.fit_initial_curve(curve)

    calibration_result: Dict[str, Any]
    if isinstance(options_df, pd.DataFrame) and {"expiry", "normal_vol"}.issubset(options_df.columns):
        calibration_result = model.calibrate_to_options(options_df)
    else:
        calibration_result = {"skipped": True, "reason": "No uploaded options surface with [expiry, normal_vol]."}

    return {
        "model_choice": model_choice,
        "model": model,
        "calibration": calibration_result,
    }


def price_fra(state: Mapping[str, Any], curves_payload: Mapping[str, Any]) -> Dict[str, Any]:
    fra_pair = str(state.get(STATE_KEY_FRA_PAIR, "3x6"))
    start_m, end_m = _parse_fra_pair(fra_pair)
    notional = float(state.get(STATE_KEY_NOTIONAL, 100_000_000.0))
    payer_receiver = str(state.get(STATE_KEY_PAYER_RECEIVER, "payer")).lower()

    curve_df = curves_payload["curve_df"]
    row1 = curve_df.loc[curve_df["month"] == start_m].iloc[0]
    row2 = curve_df.loc[curve_df["month"] == end_m].iloc[0]

    tau = float(end_m - start_m) / 12.0
    p1, p2 = float(row1["huf_df"]), float(row2["huf_df"])
    fwd = (p1 / p2 - 1.0) / tau
    strike = fwd

    sign = 1.0 if payer_receiver == "payer" else -1.0
    pv = sign * notional * tau * (fwd - strike) * p2

    return {
        "fra_pair": fra_pair,
        "start_month": start_m,
        "end_month": end_m,
        "tau": tau,
        "forward_rate": fwd,
        "strike": strike,
        "discount_t2": p2,
        "pv": pv,
        "conventions": {
            "day_count": state.get(STATE_KEY_DAY_COUNT),
            "compounding": state.get(STATE_KEY_COMPOUNDING),
        },
    }


def compute_risk_and_pnl(state: Mapping[str, Any], priced_fra: Mapping[str, Any]) -> Dict[str, Any]:
    scn_name = state.get(STATE_KEY_SELECTED_SCENARIO)
    scenarios = {s.name: s for s in em_scenario_library()}
    scenario = scenarios.get(str(scn_name)) or next(iter(scenarios.values()))

    custom = state.get(STATE_KEY_CUSTOM_SHOCK_PARAMS, {})
    if isinstance(custom, Mapping):
        scenario = type(scenario)(
            name=scenario.name,
            description=scenario.description,
            rates_bp={
                "front": float(custom.get("front_bp", scenario.rates_bp["front"])),
                "belly": scenario.rates_bp["belly"],
                "back": float(custom.get("back_bp", scenario.rates_bp["back"])),
            },
            fx_pct=scenario.fx_pct,
            basis_bp=scenario.basis_bp,
            risk_off=scenario.risk_off,
        )

    fra_trade = Trade(
        trade_id="FRA-1",
        instrument="FRA",
        notional=float(state.get(STATE_KEY_NOTIONAL, 100_000_000.0)),
        tenor_bucket="front" if priced_fra["start_month"] <= 3 else "belly",
        dv01=-2500.0,
    )

    pnl_df = propagate_scenario([fra_trade], scenario)
    decomposition = decompose_pnl(pnl_df)

    hedge_out = optimize_hedges(
        exposure_vector=np.array([pnl_df["pnl_rate"].sum(), pnl_df["pnl_basis"].sum(), pnl_df["pnl_fx"].sum()]),
        hedge_matrix=np.eye(3),
        carry_vector=np.array([0.2, 0.1, 0.05]),
        liquidity_vector=np.array([1.0, 0.8, 0.3]),
        instruments=["FRA_3x6", "XCCY_Basis", "FX_Fwd"],
        tenor_bucket=["front", "belly", "front"],
        config=OptimizerConfig(),
    )

    return {
        "scenario_used": asdict(scenario),
        "pnl": pnl_df,
        "pnl_decomposition": decomposition,
        "hedge": hedge_out,
    }


def compute_xccy_cip_analytics(curves_payload: Mapping[str, Any]) -> Dict[str, Any]:
    tenor_index = curves_payload["domestic_ois"].index.to_numpy(dtype=float)
    as_of = pd.to_datetime(["2026-01-01"])

    spot = pd.Series([360.0], index=as_of)
    forwards = pd.DataFrame([curves_payload["fx_forwards"].to_numpy(dtype=float)], index=as_of, columns=tenor_index)
    dom_ois = pd.DataFrame([curves_payload["domestic_ois"].to_numpy(dtype=float)], index=as_of, columns=tenor_index)
    for_ois = pd.DataFrame([curves_payload["foreign_ois"].to_numpy(dtype=float)], index=as_of, columns=tenor_index)
    raw = compute_raw_cip_deviation(spot, forwards, dom_ois, for_ois)
    raw_basis = raw["raw_basis_bp"]
    return {
        "cip_raw_deviation": raw,
        "cip_summary_bp": float(raw_basis.mean().mean()),
    }


def run_compute_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    curves = load_or_assemble_curves(state)
    model = calibrate_selected_model(state, curves)
    priced = price_fra(state, curves)
    risk = compute_risk_and_pnl(state, priced)
    xccy = compute_xccy_cip_analytics(curves)
    return {
        "curves": curves,
        "model": model,
        "pricing": priced,
        "risk": risk,
        "xccy": xccy,
    }


def ensure_pipeline_outputs(state: Dict[str, Any]) -> Dict[str, Any]:
    new_fp = compute_fingerprint_from_state(state)
    cached_fp = state.get(STATE_KEY_COMPUTE_FINGERPRINT)
    cached_outputs = state.get(STATE_KEY_PIPELINE_OUTPUTS, {})
    if cached_fp != new_fp or not cached_outputs:
        state[STATE_KEY_PIPELINE_OUTPUTS] = run_compute_pipeline(state)
        state[STATE_KEY_COMPUTE_FINGERPRINT] = new_fp
    return state[STATE_KEY_PIPELINE_OUTPUTS]
