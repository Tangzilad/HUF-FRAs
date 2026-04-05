from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.explainers.cip import CIPExplainer
from src.explainers.cross_currency import CrossCurrencyExplainer
from src.explainers.curve_fit import CurveFitExplainer
from src.explainers.policy_narrative import PolicyNarrativeExplainer
from src.explainers.risk import RiskExplainer
from src.explainers.risk_scenario import RiskScenarioExplainer
from src.explainers.short_rate import ShortRateExplainer


@dataclass(frozen=True)
class ExplainerPanel:
    """UI-ready explanation panel payload."""

    title: str
    help_text: str | None
    why_this_matters: str | None
    markdown: str


CORE_CONCEPTS: dict[str, dict[str, str]] = {
    "forward_curve_construction": {
        "help_text": (
            "Forward curve construction turns today's spot/discount inputs into implied future funding rates "
            "so pricing and hedging stay internally consistent across maturities."
        ),
        "why_this_matters": (
            "If the forward curve is built inconsistently, your FRA marks and hedge P&L can drift for technical reasons "
            "instead of real market moves. A clean forward curve keeps valuation, risk, and trading decisions aligned."
        ),
    },
    "convexity": {
        "help_text": (
            "Convexity means price sensitivity is curved, not linear: larger rate moves create disproportionately larger P&L effects."
        ),
        "why_this_matters": (
            "Ignoring convexity can make futures-vs-FRA comparisons look cheap or rich for the wrong reason. "
            "Including it improves hedge sizing under volatility spikes."
        ),
    },
    "pnl_decomposition": {
        "help_text": (
            "P&L decomposition separates carry, curve shift, basis move, and residual terms so you can see what really drove performance."
        ),
        "why_this_matters": (
            "Without decomposition, it is easy to confuse good carry with hidden directional risk. "
            "Decomposition helps desks adjust exposures before losses compound."
        ),
    },
    "cip_decomposition": {
        "help_text": (
            "CIP decomposition splits observed basis into risk-free parity, credit/liquidity components, and residual funding premium."
        ),
        "why_this_matters": (
            "This distinction matters because structural credit costs and temporary funding stress imply different trade horizons "
            "and different hedging choices."
        ),
    },
    "hedge_rationale": {
        "help_text": (
            "Hedge rationale explains which risk bucket is being neutralized, what residual exposure remains, and why that trade-off is acceptable."
        ),
        "why_this_matters": (
            "A clear hedge rationale prevents over-hedging and helps stakeholders understand expected protection versus carry drag."
        ),
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
    """Shared adapter that packages explanation text for app-level rendering."""

    def __init__(self, explanation_mode: bool, basic_mode: bool = True) -> None:
        self.explanation_mode = bool(explanation_mode)
        self.basic_mode = bool(basic_mode)

    def build_panel(self, *, title: str, module: str, concept: str) -> ExplainerPanel:
        markdown = EXPLAINER_LOADERS[module]()
        if not self.explanation_mode:
            return ExplainerPanel(title=title, help_text=None, why_this_matters=None, markdown=markdown)

        concept_copy = CORE_CONCEPTS[concept]
        help_text = concept_copy["help_text"]

        # In basic mode we keep only lightweight tooltips/help to avoid UI clutter.
        why_this_matters = None if self.basic_mode else concept_copy["why_this_matters"]
        return ExplainerPanel(title=title, help_text=help_text, why_this_matters=why_this_matters, markdown=markdown)


def build_shared_explainer_adapter(*, explanation_mode: bool, basic_mode: bool = True) -> SharedExplainerAdapter:
    """Factory used by app pages to consistently render explanation affordances."""

    return SharedExplainerAdapter(explanation_mode=explanation_mode, basic_mode=basic_mode)
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Iterable

import pandas as pd

from src.data.loaders.core import MarketQuote, QuoteCollection, QuoteValidationError, validate_quotes
from src.data.loaders.market_loaders import load_bond_yields


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
        parsed = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        if parsed.isna().any():
            bad_rows = parsed.index[parsed.isna()].tolist()
            raise CurveSchemaError(
                "Schema mismatch: date/timestamp column contains unparsable values "
                f"at row(s) {bad_rows}."
            )
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
    """Default ingestion route uses shared market loader + validation utilities."""

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
    """Manual or upload overrides synthetic only when complete and valid (already validated)."""

    if manual_curve is not None:
        return manual_curve
    if uploaded_curve is not None:
        return uploaded_curve
    return synthetic_curve


def parse_uploaded_curve_via_default_loader(file_obj: BinaryIO, required_tenors: list[str]) -> CurveIngestionResult:
    """Adapter that routes uploaded CSV through the default loader path for consistency."""

    with NamedTemporaryFile(mode="wb", suffix=".csv", delete=True) as tmp:
        tmp.write(file_obj.read())
        tmp.flush()
        quotes = load_bond_yields(tmp.name, required_tenors=required_tenors)
    return CurveIngestionResult(source="uploaded", quotes=quotes)
"""Shared helpers for formatting, adapters, and validation."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


def validate_positive(label: str, value: float) -> None:
    """Raise ``ValueError`` if ``value`` is not strictly positive."""

    if value <= 0.0:
        raise ValueError(f"{label} must be positive, received {value}.")


def to_panel_dataframe(
    *,
    spot: float,
    forward: float,
    domestic_ois: float,
    foreign_ois: float,
    tenor_years: Iterable[float],
) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build tenor-aligned inputs for CIP analytics from scalar controls."""

    tenor_idx = [float(t) for t in tenor_years]
    spot_series = pd.Series([spot], index=[pd.Timestamp("today").normalize()], dtype=float)
    forward_df = pd.DataFrame([[forward for _ in tenor_idx]], index=spot_series.index, columns=tenor_idx, dtype=float)
    domestic_df = pd.DataFrame(
        [[domestic_ois for _ in tenor_idx]],
        index=spot_series.index,
        columns=tenor_idx,
        dtype=float,
    )
    foreign_df = pd.DataFrame(
        [[foreign_ois for _ in tenor_idx]],
        index=spot_series.index,
        columns=tenor_idx,
        dtype=float,
    )
    return spot_series, forward_df, domestic_df, foreign_df


def format_bp(value: float) -> str:
    """Format decimal value in basis points."""

    return f"{value:,.2f} bp"
