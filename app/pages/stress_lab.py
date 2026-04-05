from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
from src.risk.hedging_optimizer import OptimizerConfig, optimize_hedges
from src.risk.scenarios.em_scenarios import em_scenario_library

TEMPLATE_FILES = [
    "capital_outflow_shock.json",
    "currency_devaluation_shock.json",
    "sovereign_downgrade_liquidity_shock.json",
]

TENORS = ["front", "belly", "back"]

BASE_VALUATION = {
    "rates_book_usd_mm": 42.0,
    "basis_book_usd_mm": 14.0,
    "fx_book_usd_mm": 9.0,
}

BASE_EXPOSURE_VECTOR = np.array([2.5, 1.8, 1.2, 1.0, 0.75, 0.5])
HEDGE_MATRIX = np.array(
    [
        [-0.90, -0.35, -0.15, -0.30, -0.20, -0.10],
        [-0.40, -0.95, -0.35, -0.15, -0.25, -0.15],
        [-0.15, -0.35, -0.90, -0.10, -0.20, -0.25],
        [-0.10, -0.25, -0.15, -0.85, -0.30, -0.15],
        [-0.05, -0.15, -0.25, -0.20, -0.85, -0.35],
        [-0.05, -0.10, -0.20, -0.15, -0.35, -0.85],
    ]
)
CARRY_VECTOR = np.array([0.20, 0.15, 0.10, 0.08, 0.06, 0.04])
LIQUIDITY_VECTOR = np.array([0.12, 0.11, 0.10, 0.08, 0.07, 0.06])
INSTRUMENTS = [
    "2Y IRS payer",
    "5Y IRS payer",
    "10Y IRS payer",
    "1Y FX forward",
    "3Y XCCY basis",
    "5Y XCCY basis",
]
TENOR_BUCKETS = ["front", "belly", "back", "front", "belly", "back"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_template(file_name: str) -> Dict[str, Any]:
    path = _repo_root() / "templates" / "scenarios" / file_name
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_scenarios() -> Dict[str, Dict[str, Any]]:
    scenario_map: Dict[str, Dict[str, Any]] = {}

    for file_name in TEMPLATE_FILES:
        payload = _read_template(file_name)
        scenario_map[payload["name"]] = payload

    for generated in em_scenario_library():
        scenario_map[generated.name] = {
            "name": generated.name,
            "description": generated.description,
            "rates_bp": dict(generated.rates_bp),
            "fx_pct": dict(generated.fx_pct),
            "basis_bp": dict(generated.basis_bp),
            "risk_off": dict(generated.risk_off),
        }

    return scenario_map


def _customized_scenario(base: Dict[str, Any], parallel_bp: float, slope_bp: float, basis_widen_bp: float) -> Dict[str, Any]:
    scenario = json.loads(json.dumps(base))
    scenario["name"] = f"{base['name']}_custom"

    for tenor in TENORS:
        scenario["rates_bp"][tenor] += parallel_bp
        scenario["basis_bp"][tenor] += basis_widen_bp

    scenario["rates_bp"]["front"] += slope_bp
    scenario["rates_bp"]["back"] -= slope_bp

    return scenario


def _bucket_avg(values: Dict[str, float], tenors: Iterable[str]) -> float:
    return float(np.mean([values[t] for t in tenors]))


def _stressed_valuation(base: Dict[str, float], scenario: Dict[str, Any]) -> Dict[str, float]:
    rates_move = _bucket_avg(scenario["rates_bp"], TENORS) / 100.0
    basis_move = _bucket_avg(scenario["basis_bp"], TENORS) / 100.0
    fx_move = scenario["fx_pct"]["spot"] / 100.0

    stressed = {
        "rates_book_usd_mm": base["rates_book_usd_mm"] - (0.60 * rates_move * base["rates_book_usd_mm"]),
        "basis_book_usd_mm": base["basis_book_usd_mm"] - (0.45 * basis_move * base["basis_book_usd_mm"]),
        "fx_book_usd_mm": base["fx_book_usd_mm"] - (0.50 * fx_move * base["fx_book_usd_mm"]),
    }
    stressed["total_usd_mm"] = sum(stressed.values())
    base_total = sum(base.values())
    stressed["delta_vs_base_usd_mm"] = stressed["total_usd_mm"] - base_total
    return stressed


def _scenario_exposure_vector(scenario: Dict[str, Any]) -> np.ndarray:
    rates = scenario["rates_bp"]
    basis = scenario["basis_bp"]
    fx = scenario["fx_pct"]
    return np.array(
        [
            rates["front"] / 100.0,
            rates["belly"] / 100.0,
            rates["back"] / 100.0,
            fx["spot"] / 100.0,
            basis["belly"] / 100.0,
            basis["back"] / 100.0,
        ]
    )


def _compute_hedge_effectiveness(exposure_vector: np.ndarray, hedge_solution: np.ndarray) -> Dict[str, float]:
    unhedged = exposure_vector
    hedged = exposure_vector + HEDGE_MATRIX @ hedge_solution
    unhedged_risk = float(unhedged.T @ unhedged)
    hedged_risk = float(hedged.T @ hedged)
    effectiveness = 0.0 if unhedged_risk < 1e-12 else 1.0 - hedged_risk / unhedged_risk
    return {
        "unhedged_risk": unhedged_risk,
        "hedged_risk": hedged_risk,
        "hedge_effectiveness": effectiveness,
    }


def render(controls: Dict[str, Any] | None = None) -> None:
    import streamlit as st

    st.subheader("Stress Lab")
    st.caption("Scenario stress + custom shocks + hedge what-if optimization")

    scenarios = _merge_scenarios()
    scenario_names = sorted(scenarios.keys())
    default_scenario_index = 0
    requested_scenario = controls.get("default_scenario")
    if isinstance(requested_scenario, str) and requested_scenario in scenario_names:
        default_scenario_index = scenario_names.index(requested_scenario)

    left, right = st.columns([1, 1])

    with left:
        selected_name = st.selectbox("Scenario template", scenario_names, index=default_scenario_index)
        base_scenario = scenarios[selected_name]
        st.write(base_scenario["description"])

        st.subheader("Custom shock builder")
        parallel_bp = st.slider("Parallel rates shift (bp)", min_value=-300, max_value=300, value=0, step=5)
        slope_bp = st.slider("Curve slope change (bp): +front / -back", min_value=-200, max_value=200, value=0, step=5)
        basis_widen_bp = st.slider("Basis widening (bp)", min_value=-200, max_value=300, value=0, step=5)

        shocked = _customized_scenario(base_scenario, parallel_bp, slope_bp, basis_widen_bp)

        with st.expander("Scenario detail", expanded=False):
            st.json(shocked)

    with right:
        st.subheader("Hedge optimization what-if")
        max_notional = st.number_input("Max notional", min_value=0.5, max_value=20.0, value=5.0, step=0.5)
        max_concentration = st.slider("Max tenor concentration", min_value=0.25, max_value=1.0, value=0.65, step=0.05)
        tx_cost = st.number_input("Transaction cost per unit", min_value=0.0, max_value=1.0, value=0.01, step=0.01)
        carry_penalty = st.slider("Carry penalty", min_value=0.0, max_value=1.0, value=0.25, step=0.05)
        liquidity_penalty = st.slider("Liquidity penalty", min_value=0.0, max_value=1.0, value=0.10, step=0.05)

        config = OptimizerConfig(
            max_notional=float(max_notional),
            max_tenor_concentration=float(max_concentration),
            transaction_cost_per_unit=float(tx_cost),
            carry_penalty=float(carry_penalty),
            liquidity_penalty=float(liquidity_penalty),
        )

        scenario_exposure = BASE_EXPOSURE_VECTOR + _scenario_exposure_vector(shocked)
        optimization = optimize_hedges(
            exposure_vector=scenario_exposure,
            hedge_matrix=HEDGE_MATRIX,
            carry_vector=CARRY_VECTOR,
            liquidity_vector=LIQUIDITY_VECTOR,
            instruments=INSTRUMENTS,
            tenor_bucket=TENOR_BUCKETS,
            config=config,
        )

        solution_df = optimization["solution"]
        hedge_solution = solution_df["optimal_notional"].to_numpy(dtype=float)
        effectiveness = _compute_hedge_effectiveness(scenario_exposure, hedge_solution)

    st.divider()
    stressed = _stressed_valuation(BASE_VALUATION, shocked)
    base_total = sum(BASE_VALUATION.values())

    valuation_df = pd.DataFrame(
        {
            "book": list(BASE_VALUATION.keys()),
            "base_usd_mm": list(BASE_VALUATION.values()),
            "stressed_usd_mm": [stressed["rates_book_usd_mm"], stressed["basis_book_usd_mm"], stressed["fx_book_usd_mm"]],
        }
    )
    valuation_df["delta_usd_mm"] = valuation_df["stressed_usd_mm"] - valuation_df["base_usd_mm"]

    st.subheader("1) Base vs stressed valuation table/metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Base total (USD mm)", f"{base_total:,.2f}")
    col2.metric("Stressed total (USD mm)", f"{stressed['total_usd_mm']:,.2f}", delta=f"{stressed['delta_vs_base_usd_mm']:,.2f}")
    col3.metric("Total delta vs base (USD mm)", f"{stressed['delta_vs_base_usd_mm']:,.2f}")
    st.dataframe(valuation_df, use_container_width=True)

    st.subheader("2) Hedge solution table")
    st.dataframe(solution_df, use_container_width=True)

    st.subheader("3) Hedge effectiveness metrics")
    stat_cols = st.columns(3)
    stat_cols[0].metric("Unhedged risk", f"{effectiveness['unhedged_risk']:.4f}")
    stat_cols[1].metric("Hedged risk", f"{effectiveness['hedged_risk']:.4f}")
    stat_cols[2].metric("Optimization objective", f"{optimization['total_objective']:.4f}")
    st.metric("Hedge effectiveness", f"{100.0 * effectiveness['hedge_effectiveness']:.1f}%")

    if controls.get("show_downloads", True):
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                "Download valuation table (CSV)",
                data=valuation_df.to_csv(index=False).encode("utf-8"),
                file_name="stress_lab_valuation.csv",
                mime="text/csv",
            )
        with dl_col2:
            st.download_button(
                "Download hedge solution (CSV)",
                data=solution_df.to_csv(index=False).encode("utf-8"),
                file_name="stress_lab_hedge_solution.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    render()
