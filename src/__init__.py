"""HUF FRA analytics package."""

from .explainers import ShortRateExplainer as ShortRateExplainer
from .explainers import summarize_convexity_table as summarize_convexity_table

__all__ = ["ShortRateExplainer", "summarize_convexity_table"]
