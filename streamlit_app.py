from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from typing import Any

import pandas as pd
import streamlit as st

from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import EMScenario, em_scenario_library


REQUIRED_PORTFOLIO_COLUMNS = [
    "trade_id",
    "instrument",
    "notional",
    "tenor_bucket",
    "dv01",
    "fx_delta",
    "basis01",
    "carry",
    "hedge_overlay",
]


DEFAULT_PORTFOLIO = pd.DataFrame(
    [
        {
            "trade_id": "T1",
            "instrument": "FRA",
            "notional": 12_000_000,
            "tenor_bucket": "front",
            "dv01": -2800.0,
            "fx_delta": 0.0,
            "basis01": 0.0,
            "carry": 1800.0,
            "hedge_overlay": False,
        },
        {
            "trade_id": "T2",
            "instrument": "Swap",
            "notional": 18_000_000,
            "tenor_bucket": "belly",
            "dv01": -4600.0,
            "fx_delta": 0.0,
            "basis01": 0.0,
            "carry": 3200.0,
            "hedge_overlay": False,
        },
        {
            "trade_id": "T3",
            "instrument": "XCCY_BasisSwap",
            "notional": 9_000_000,
            "tenor_bucket": "back",
            "dv01": -900.0,
            "fx_delta": 0.0,
            "basis01": -2000.0,
            "carry": 850.0,
            "hedge_overlay": True,
        },
        {
            "trade_id": "T4",
            "instrument": "FX_Forward",
            "notional": 7_000_000,
            "tenor_bucket": "front",
            "dv01": 0.0,
            "fx_delta": -3_200_000.0,
            "basis01": 0.0,
            "carry": 300.0,
            "hedge_overlay": True,
        },
    ]
)


def _to_portfolio_trades(df: pd.DataFrame) -> list[Trade]:
    casted = df.copy(deep=True)
    casted["hedge_overlay"] = casted["hedge_overlay"].astype(str).str.lower().isin({"true", "1", "yes"})
    for col in ["notional", "dv01", "fx_delta", "basis01", "carry"]:
        casted[col] = pd.to_numeric(casted[col], errors="coerce").fillna(0.0)

    return [
        Trade(
            trade_id=str(row["trade_id"]),
            instrument=str(row["instrument"]),
            notional=float(row["notional"]),
            tenor_bucket=str(row["tenor_bucket"]),
            dv01=float(row["dv01"]),
            fx_delta=float(row["fx_delta"]),
            basis01=float(row["basis01"]),
            carry=float(row["carry"]),
            hedge_overlay=bool(row["hedge_overlay"]),
        )
        for _, row in casted.iterrows()
    ]


def _normalize_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy(deep=True)
    normalized = normalized.reindex(columns=REQUIRED_PORTFOLIO_COLUMNS)
    for text_col in ["trade_id", "instrument", "tenor_bucket", "hedge_overlay"]:
        normalized[text_col] = normalized[text_col].astype(str).str.strip()

    for col in ["notional", "dv01", "fx_delta", "basis01", "carry"]:
        normalized[col] = pd.to_numeric(normalized[col], errors="coerce").fillna(0.0).round(8)

    normalized = normalized.sort_values(["trade_id", "instrument", "tenor_bucket"], kind="mergesort")
    normalized = normalized.reset_index(drop=True)
    return normalized


def _scenario_map() -> dict[str, EMScenario]:
    return {scenario.name: scenario for scenario in em_scenario_library()}


@st.cache_resource(show_spinner=False)
def cached_scenario_map() -> dict[str, dict[str, Any]]:
    # Return serialized dicts only to avoid mutable object leakage from cache.
    return {name: asdict(scn) for name, scn in _scenario_map().items()}


def _normalize_user_inputs(selected_scenario: str, include_overlay: bool) -> str:
    normalized_payload = {
        "selected_scenario": selected_scenario.strip().lower(),
        "include_overlay": bool(include_overlay),
    }
    payload = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _fingerprint_uploaded_data(uploaded_bytes: bytes | None, normalized_portfolio: pd.DataFrame) -> str:
    hasher = sha256()
    hasher.update(normalized_portfolio.to_csv(index=False).encode("utf-8"))
    if uploaded_bytes:
        hasher.update(uploaded_bytes)
    return hasher.hexdigest()


@st.cache_data(show_spinner=False)
def compute_results_cached(
    portfolio_json: str,
    scenario_name: str,
    include_overlay: bool,
    input_key: str,
    data_fingerprint: str,
) -> dict[str, str]:
    _ = (input_key, data_fingerprint)  # explicit cache-key dependencies

    scenario_library = cached_scenario_map()
    selected = EMScenario(**scenario_library[scenario_name])

    portfolio_df = pd.read_json(BytesIO(portfolio_json.encode("utf-8")), orient="records")
    trades = _to_portfolio_trades(portfolio_df)

    scenario_df = propagate_scenario(trades, selected)
    if not include_overlay:
        scenario_df = scenario_df.loc[~scenario_df["hedge_overlay"]].copy(deep=True)

    decomposition = decompose_pnl(scenario_df)
    risk_table = decomposition["instrument"].copy(deep=True)

    # Serialize DataFrames to JSON strings so each rerun gets fresh mutable objects.
    return {
        "scenario_results": scenario_df.to_json(orient="records", date_format="iso"),
        "pnl_decomposition": decomposition["factor_bucket"].to_json(orient="records", date_format="iso"),
        "risk_table": risk_table.to_json(orient="records", date_format="iso"),
    }


def _to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


def _render_downloads(df: pd.DataFrame, label_prefix: str, filename_stem: str) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"Download {label_prefix} (CSV)",
        data=csv_bytes,
        file_name=f"{filename_stem}.csv",
        mime="text/csv",
        key=f"{filename_stem}_csv",
    )
    st.download_button(
        f"Download {label_prefix} (Excel)",
        data=_to_excel_bytes(df, label_prefix.replace(" ", "_")),
        file_name=f"{filename_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{filename_stem}_xlsx",
    )


def main() -> None:
    st.set_page_config(page_title="HUF FRA Risk Workbench", layout="wide")
    st.title("HUF FRA Risk Workbench")
    st.caption("Scenario analysis with cache-safe computations and table exports.")

    with st.sidebar:
        st.header("Scenario Controls")
        scenario_library = cached_scenario_map()
        scenario_name = st.selectbox("Scenario", sorted(scenario_library.keys()))
        include_overlay = st.toggle("Include hedge overlays", value=True)

        refresh_requested = st.button("Clear cache / refresh", type="secondary")
        if refresh_requested:
            st.cache_data.clear()
            st.cache_resource.clear()
            st.toast("All Streamlit caches cleared.")
            st.rerun()

    st.subheader("Portfolio input")
    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])
    if uploaded is not None:
        uploaded_bytes = uploaded.getvalue()
        portfolio = pd.read_csv(BytesIO(uploaded_bytes))
    else:
        uploaded_bytes = None
        portfolio = DEFAULT_PORTFOLIO.copy(deep=True)

    missing = sorted(set(REQUIRED_PORTFOLIO_COLUMNS) - set(portfolio.columns))
    if missing:
        st.error(f"Uploaded portfolio is missing required columns: {missing}")
        st.stop()

    normalized_portfolio = _normalize_portfolio(portfolio)
    st.dataframe(normalized_portfolio, use_container_width=True)

    normalized_user_input_key = _normalize_user_inputs(scenario_name, include_overlay)
    data_fingerprint = _fingerprint_uploaded_data(uploaded_bytes, normalized_portfolio)
    portfolio_json = normalized_portfolio.to_json(orient="records", date_format="iso")

    cached_results = compute_results_cached(
        portfolio_json=portfolio_json,
        scenario_name=scenario_name,
        include_overlay=include_overlay,
        input_key=normalized_user_input_key,
        data_fingerprint=data_fingerprint,
    )

    scenario_results = pd.read_json(BytesIO(cached_results["scenario_results"].encode("utf-8")), orient="records")
    pnl_decomposition = pd.read_json(BytesIO(cached_results["pnl_decomposition"].encode("utf-8")), orient="records")
    risk_table = pd.read_json(BytesIO(cached_results["risk_table"].encode("utf-8")), orient="records")

    tab_risk, tab_pnl, tab_scenario = st.tabs(["Risk tables", "P&L decomposition", "Scenario results"])

    with tab_risk:
        st.dataframe(risk_table, use_container_width=True)
        _render_downloads(risk_table, "Risk Table", "risk_table")

    with tab_pnl:
        st.dataframe(pnl_decomposition, use_container_width=True)
        _render_downloads(pnl_decomposition, "P&L Decomposition", "pnl_decomposition")

    with tab_scenario:
        st.dataframe(scenario_results, use_container_width=True)
        _render_downloads(scenario_results, "Scenario Results", "scenario_results")


if __name__ == "__main__":
    main()
