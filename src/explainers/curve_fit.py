"""Explainers for curve calibration diagnostics."""

from __future__ import annotations

from .base import BaseExplainer


class CurveFitExplainer(BaseExplainer):
    """Summarize curve fit quality and parameter dynamics."""

    def __init__(self) -> None:
        super().__init__(name="curve-fit")
