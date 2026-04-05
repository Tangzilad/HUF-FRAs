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
