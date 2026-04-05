from __future__ import annotations

from pathlib import Path

import pandas as pd

from fra_simulation import generate_base_curves, run_scenario, save_dataframe


def test_base_and_stressed_outputs_export_to_csv(tmp_path: Path) -> None:
    base_curve = generate_base_curves()
    stressed = run_scenario("war_shock")

    base_path = save_dataframe(base_curve, tmp_path, "base_curve.csv")
    stressed_path = save_dataframe(stressed["huf_gran"], tmp_path, "stressed_huf_gran.csv")

    assert base_path.exists()
    assert stressed_path.exists()

    base_loaded = pd.read_csv(base_path)
    stressed_loaded = pd.read_csv(stressed_path)

    assert not base_loaded.empty
    assert not stressed_loaded.empty
    assert {"month", "huf_zero", "usd_zero"}.issubset(base_loaded.columns)
    assert {"fra", "pnl", "bucket"}.issubset(stressed_loaded.columns)
