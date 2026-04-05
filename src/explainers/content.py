from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TopicName = Literal["parametric", "short-rate", "cross-currency", "cip", "risk"]
SectionName = Literal["full", "concepts", "inputs", "calibration", "outputs", "trading"]
OutputFormat = Literal["md", "text"]

SECTIONS: tuple[str, ...] = (
    "concepts",
    "inputs",
    "calibration",
    "outputs",
    "trading",
)


@dataclass(frozen=True)
class TopicExplanation:
    title: str
    sections: dict[str, str]


TOPIC_EXPLANATIONS: dict[TopicName, TopicExplanation] = {
    "parametric": TopicExplanation(
        title="Parametric Curve Fitting",
        sections={
            "concepts": (
                "Parametric term-structure models summarize an entire yield curve with a small set of factors. "
                "The project supports Nelson-Siegel and Svensson forms so traders can compare smoothness and long-end flexibility."
            ),
            "inputs": (
                "Provide tenors in years and observed yields in decimal form. Optional weights can reflect liquidity, bid-ask, "
                "or confidence in specific maturities."
            ),
            "calibration": (
                "Calibration minimizes weighted pricing/yield errors under parameter bounds and regularization. "
                "Use bounds to avoid unstable hump shapes and regularization to prevent overfitting sparse points."
            ),
            "outputs": (
                "Outputs include fitted parameters, callable curve evaluators, and fitted-vs-observed diagnostics suitable for charting and QA."
            ),
            "trading": (
                "Use residuals to spot curve rich/cheap points, and track parameter shifts to monitor macro repricing versus microstructure noise."
            ),
        },
    ),
    "short-rate": TopicExplanation(
        title="Short-Rate Models",
        sections={
            "concepts": (
                "Short-rate frameworks model the instantaneous policy-relevant rate and derive bond/FRA prices from its dynamics. "
                "Hull-White and Ho-Lee variants in this repo emphasize tractable calibration and scenario stressing."
            ),
            "inputs": (
                "Inputs usually include discount curve anchors, FRA tenors, and optional volatility assumptions used in convexity-aware pricing."
            ),
            "calibration": (
                "Fit mean-reversion and volatility terms to market observables, then validate that model-implied FRAs and discounts remain close to quotes."
            ),
            "outputs": (
                "Typical outputs are path statistics, analytic pricing objects, and fair FRA rates under baseline and shocked assumptions."
            ),
            "trading": (
                "Translate calibration changes into carry/roll-down views, convexity adjustments, and hedge-ratio updates for short-end books."
            ),
        },
    ),
    "cross-currency": TopicExplanation(
        title="Cross-Currency Curves",
        sections={
            "concepts": (
                "Cross-currency analytics combine domestic and foreign curves with a basis spread so FX-converted discounting remains internally consistent."
            ),
            "inputs": (
                "Use spot FX, forward FX, and tenor-aligned domestic/foreign rates or discount factors, with conventions standardized before calibration."
            ),
            "calibration": (
                "Solve for basis terms that reconcile observed forwards and swap quotes, then smooth the tenor profile for stable risk attribution."
            ),
            "outputs": (
                "Outputs include basis-by-tenor vectors, implied forward checks, and panel data for dashboard visualizations."
            ),
            "trading": (
                "A steepening basis can indicate funding stress; compare basis dynamics with CIP diagnostics before expressing RV trades."
            ),
        },
    ),
    "cip": TopicExplanation(
        title="Covered Interest Parity (CIP)",
        sections={
            "concepts": (
                "CIP links FX forwards to domestic and foreign funding rates. Persistent deviations can proxy balance-sheet constraints or collateral frictions."
            ),
            "inputs": (
                "Supply spot/forward FX quotes, tenor day-count assumptions, and matched domestic/foreign rates (plus optional sovereign/liquidity proxies)."
            ),
            "calibration": (
                "Compute implied-rate gaps tenor-by-tenor and optionally purify raw basis by removing local credit/liquidity differentials."
            ),
            "outputs": (
                "Generate raw and purified basis series, decomposition tables, and stress labels for monitoring dislocations over time."
            ),
            "trading": (
                "Treat short-lived spikes as potential execution/microstructure events, while broad persistent gaps can justify structural hedges."
            ),
        },
    ),
    "risk": TopicExplanation(
        title="Risk and Stress Testing",
        sections={
            "concepts": (
                "Risk modules combine scenario shocks, factor views, and backtesting to evaluate how curve and basis moves impact P&L."
            ),
            "inputs": (
                "Provide position sensitivities, baseline curves, scenario templates, and optional factor covariance estimates."
            ),
            "calibration": (
                "Calibrate factor loadings or scenario magnitudes to historical regimes, then validate stability with out-of-sample windows."
            ),
            "outputs": (
                "Outputs include stressed P&L distributions, tail metrics, hedge efficiency diagnostics, and scenario attribution slices."
            ),
            "trading": (
                "Use scenario outputs to size hedges, set risk limits, and prioritize trades that improve downside resilience without sacrificing carry."
            ),
        },
    ),
}


def render_topic(topic: TopicName, section: SectionName = "full", output_format: OutputFormat = "md") -> str:
    explanation = TOPIC_EXPLANATIONS[topic]
    sections = list(SECTIONS) if section == "full" else [section]

    if output_format == "md":
        lines = [f"## {explanation.title}"]
        for name in sections:
            lines.append(f"### {name.title()}")
            lines.append(explanation.sections[name])
    else:
        lines = [explanation.title, "=" * len(explanation.title)]
        for name in sections:
            lines.append("")
            lines.append(name.upper())
            lines.append(explanation.sections[name])
    return "\n".join(lines).strip()


def render_explanation(
    topic: TopicName | Literal["all"] = "all",
    section: SectionName = "full",
    output_format: OutputFormat = "md",
) -> str:
    topics = list(TOPIC_EXPLANATIONS.keys()) if topic == "all" else [topic]
    blocks = [render_topic(name, section=section, output_format=output_format) for name in topics]
    separator = "\n\n---\n\n" if output_format == "md" else "\n\n" + ("-" * 72) + "\n\n"
    return separator.join(blocks).strip()
