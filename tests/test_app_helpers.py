from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from app.helpers import CurveSchemaError, parse_manual_nodes, parse_uploaded_curve, select_curve_source
from src.data.loaders.core import QuoteCollection


REQUIRED_TENORS = ["1M", "3M", "6M", "12M"]


def test_parse_uploaded_curve_accepts_aliases_and_dates() -> None:
    payload = b"term,zero_rate,as_of\n1M,6.2,2026-04-04\n3M,6.1,2026-04-04\n6M,5.9,2026-04-04\n12M,5.7,2026-04-04\n"
    out = parse_uploaded_curve(BytesIO(payload), REQUIRED_TENORS)

    assert out.source == "uploaded"
    frame = out.frame
    assert isinstance(out.quotes, QuoteCollection)
    assert set(frame["tenor"].tolist()) == set(REQUIRED_TENORS)


def test_parse_uploaded_curve_missing_tenor_rate_message() -> None:
    payload = b"date,foo\n2026-04-04,6.2\n"
    with pytest.raises(CurveSchemaError, match="missing required columns"):
        parse_uploaded_curve(BytesIO(payload), REQUIRED_TENORS)


def test_parse_uploaded_curve_bad_date_type_message() -> None:
    payload = b"tenor,rate,date\n1M,6.2,not-a-date\n3M,6.1,2026-04-04\n6M,5.9,2026-04-04\n12M,5.7,2026-04-04\n"
    with pytest.raises(CurveSchemaError, match="unparsable"):
        parse_uploaded_curve(BytesIO(payload), REQUIRED_TENORS)


def test_parse_manual_nodes_requires_completeness() -> None:
    manual = pd.DataFrame({"tenor": ["1M", "3M"], "rate": [6.1, 6.0]})

    with pytest.raises(Exception, match="Missing required tenors"):
        parse_manual_nodes(manual, REQUIRED_TENORS)


def test_source_precedence_manual_over_uploaded_over_synthetic() -> None:
    base_payload = b"tenor,rate\n1M,6.2\n3M,6.1\n6M,5.9\n12M,5.7\n"
    synthetic = parse_uploaded_curve(BytesIO(base_payload), REQUIRED_TENORS)
    synthetic.source = "synthetic"
    uploaded = parse_uploaded_curve(BytesIO(base_payload), REQUIRED_TENORS)
    manual = parse_manual_nodes(pd.DataFrame({"tenor": REQUIRED_TENORS, "rate": [6.2, 6.1, 5.9, 5.7]}), REQUIRED_TENORS)

    assert select_curve_source(synthetic, uploaded, manual).source == "manual"
    assert select_curve_source(synthetic, uploaded, None).source == "uploaded"
    assert select_curve_source(synthetic, None, None).source == "synthetic"
