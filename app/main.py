from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from app.helpers import (
    CurveSchemaError,
    load_default_synthetic_curve,
    parse_manual_nodes,
    parse_uploaded_curve,
    select_curve_source,
)
from src.data.loaders.core import QuoteValidationError

REQUIRED_TENORS = ["1M", "3M", "6M", "12M"]
DEFAULT_SYNTHETIC_CURVE = Path("data/synthetic_bond_yields.csv")


st.set_page_config(page_title="HUF FRA Curve Ingestion", layout="wide")
st.title("HUF FRA Curve Ingestion")
st.caption("Default path uses market loader utilities; uploaded/manual data can override when valid + complete.")

with st.sidebar:
    st.header("Curve inputs")
    uploaded_file = st.file_uploader("Upload curve CSV", type=["csv"])

    st.subheader("Manual node entry")
    default_nodes = pd.DataFrame(
        {
            "tenor": ["1M", "3M", "6M", "12M"],
            "rate": [6.20, 6.10, 5.95, 5.75],
            "date": [pd.Timestamp.today().date()] * 4,
        }
    )
    manual_nodes = st.data_editor(
        default_nodes,
        num_rows="dynamic",
        use_container_width=True,
        key="manual_curve_editor",
    )

synthetic_result = None
uploaded_result = None
manual_result = None
messages: list[tuple[str, str]] = []

try:
    synthetic_result = load_default_synthetic_curve(DEFAULT_SYNTHETIC_CURVE, REQUIRED_TENORS)
    messages.append(("info", "Loaded synthetic/default curve through `src.data.loaders.market_loaders.load_bond_yields`."))
except FileNotFoundError:
    messages.append(("warning", f"Default synthetic curve file was not found at `{DEFAULT_SYNTHETIC_CURVE}`."))
except (QuoteValidationError, CurveSchemaError, ValueError) as exc:
    messages.append(("error", f"Synthetic/default curve is invalid: {exc}"))

if uploaded_file is not None:
    try:
        uploaded_result = parse_uploaded_curve(uploaded_file, REQUIRED_TENORS)
        messages.append(("success", "Uploaded CSV passed schema + completeness checks and is eligible to override synthetic input."))
    except (QuoteValidationError, CurveSchemaError, ValueError) as exc:
        messages.append(("error", f"Uploaded CSV failed validation and will not override synthetic source: {exc}"))

if not manual_nodes.empty:
    try:
        manual_result = parse_manual_nodes(manual_nodes, REQUIRED_TENORS)
        messages.append(("success", "Manual node table passed schema + completeness checks and is eligible to override synthetic input."))
    except (QuoteValidationError, CurveSchemaError, ValueError) as exc:
        messages.append(("error", f"Manual node table failed validation and will not override synthetic source: {exc}"))

for level, msg in messages:
    getattr(st, level)(msg)

if synthetic_result is not None:
    selected = select_curve_source(synthetic_result, uploaded_result, manual_result)
    st.subheader(f"Effective source: {selected.source}")
    st.dataframe(selected.frame, use_container_width=True)
else:
    st.error("No valid curve source available. Fix synthetic path or provide complete/valid uploaded or manual data.")
