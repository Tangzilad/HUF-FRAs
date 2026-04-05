"""Explainers for macro and policy narrative framing."""

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseExplainer


@dataclass(frozen=True)
class PolicyNarrativeExplainer(BaseExplainer):
    """Frame quant outputs using macro-policy language for stakeholders."""

    title: str = "Policy Narrative Explainer"

    def explain_concepts(self) -> str:
        return (
            "Policy narratives translate quantitative signals into central-bank and macro storytelling. "
            "The goal is to connect technical model outputs to intuitive decision language."
        )

    def explain_inputs(self) -> str:
        return (
            "- Core analytics outputs (curve shifts, basis moves, stress P&L).\n"
            "- Macro context (inflation trend, growth signals, external funding backdrop).\n"
            "- Policy-event timeline and communication regime assumptions."
        )

    def explain_calibration(self) -> str:
        return (
            "Narrative calibration links observed factor moves to a concise macro interpretation, "
            "with explicit confidence qualifiers so users can separate data-supported claims from judgment calls."
        )

    def explain_outputs(self) -> str:
        return (
            "Outputs are plain-English summaries, risk signposts, and action-oriented commentary. "
            "They should preserve key numbers while avoiding jargon overload."
        )

    def explain_trading_implications(self) -> str:
        return (
            "A consistent narrative helps align traders, risk managers, and stakeholders around the same risk map. "
            "It improves hedge timing by clarifying which risks are cyclical noise versus regime-defining changes."
        )
