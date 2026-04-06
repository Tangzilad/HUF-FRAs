from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, Callable, Dict, Iterable

import numpy as np
import pandas as pd

from app.state import (
    STATE_KEY_COMPUTE_FINGERPRINT,
    STATE_KEY_FRA_PAIR,
    STATE_KEY_NOTIONAL,
    STATE_KEY_PIPELINE_OUTPUTS,
    compute_fingerprint_from_state,
)
from src.analytics.cip_premium import compute_raw_cip_deviation
from src.curves.cross_currency import build_discount_curve
from src.data.loaders.core import MarketQuote, QuoteCollection, QuoteValidationError, validate_quotes
from src.data.loaders.market_loaders import load_bond_yields
from src.explainers.cip import CIPExplainer
from src.explainers.cross_currency import CrossCurrencyExplainer
from src.explainers.curve_fit import CurveFitExplainer
from src.explainers.policy_narrative import PolicyNarrativeExplainer
from src.explainers.risk import RiskExplainer
from src.explainers.risk_scenario import RiskScenarioExplainer
from src.explainers.short_rate import ShortRateExplainer
from src.models.short_rate.fra import simulate_fra_distribution
from src.models.short_rate.ho_lee import HoLeeModel
from src.risk.portfolio_shocks import Trade, decompose_pnl, propagate_scenario
from src.risk.scenarios.em_scenarios import em_scenario_library


# ---------- UI helper utilities ----------

def format_bp(value_bp: float) -> str:
    return f"{value_bp:+.2f} bp"


def validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def to_panel_dataframe(
    *,
    spot: float,
    forward: float,
    domestic_ois: float,
    foreign_ois: float,
    tenor_years: Iterable[float],
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tenors = [float(t) for t in tenor_years]
    index = pd.DatetimeIndex([pd.Timestamp.utcnow().normalize()])
    spot_series = pd.Series([float(spot)], index=index)
    forward_df = pd.DataFrame({t: [float(forward)] for t in tenors}, index=index)
    domestic_df = pd.DataFrame({t: [float(domestic_ois)] for t in tenors}, index=index)
    foreign_df = pd.DataFrame({t: [float(foreign_ois)] for t in tenors}, index=index)
    return spot_series, forward_df, domestic_df, foreign_df


# ---------- Pipeline engines ----------

def build_curve_table(payload: Dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for ccy, quote_map in payload["ois_by_ccy"].items():
        discount_curve = build_discount_curve(quote_map)
        for tenor, df in sorted(discount_curve.items()):
            rows.append({"currency": ccy, "tenor_years": float(tenor), "discount_factor": float(df)})
    return pd.DataFrame(rows)


def run_pricing_engine(payload: Dict[str, Any], seed: int = 7) -> pd.DataFrame:
    curve = pd.DataFrame(payload["short_rate_curve"])
    out = simulate_fra_distribution(HoLeeModel(sigma=0.01), curve, start=0.5, end=1.0, n_paths=400, seed=seed)
    return pd.DataFrame(
        [
            {
                "n_paths": int(out.pnl.size),
                "fra_pnl_mean": float(np.mean(out.pnl)),
                "fra_pnl_std": float(np.std(out.pnl)),
                "fra_forward_mean": float(np.mean(out.fra_forward)),
                "futures_rate_mean": float(np.mean(out.futures_rate)),
            }
        ]
    )


def run_risk_engine(payload: Dict[str, Any]) -> dict[str, pd.DataFrame]:
    scenario = em_scenario_library()[0]
    portfolio = [Trade(**row) for row in payload["portfolio"]]
    pnl = propagate_scenario(portfolio, scenario)
    parts = decompose_pnl(pnl)
    return {"trade_pnl": pnl, **parts}


def run_cip_path(payload: Dict[str, Any]) -> pd.DataFrame:
    cip = payload["cip"]
    index = pd.to_datetime(cip["dates"])
    tenors = [float(x) for x in cip["tenors"]]

    spot = pd.Series(cip["spot"], index=index)
    domestic_ois = pd.DataFrame(cip["domestic_ois"], index=index, columns=tenors)
    foreign_ois = pd.DataFrame(cip["foreign_ois"], index=index, columns=tenors)

    forwards = pd.DataFrame(index=index, columns=tenors, dtype=float)
    for t in tenors:
        forwards[t] = spot * (1 + domestic_ois[t] * t) / (1 + foreign_ois[t] * t)

    raw = compute_raw_cip_deviation(spot, forwards, domestic_ois, foreign_ois)
    return raw["raw_basis_bp"].reset_index(names="date").melt(id_vars="date", var_name="tenor_years", value_name="raw_basis_bp")


def ensure_pipeline_outputs(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Memoize top-level app outputs and invalidate when fingerprint changes."""

    fp = compute_fingerprint_from_state(state)
    if state.get(STATE_KEY_COMPUTE_FINGERPRINT) == fp and STATE_KEY_PIPELINE_OUTPUTS in state:
        return state[STATE_KEY_PIPELINE_OUTPUTS]

    outputs = {
        "valuation": {"pv": 0.0, "fra_pair": state.get(STATE_KEY_FRA_PAIR, "3x6"), "notional": state.get(STATE_KEY_NOTIONAL, 1_000_000.0)},
        "risk": {"scenario": "base"},
        "xccy": {"cip_mean_bp": 0.0},
        "pricing": {"fra_pair": state.get(STATE_KEY_FRA_PAIR, "3x6")},
    }
    state[STATE_KEY_PIPELINE_OUTPUTS] = outputs
    state[STATE_KEY_COMPUTE_FINGERPRINT] = fp
    return outputs


# ---------- Explainer helpers ----------

@dataclass(frozen=True)
class ExplainerPanel:
    title: str
    help_text: str | None
    why_this_matters: str | None
    markdown: str


CORE_CONCEPTS: dict[str, dict[str, str]] = {
    "forward_curve_construction": {
        "help_text": "Forward curve construction maps current market data into internally consistent future rates.",
        "why_this_matters": "Consistent forward curves prevent technical mispricing in valuation and hedging.",
    },
    "convexity": {
        "help_text": "Convexity captures non-linear price sensitivity to rate changes.",
        "why_this_matters": "Ignoring convexity can distort futures-vs-FRA comparisons and hedge sizing.",
    },
    "pnl_decomposition": {
        "help_text": "P&L decomposition splits carry, curve shift, basis move, and residual effects.",
        "why_this_matters": "Component-level attribution improves diagnosis and risk response.",
    },
    "cip_decomposition": {
        "help_text": "CIP decomposition separates parity mechanics from funding/credit effects.",
        "why_this_matters": "Different basis drivers imply different trade horizon and hedging choices.",
    },
    "hedge_rationale": {
        "help_text": "Hedge rationale states what risk is neutralized and what remains intentionally open.",
        "why_this_matters": "Clear hedge rationale improves governance and prevents over-hedging.",
    },
}

EXPLAINER_LOADERS: dict[str, Callable[[], str]] = {
    "cip": lambda: CIPExplainer().explain(),
    "cross_currency": lambda: CrossCurrencyExplainer().explain(),
    "short_rate": lambda: ShortRateExplainer().explain(model_name="Hull-White"),
    "risk": lambda: RiskExplainer().explain(),
    "curve_fit": lambda: CurveFitExplainer().explain(),
    "risk_scenario": lambda: RiskScenarioExplainer().explain(),
    "policy_narrative": lambda: PolicyNarrativeExplainer().explain(),
}


class SharedExplainerAdapter:
    def __init__(self, explanation_mode: bool, basic_mode: bool = True) -> None:
        self.explanation_mode = bool(explanation_mode)
        self.basic_mode = bool(basic_mode)

    def build_panel(self, *, title: str, module: str, concept: str) -> ExplainerPanel:
        markdown = EXPLAINER_LOADERS[module]()
        if not self.explanation_mode:
            return ExplainerPanel(title=title, help_text=None, why_this_matters=None, markdown=markdown)

        concept_copy = CORE_CONCEPTS[concept]
        return ExplainerPanel(
            title=title,
            help_text=concept_copy["help_text"],
            why_this_matters=None if self.basic_mode else concept_copy["why_this_matters"],
            markdown=markdown,
        )


def build_shared_explainer_adapter(*, explanation_mode: bool, basic_mode: bool = True) -> SharedExplainerAdapter:
    return SharedExplainerAdapter(explanation_mode=explanation_mode, basic_mode=basic_mode)


# ---------- Curve ingestion helpers ----------

class CurveSchemaError(ValueError):
    """Raised when uploaded/manual curve input does not satisfy schema expectations."""


@dataclass(slots=True)
class CurveIngestionResult:
    source: str
    quotes: QuoteCollection

    @property
    def frame(self) -> pd.DataFrame:
        return self.quotes.to_frame()


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "tenor": ("tenor", "tenor_months", "tenor_years", "maturity", "term"),
    "rate": ("rate", "value", "yield", "zero_rate", "quote"),
    "date": ("timestamp", "date", "as_of", "asof"),
}


def _find_column(df: pd.DataFrame, logical_name: str) -> str | None:
    aliases = _COLUMN_ALIASES[logical_name]
    lowered = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def _normalize_uploaded_schema(df: pd.DataFrame, source: str) -> pd.DataFrame:
    tenor_col = _find_column(df, "tenor")
    rate_col = _find_column(df, "rate")
    date_col = _find_column(df, "date")

    missing_fields = []
    if tenor_col is None:
        missing_fields.append("tenor")
    if rate_col is None:
        missing_fields.append("rate")
    if missing_fields:
        raise CurveSchemaError(
            "Schema mismatch: missing required columns "
            f"{missing_fields}. Supported tenor aliases: {_COLUMN_ALIASES['tenor']}; "
            f"supported rate aliases: {_COLUMN_ALIASES['rate']}."
        )

    out = pd.DataFrame({"tenor": df[tenor_col], "value": pd.to_numeric(df[rate_col], errors="coerce")})
    if out["value"].isna().any():
        bad_rows = out.index[out["value"].isna()].tolist()
        raise CurveSchemaError(f"Schema mismatch: rate column contains non-numeric values at row(s) {bad_rows}.")

    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce", utc=True, format="mixed")
        if parsed.isna().any():
            bad_rows = parsed.index[parsed.isna()].tolist()
            raise CurveSchemaError(f"Schema mismatch: date/timestamp column contains unparsable values at row(s) {bad_rows}.")
        out["timestamp"] = parsed
    else:
        out["timestamp"] = datetime.now(timezone.utc)

    out["source"] = source
    out["instrument"] = "uploaded_curve"
    out["currency"] = "HUF"
    out["unit"] = "percent"
    return out


def _frame_to_quote_collection(normalized_df: pd.DataFrame, required_tenors: Iterable[str]) -> QuoteCollection:
    quotes = [
        MarketQuote(
            timestamp=row.timestamp.to_pydatetime().astimezone(timezone.utc),
            tenor=str(row.tenor),
            quote_type="yield",
            value=float(row.value),
            source=str(row.source),
            instrument=str(row.instrument),
            currency=str(row.currency),
            unit=str(row.unit),
        )
        for row in normalized_df.itertuples(index=False)
    ]
    validated = validate_quotes(
        quotes,
        required_tenors=required_tenors,
        stale_after_minutes=24 * 60,
        now=datetime.now(timezone.utc),
    )
    return QuoteCollection(validated)


def load_default_synthetic_curve(csv_path: str | Path, required_tenors: list[str]) -> CurveIngestionResult:
    return CurveIngestionResult(source="synthetic", quotes=load_bond_yields(csv_path, required_tenors=required_tenors))


def parse_uploaded_curve(file_obj: BinaryIO, required_tenors: list[str]) -> CurveIngestionResult:
    raw_df = pd.read_csv(file_obj)
    normalized = _normalize_uploaded_schema(raw_df, source="uploaded")
    quotes = _frame_to_quote_collection(normalized, required_tenors=required_tenors)
    return CurveIngestionResult(source="uploaded", quotes=quotes)


def parse_manual_nodes(nodes_df: pd.DataFrame, required_tenors: list[str]) -> CurveIngestionResult:
    normalized = _normalize_uploaded_schema(nodes_df, source="manual")
    quotes = _frame_to_quote_collection(normalized, required_tenors=required_tenors)
    return CurveIngestionResult(source="manual", quotes=quotes)


def select_curve_source(
    synthetic_curve: CurveIngestionResult,
    uploaded_curve: CurveIngestionResult | None,
    manual_curve: CurveIngestionResult | None,
) -> CurveIngestionResult:
    if manual_curve is not None:
        return manual_curve
    if uploaded_curve is not None:
        return uploaded_curve
    return synthetic_curve


def parse_uploaded_curve_via_default_loader(file_obj: BinaryIO, required_tenors: list[str]) -> CurveIngestionResult:
    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=True) as tmp:
        tmp.write(file_obj.read())
        tmp.flush()
        quotes = load_bond_yields(tmp.name, required_tenors=required_tenors)
    return CurveIngestionResult(source="uploaded", quotes=quotes)
