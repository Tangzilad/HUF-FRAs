"""Markdown explainers for core analytics modules."""

from .base import BaseExplainer
from .cip import CIPExplainer
from .cross_currency import CrossCurrencyExplainer
from .parametric_curve import ParametricCurveExplainer
from .risk import RiskExplainer
from .short_rate import ShortRateExplainer, summarize_convexity_table

__all__ = [
    "BaseExplainer",
    "ParametricCurveExplainer",
    "ShortRateExplainer",
    "CrossCurrencyExplainer",
    "CIPExplainer",
    "RiskExplainer",
    "summarize_convexity_table",
]
