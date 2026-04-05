from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping

import pandas as pd

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional dependency in tests
    st = None

FRA_CHOICES = ["1x3", "1x6", "2x5", "2x8", "3x6", "3x9", "6x9", "6x12", "9x12"]
FRA_TENOR_TO_YEARS: dict[str, tuple[float, float]] = {
    label: (int(label.split("x")[0]) / 12.0, int(label.split("x")[1]) / 12.0) for label in FRA_CHOICES
}

DAY_COUNT_MAP = {"ACT/360": "act_360", "ACT/365F": "act_365f", "30/360": "30_360"}
COMPOUNDING_MAP = {"Simple": "simple", "Annual": "annual", "Continuous": "continuous"}
MODEL_MAP = {"Static": "static", "Ho-Lee": "ho_lee", "Hull-White": "hull_white"}
SCENARIO_PRELOAD_MAP = {
    "Capital Outflow Shock": "capital_outflow_shock",
    "Currency Devaluation Shock": "currency_devaluation_shock",
    "Sovereign Downgrade + Liquidity Shock": "sovereign_downgrade_liquidity_shock",
    "Custom Parallel": "custom_parallel",
    "Custom Steepener": "custom_steepener",
    "Custom Flattener": "custom_flattener",
}
HEDGE_MAP = {"USD FRA": "FRA", "XCCY Basis Swap": "XCCY_BasisSwap"}
EXPLANATION_MODE_MAP = {"Basic": "basic", "Learning": "learning"}
PAGES = ["CIP basis", "Cross-currency", "Short-rate FRA"]


@dataclass
class SidebarControls:
    valuation_date: date
    curve_source: str
    fra_labels: list[str]
    fra_tenors_years: list[tuple[float, float]]
    notional: float
    direction: str
    day_count: str
    compounding: str
    model: str
    scenario: str
    custom_shocks_bp: dict[str, float]
    hedge_instruments: list[str]
    explanation_mode: str
    active_page: str = "CIP basis"
    uploaded_curve: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)

    def to_updates(self) -> dict[str, Any]:
        return {
            "active_page": self.active_page,
            "tenor_years": self.fra_tenors_years[0][1] if self.fra_tenors_years else 1.0,
            "spot": 365.0,
            "forward_points": 2.5,
            "domestic_ois": 0.065,
            "foreign_ois": 0.045,
            "show_details": True,
        }


def _warn(msg: str, warnings: list[str]) -> None:
    warnings.append(msg)
    if st is not None:
        st.warning(msg)


def _validate_uploaded_curve(uploaded_curve: pd.DataFrame | None, warnings: list[str]) -> pd.DataFrame | None:
    if uploaded_curve is None:
        return None
    required = {"t", "zero_rate"}
    missing = required.difference(uploaded_curve.columns)
    if missing:
        _warn(f"Uploaded curve is missing required fields: {', '.join(sorted(missing))}. Expected columns: t, zero_rate.", warnings)
        return None

    curve = uploaded_curve.copy()
    curve["t"] = pd.to_numeric(curve["t"], errors="coerce")
    curve["zero_rate"] = pd.to_numeric(curve["zero_rate"], errors="coerce")
    curve = curve.dropna(subset=["t", "zero_rate"])
    curve = curve[curve["t"] > 0]
    return None if curve.empty else curve.sort_values("t").reset_index(drop=True)


def _normalize_fra_labels(labels: list[str], warnings: list[str]) -> tuple[list[str], list[tuple[float, float]]]:
    if not labels:
        _warn("No FRA tenors selected; defaulted to ['3x6'] for valuation.", warnings)
        labels = ["3x6"]

    normalized = [label for label in labels if label in FRA_TENOR_TO_YEARS]
    if not normalized:
        _warn("No valid FRA labels remained; defaulted to ['3x6'].", warnings)
        normalized = ["3x6"]
    return normalized, [FRA_TENOR_TO_YEARS[label] for label in normalized]


def render_sidebar_controls(defaults: Mapping[str, Any] | None = None, uploaded_curve: pd.DataFrame | None = None) -> SidebarControls:
    """Render sidebar controls if Streamlit is available, else normalize defaults for tests."""

    defaults = dict(defaults or {})
    warnings: list[str] = []

    if st is not None and not defaults:
        with st.sidebar:
            active_page = st.radio("Page", options=PAGES, index=0)
            valuation_date = st.date_input("Valuation date", value=date.today())
            curve_source_display = st.radio("Curve source", options=["Synthetic", "Upload"], index=0)
            fra_labels = st.multiselect("FRA tenors", options=FRA_CHOICES, default=["3x6"])
            notional = float(st.number_input("Notional", min_value=0.0, value=1_000_000.0, step=100_000.0))
            direction_display = st.radio("Direction", options=["Payer", "Receiver"], index=0)
            day_count_display = st.selectbox("Day-count", options=list(DAY_COUNT_MAP), index=0)
            comp_display = st.selectbox("Compounding", options=list(COMPOUNDING_MAP), index=0)
            model_display = st.selectbox("Model", options=list(MODEL_MAP), index=0)
            scenario_display = st.selectbox("Shock / scenario", options=list(SCENARIO_PRELOAD_MAP), index=0)
            hedge_display = st.multiselect("Hedge instruments", options=list(HEDGE_MAP), default=["USD FRA"])
            explain_display = st.radio("Explanation mode", options=list(EXPLANATION_MODE_MAP), index=0)
            custom_shocks_bp = {"front": 0.0, "belly": 0.0, "back": 0.0}
    else:
        active_page = str(defaults.get("active_page", "CIP basis"))
        valuation_date = defaults.get("valuation_date", date.today())
        curve_source_display = defaults.get("curve_source", "Synthetic")
        fra_labels = defaults.get("fra_labels", ["3x6"])
        notional = float(defaults.get("notional", 1_000_000.0))
        direction_display = defaults.get("direction", "Payer")
        day_count_display = defaults.get("day_count", "ACT/360")
        comp_display = defaults.get("compounding", "Simple")
        model_display = defaults.get("model", "Static")
        scenario_display = defaults.get("scenario", "Capital Outflow Shock")
        hedge_display = defaults.get("hedge_instruments", ["USD FRA"])
        explain_display = defaults.get("explanation_mode", "Basic")
        custom_shocks_bp = {
            "front": float(defaults.get("custom_front", 0.0)),
            "belly": float(defaults.get("custom_belly", 0.0)),
            "back": float(defaults.get("custom_back", 0.0)),
        }

    if notional <= 0:
        _warn("Notional must be positive; defaulted to 1,000,000.", warnings)
        notional = 1_000_000.0

    fra_labels_norm, fra_tenors_years = _normalize_fra_labels(list(fra_labels), warnings)
    curve_source = "uploaded" if str(curve_source_display).lower().startswith("upload") else "synthetic"
    direction = "receiver" if str(direction_display).lower().startswith("receiver") else "payer"
    day_count = DAY_COUNT_MAP.get(str(day_count_display), "act_360")
    compounding = COMPOUNDING_MAP.get(str(comp_display), "simple")
    model = MODEL_MAP.get(str(model_display), "static")
    scenario = SCENARIO_PRELOAD_MAP.get(str(scenario_display), "capital_outflow_shock")
    hedge_instruments = [HEDGE_MAP[h] for h in hedge_display if h in HEDGE_MAP]
    explanation_mode = EXPLANATION_MODE_MAP.get(str(explain_display), "basic")

    if not hedge_instruments:
        _warn("No hedge instruments selected; defaulted to USD FRA.", warnings)
        hedge_instruments = ["FRA"]

    validated_upload = _validate_uploaded_curve(uploaded_curve, warnings) if curve_source == "uploaded" else None
    if curve_source == "uploaded" and validated_upload is None:
        _warn("Uploaded curve is invalid or missing; curve source reverted to synthetic.", warnings)
        curve_source = "synthetic"

    return SidebarControls(
        valuation_date=valuation_date,
        curve_source=curve_source,
        fra_labels=fra_labels_norm,
        fra_tenors_years=fra_tenors_years,
        notional=notional,
        direction=direction,
        day_count=day_count,
        compounding=compounding,
        model=model,
        scenario=scenario,
        custom_shocks_bp=custom_shocks_bp,
        hedge_instruments=hedge_instruments,
        explanation_mode=explanation_mode,
        active_page=active_page,
        uploaded_curve=validated_upload,
        warnings=warnings,
    )
