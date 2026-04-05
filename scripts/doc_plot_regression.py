from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.curves.parametric import fit_parametric_curve
from src.visualization.market_diagnostics import (
    plot_basis_term_premium_panel,
    plot_cip_deviation,
    plot_fitted_vs_observed,
)

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = [
    ROOT / "notebooks" / "huf_usd_end_to_end_calibration.ipynb",
    ROOT / "notebooks" / "simulation_and_convexity_workflow.ipynb",
    ROOT / "notebooks" / "hedging_and_stress_testing_workflow.ipynb",
]


def check_notebooks() -> None:
    for nb_path in NOTEBOOKS:
        payload = json.loads(nb_path.read_text())
        if payload.get("nbformat") != 4:
            raise ValueError(f"Notebook has unexpected format: {nb_path}")
        if len(payload.get("cells", [])) < 2:
            raise ValueError(f"Notebook has too few cells: {nb_path}")


def check_plot_generation() -> None:
    out = ROOT / "artifacts" / "regression"
    out.mkdir(parents=True, exist_ok=True)

    tenors = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10], dtype=float)
    observed = np.array([0.068, 0.067, 0.066, 0.064, 0.063, 0.062, 0.0615, 0.061], dtype=float)
    fit = fit_parametric_curve(tenors, observed, model="nelson_siegel")
    fitted = fit.curve(tenors)

    p1 = plot_fitted_vs_observed(tenors, observed, fitted, out / "fitted_vs_observed.png")

    dates = pd.date_range("2026-01-01", periods=6, freq="D")
    cip = pd.DataFrame(
        {
            "timestamp": np.repeat(dates, 3),
            "tenor": ["1M", "3M", "6M"] * len(dates),
            "cip_deviation_bp": np.tile([3.2, 1.1, -0.4], len(dates)),
        }
    )
    p2 = plot_cip_deviation(cip, out / "cip_deviation.png")

    panel = pd.DataFrame(
        {
            "tenor_years": [1, 2, 3, 5, 10],
            "basis_bp": [14, 11, 9, 8, 6],
            "term_premium_bp": [22, 19, 15, 13, 10],
        }
    )
    p3 = plot_basis_term_premium_panel(panel, out / "basis_term_premium.png")

    for path in (p1, p2, p3):
        if path.stat().st_size <= 0:
            raise ValueError(f"Generated empty plot file: {path}")


if __name__ == "__main__":
    check_notebooks()
    check_plot_generation()
    print("Notebook smoke and plot regression checks passed.")
