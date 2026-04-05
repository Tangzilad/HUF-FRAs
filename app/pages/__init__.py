"""Page renderers for the Streamlit app."""


def render_home_page(*args, **kwargs):
    from .home import render

    return render(*args, **kwargs)


def render_cip_page(*args, **kwargs):
    from .cip_page import render

    return render(*args, **kwargs)


def render_cross_currency_page(*args, **kwargs):
    from .cross_currency_page import render

    return render(*args, **kwargs)


def render_short_rate_page(*args, **kwargs):
    from .short_rate_page import render

    return render(*args, **kwargs)


def render_risk_pnl_page(*args, **kwargs):
    from .risk_pnl import main

    return main(*args, **kwargs)


def render_stress_lab_page(*args, **kwargs):
    from .stress_lab import render

    return render(*args, **kwargs)


__all__ = [
    "render_home_page",
    "render_cip_page",
    "render_cross_currency_page",
    "render_short_rate_page",
    "render_risk_pnl_page",
    "render_stress_lab_page",
]
