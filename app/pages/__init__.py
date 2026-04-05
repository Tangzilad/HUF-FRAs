"""Page renderers for the Streamlit app."""

from .home import render as render_home_page
from .cip_page import render as render_cip_page
from .cross_currency_page import render as render_cross_currency_page
from .short_rate_page import render as render_short_rate_page

__all__ = ["render_home_page", "render_cip_page", "render_cross_currency_page", "render_short_rate_page"]
