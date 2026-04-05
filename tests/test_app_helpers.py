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
