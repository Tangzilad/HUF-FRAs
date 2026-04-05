from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
import streamlit as st

from app.calculation_windows import render_equation_window
from src.models.short_rate.fra import convexity_adjustment_summary
from src.risk.backtesting import scenario_plausibility_check
from src.risk.factor_models import PCAPreprocessConfig, pca_decompose, prepare_pca_inputs
from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import EMScenario, em_scenario_library
from src.risk.tail_risk import marginal_component_var_es


TENOR_TO_POINTS = {
    "front": [0.25, 0.50, 1.00],
    "belly": [2.0, 3.0, 5.0],
    "back": [7.0, 10.0, 15.0],
}


def _control_value(controls: Any, key: str) -> Any:
    if controls is None:
        return None
    if isinstance(controls, dict):
        return controls.get(key)
    return getattr(controls, key, None)


def _default_curve() -> pd.DataFrame:
    return pd.DataFrame(
        {"t": [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0], "zero_rate": [0.062, 0.064, 0.066, 0.067, 0.068, 0.069, 0.07, 0.071, 0.072]}
    )


def _resolve_scenario(raw: Any) -> EMScenario:
    scenarios = {s.name: s for s in em_scenario_library()}
    default = em_scenario_library()[0]
    if isinstance(raw, EMScenario):
        return raw
    if isinstance(raw, str) and raw in scenarios:
        return scenarios[raw]
    return default


def _resolve_selected_scenario(controls: Any) -> EMScenario:
    control_scenario = _control_value(controls, "scenario")
    if control_scenario is not None:
        return _resolve_scenario(control_scenario)
    return _resolve_scenario(st.session_state.get("selected_scenario"))


def _resolve_model_name(model: Any) -> str:
    if model is None:
        return "none"
    return getattr(model, "__class__", type(model)).__name__


def _resolve_selected_model(controls: Any) -> Any:
    control_model = _control_value(controls, "model")
    if control_model is None:
        return st.session_state.get("selected_short_rate_model")
    if isinstance(control_model, str) and control_model.lower() in {"static", "none"}:
        return None
    return st.session_state.get("selected_short_rate_model")


def _sample_portfolio() -> list[Trade]:
    return [
        Trade("fra_3x6", "FRA", 7_500_000, "front", dv01=-950.0, fx_delta=80_000.0, basis01=140.0, carry=1_800.0),
        Trade("swap_2y", "IRS", 12_000_000, "belly", dv01=-2_300.0, fx_delta=40_000.0, basis01=320.0, carry=2_100.0),
        Trade("xccy_5y", "XCCY Basis", 10_000_000, "back", dv01=-2_750.0, fx_delta=160_000.0, basis01=510.0, carry=2_400.0),
        Trade("fx_fwd", "FX Forward", 6_000_000, "front", dv01=-120.0, fx_delta=210_000.0, basis01=40.0, carry=700.0, hedge_overlay=True),
    ]


def _resolve_portfolio(raw: Any) -> list[Trade]:
    if raw is None:
        return _sample_portfolio()
    out: list[Trade] = []
    for item in raw:
        if isinstance(item, Trade):
            out.append(item)
            continue
        if isinstance(item, dict):
            out.append(
                Trade(
                    trade_id=str(item.get("trade_id", f"trade_{len(out)}")),
                    instrument=str(item.get("instrument", "unknown")),
                    notional=float(item.get("notional", 0.0)),
                    tenor_bucket=str(item.get("tenor_bucket", "front")),
                    dv01=float(item.get("dv01", 0.0)),
                    fx_delta=float(item.get("fx_delta", 0.0)),
                    basis01=float(item.get("basis01", 0.0)),
                    carry=float(item.get("carry", 0.0)),
                    hedge_overlay=bool(item.get("hedge_overlay", False)),
                )
            )
    return out or _sample_portfolio()


def _resolve_selected_portfolio() -> list[Trade]:
    return _resolve_portfolio(st.session_state.get("risk_portfolio"))


def _resolve_selected_curve() -> pd.DataFrame:
    curve = st.session_state.get("short_rate_curve")
    if isinstance(curve, pd.DataFrame) and not curve.empty:
        return curve
    return _default_curve()


def _bucket_roll_down(curve: pd.DataFrame, horizon_years: float = 1 / 12) -> pd.DataFrame:
    rows = []
    c = curve.sort_values("t")
    for bucket, points in TENOR_TO_POINTS.items():
        vals = []
        for t in points:
            r_t = np.interp(t, c["t"], c["zero_rate"])
            r_roll = np.interp(max(t - horizon_years, c["t"].min()), c["t"], c["zero_rate"])
            vals.append((r_roll - r_t) * 1e4)
        rows.append({"tenor_bucket": bucket, "roll_down_bp_1m": float(np.mean(vals))})
    return pd.DataFrame(rows)


def _model_bucket_adjustment(model: Any, curve: pd.DataFrame) -> pd.DataFrame:
    if model is None:
        return pd.DataFrame({"tenor_bucket": list(TENOR_TO_POINTS), "model_convexity_adj_bp": [0.0, 0.0, 0.0]})

    tenors = [(0.25, 0.50), (2.0, 3.0), (7.0, 10.0)]
    vols = [float(getattr(model, "sigma", 0.01))]
    summary = convexity_adjustment_summary(
        model=model,
        curve=curve,
        tenors=tenors,
        vol_regimes=vols,
        n_paths=2000,
        seed=7,
    )
    summary["tenor_bucket"] = ["front", "belly", "back"]
    return summary[["tenor_bucket", "convexity_adjustment"]].rename(
        columns={"convexity_adjustment": "model_convexity_adj_bp"}
    ).assign(model_convexity_adj_bp=lambda df: df["model_convexity_adj_bp"] * 1e4)


def _scenario_ladder(portfolio: Iterable[Trade], scenario: EMScenario, multipliers: list[float]) -> pd.DataFrame:
    rows = []
    for m in multipliers:
        scaled = EMScenario(
            name=f"{scenario.name}_x{m:.1f}",
            description=scenario.description,
            rates_bp={k: v * m for k, v in scenario.rates_bp.items()},
            fx_pct={k: v * m for k, v in scenario.fx_pct.items()},
            basis_bp={k: v * m for k, v in scenario.basis_bp.items()},
            risk_off={k: v * m for k, v in scenario.risk_off.items()},
        )
        pnl = propagate_scenario(portfolio, scaled)
        rows.append({"multiplier": m, "pnl_total": float(pnl["pnl_total"].sum())})
    return pd.DataFrame(rows)


def _build_pca_diagnostics() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    rates_hist = st.session_state.get("rate_factor_history")
    macro_hist = st.session_state.get("macro_history")
    if not isinstance(rates_hist, pd.DataFrame) or not isinstance(macro_hist, pd.DataFrame):
        return None, None

    matrix = prepare_pca_inputs(rates_hist, macro_hist, config=PCAPreprocessConfig(target_freq="W"))
    pca = pca_decompose(matrix, n_factors=3)
    loadings = pd.DataFrame(pca["factor_loadings"], columns=pca["columns"]).assign(factor=lambda df: [f"PC{i+1}" for i in range(len(df))])
    variance = pd.DataFrame({"factor": [f"PC{i+1}" for i in range(len(pca["explained_variance"]))], "explained_variance": pca["explained_variance"]})
    return loadings, variance


def render(controls: dict[str, Any] | None = None) -> None:
    controls = controls or {}
    st.subheader("Risk P&L")

    selected_scenario = _resolve_selected_scenario(controls)
    selected_model = _resolve_selected_model(controls)
    model_name = _resolve_model_name(selected_model)

    st.caption(f"Using scenario: `{selected_scenario.name}` and short-rate model: `{model_name}`.")

    portfolio = _resolve_selected_portfolio()
    curve = _resolve_selected_curve()

    model_adj = _model_bucket_adjustment(selected_model, curve)
    roll_down = _bucket_roll_down(curve)

    adj_map = dict(zip(model_adj["tenor_bucket"], model_adj["model_convexity_adj_bp"]))
    enriched: list[Trade] = []
    for tr in portfolio:
        adj_scale = 1.0 + 1e-4 * adj_map.get(tr.tenor_bucket, 0.0)
        enriched.append(Trade(**{**asdict(tr), "dv01": tr.dv01 * adj_scale}))

    pnl = propagate_scenario(enriched, selected_scenario)
    decomposition = decompose_pnl(pnl)
    dv01_table = pd.DataFrame([asdict(tr) for tr in enriched]).groupby("tenor_bucket", as_index=False)[["dv01"]].sum()
    dv01_table = dv01_table.merge(roll_down, on="tenor_bucket", how="left").merge(model_adj, on="tenor_bucket", how="left")

    factor_bucket = decomposition["factor_bucket"].merge(roll_down, on="tenor_bucket", how="left")
    factor_bucket["roll_down_pnl"] = -factor_bucket["pnl_rate"] * factor_bucket["roll_down_bp_1m"] / 1e4

    ladder = _scenario_ladder(enriched, selected_scenario, multipliers=[0.5, 1.0, 1.5, 2.0])

    st.subheader("DV01 by tenor bucket")
    st.dataframe(dv01_table, use_container_width=True)

    st.subheader("Scenario P&L decomposition")
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(decomposition["instrument"], use_container_width=True)
        st.bar_chart(decomposition["instrument"].set_index("instrument")[["pnl_rate", "pnl_fx", "pnl_basis", "carry"]])
    with c2:
        st.dataframe(factor_bucket, use_container_width=True)
        st.bar_chart(factor_bucket.set_index("tenor_bucket")[["pnl_total", "roll_down_pnl"]])

    st.subheader("Stress ladder")
    st.dataframe(ladder, use_container_width=True)
    st.line_chart(ladder.set_index("multiplier")["pnl_total"])

    st.subheader("Tail-risk decomposition")
    pnl_comp = factor_bucket[["pnl_rate", "pnl_fx", "pnl_basis", "roll_down_pnl"]].copy()
    pnl_comp["total"] = pnl_comp.sum(axis=1)
    tail = marginal_component_var_es(pnl_comp, total_col="total")
    st.dataframe(tail["decomposition"], use_container_width=True)
    st.metric("Portfolio VaR 99%", f"{tail['portfolio_var']:,.2f}")
    st.metric("Portfolio ES 99%", f"{tail['portfolio_es']:,.2f}")
    render_equation_window(
        title="How P&L, VaR, and ES are calculated",
        equations=[
            r"PnL_{\mathrm{trade}} = PnL_{\mathrm{rate}} + PnL_{\mathrm{fx}} + PnL_{\mathrm{basis}} + Carry",
            r"PnL_{\mathrm{portfolio}} = \sum_i PnL_{\mathrm{trade},i}",
            r"VaR_{99\%} = -Q_{1\%}(PnL),\quad ES_{99\%} = -\mathbb{E}[PnL \mid PnL \le Q_{1\%}]",
        ],
        notes=[
            f"Scenario = {selected_scenario.name}; portfolio trades = {len(enriched)}",
            f"Portfolio VaR 99% = {tail['portfolio_var']:,.4f}; ES 99% = {tail['portfolio_es']:,.4f}",
            "Trade-level sensitivities (DV01, FX delta, basis01, carry) feed each component above.",
        ],
    )

    st.subheader("Diagnostics")
    pca_loadings, pca_var = _build_pca_diagnostics()
    if pca_loadings is not None and pca_var is not None:
        st.caption("PCA built from `rate_factor_history` + `macro_history` in session state.")
        st.dataframe(pca_var, use_container_width=True)
        st.dataframe(pca_loadings, use_container_width=True)

    hist_shocks = st.session_state.get("historical_shocks")
    if isinstance(hist_shocks, pd.DataFrame):
        scenario_shocks = pd.DataFrame(
            {
                "rates_front": [selected_scenario.rates_bp.get("front", 0.0)],
                "rates_belly": [selected_scenario.rates_bp.get("belly", 0.0)],
                "rates_back": [selected_scenario.rates_bp.get("back", 0.0)],
                "fx_spot": [selected_scenario.fx_pct.get("spot", 0.0)],
                "basis_front": [selected_scenario.basis_bp.get("front", 0.0)],
            }
        )
        plausibility = scenario_plausibility_check(scenario_shocks, hist_shocks)
        st.dataframe(plausibility, use_container_width=True)

    export_tables: Dict[str, pd.DataFrame] = {
        "dv01_by_tenor": dv01_table,
        "pnl_by_instrument": decomposition["instrument"],
        "pnl_by_bucket": factor_bucket,
        "stress_ladder": ladder,
        "tail_decomposition": tail["decomposition"],
    }
    st.session_state["risk_pnl_export_tables"] = export_tables

    st.subheader("Download-ready tabular objects")
    st.write("The following tables are available in `st.session_state['risk_pnl_export_tables']` for export workflow:")
    st.json({name: list(df.columns) for name, df in export_tables.items()})
    if hasattr(st, "download_button"):
        for table_name in ["dv01_by_tenor", "pnl_by_instrument", "stress_ladder", "tail_decomposition"]:
            table = export_tables[table_name]
            st.download_button(
                label=f"Download {table_name}.csv",
                data=table.to_csv(index=False).encode("utf-8"),
                file_name=f"{table_name}.csv",
                mime="text/csv",
            )


def main() -> None:
    render({})


if __name__ == "__main__":
    render()
