from __future__ import annotations

import numpy as np

from src.explainers import ShortRateExplainer


def test_short_rate_explainer_includes_requested_sections() -> None:
    explainer = ShortRateExplainer(currency="HUF", desk_name="sell-side STIR desk")
    text = explainer.explain(
        model_name="Hull-White",
        calibration_result={"a": 0.2, "sigma": 0.01, "rmse": 0.0003, "success": True},
        sim_short_rates=np.array([[0.03, 0.031], [0.03, 0.029]]),
        time_grid=np.array([0.0, 1.0]),
        fra_forwards=np.array([0.031, 0.032, 0.029]),
        fra_pnl=np.array([10.0, -5.0, 4.0]),
        dv01=1250.0,
        convexity_adjustment=0.0008,
    )

    assert "Why short-rate models matter" in text
    assert "Hull-White 1F assumptions" in text
    assert "Calibration inputs and interpretation" in text
    assert "Output interpretation" in text
    assert "sell-side STIR desk" in text
    assert "\\[" in text
