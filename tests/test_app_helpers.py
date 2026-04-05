from __future__ import annotations

from app.helpers import CORE_CONCEPTS, build_shared_explainer_adapter


def test_shared_adapter_basic_mode_stays_minimal() -> None:
    adapter = build_shared_explainer_adapter(explanation_mode=True, basic_mode=True)
    panel = adapter.build_panel(
        title="Curve view",
        module="curve_fit",
        concept="forward_curve_construction",
    )

    assert panel.help_text is not None
    assert panel.why_this_matters is None
    assert "forward curve" in panel.markdown.lower()


def test_shared_adapter_full_explanation_mode_adds_expandable_copy() -> None:
    adapter = build_shared_explainer_adapter(explanation_mode=True, basic_mode=False)
    panel = adapter.build_panel(
        title="Risk summary",
        module="risk",
        concept="hedge_rationale",
    )

    assert panel.help_text is not None
    assert panel.why_this_matters is not None
    assert "hedge" in panel.why_this_matters.lower()


def test_core_concepts_have_plain_english_explanations() -> None:
    required = {
        "forward_curve_construction",
        "convexity",
        "pnl_decomposition",
        "cip_decomposition",
        "hedge_rationale",
    }
    assert required.issubset(CORE_CONCEPTS)

    for concept in required:
        payload = CORE_CONCEPTS[concept]
        assert payload["help_text"]
        assert payload["why_this_matters"]


def test_adapter_consumes_all_requested_explainer_modules() -> None:
    adapter = build_shared_explainer_adapter(explanation_mode=False, basic_mode=True)

    module_to_concept = {
        "cip": "cip_decomposition",
        "cross_currency": "forward_curve_construction",
        "short_rate": "convexity",
        "risk": "pnl_decomposition",
        "curve_fit": "forward_curve_construction",
        "risk_scenario": "hedge_rationale",
        "policy_narrative": "hedge_rationale",
    }

    for module, concept in module_to_concept.items():
        panel = adapter.build_panel(title=module, module=module, concept=concept)
        assert panel.markdown
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
