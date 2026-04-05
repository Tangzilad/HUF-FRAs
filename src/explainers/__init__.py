"""Markdown explainers for core analytics modules."""

from .base import BaseExplainer
from .cip import CIPExplainer
from .cross_currency import CrossCurrencyExplainer
from .curve_fit import CurveFitExplainer
from .parametric_curve import ParametricCurveExplainer
from .policy_narrative import PolicyNarrativeExplainer
from .risk import RiskExplainer
from .risk_scenario import RiskScenarioExplainer
from .short_rate import ShortRateExplainer, summarize_convexity_table
from .simulation_narrative import FRASimContext, ScenarioContext, SimulationNarrativeGenerator
from .slope_curvature import SlopeCurvatureExplainer

__all__ = [
    "BaseExplainer",
    "ParametricCurveExplainer",
    "CurveFitExplainer",
    "ShortRateExplainer",
    "CrossCurrencyExplainer",
    "CIPExplainer",
    "RiskExplainer",
    "RiskScenarioExplainer",
    "PolicyNarrativeExplainer",
    "summarize_convexity_table",
    "FRASimContext",
    "ScenarioContext",
    "SimulationNarrativeGenerator",
    "SlopeCurvatureExplainer",
]
