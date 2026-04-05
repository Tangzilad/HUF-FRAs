"""Page renderers for the Streamlit app."""

from .home import render as render_home_page
from .cip_page import render as render_cip_page
from .cross_currency_page import render as render_cross_currency_page
from .short_rate_page import render as render_short_rate_page
from .risk_pnl import render as render_risk_pnl_page
from .stress_lab import render as render_stress_lab_page

__all__ = [
    "render_home_page",
    "render_cip_page",
    "render_cross_currency_page",
    "render_short_rate_page",
    "render_risk_pnl_page",
    "render_stress_lab_page",
]
