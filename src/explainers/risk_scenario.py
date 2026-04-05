"""Explainers for stress-test and scenario outputs."""

from __future__ import annotations

from .base import BaseExplainer


class RiskScenarioExplainer(BaseExplainer):
    """Summarize risk scenario impacts for portfolio diagnostics."""

    def __init__(self) -> None:
        super().__init__(name="risk-scenario")
