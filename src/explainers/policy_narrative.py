"""Explainers for macro and policy narrative framing."""

from __future__ import annotations

from .base import BaseExplainer


class PolicyNarrativeExplainer(BaseExplainer):
    """Frame quant outputs using macro-policy language for stakeholders."""

    def __init__(self) -> None:
        super().__init__(name="policy-narrative")
