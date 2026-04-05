from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import json


@dataclass
class EMScenario:
    name: str
    description: str
    rates_bp: Dict[str, float]
    fx_pct: Dict[str, float]
    basis_bp: Dict[str, float]
    risk_off: Dict[str, float]


TENOR_SHOCK_KEYS = ["front", "belly", "back"]


def em_scenario_library() -> List[EMScenario]:
    """Coherent cross-asset stress scenarios for EM rates books."""

    return [
        EMScenario(
            name="capital_outflow_shock",
            description="Foreign capital exits EM local markets, rates + basis widen, FX weakens.",
            rates_bp={"front": 120.0, "belly": 95.0, "back": 70.0},
            fx_pct={"spot": 8.0, "vol": 20.0},
            basis_bp={"front": 35.0, "belly": 30.0, "back": 25.0},
            risk_off={"vix": 12.0, "credit_spread_bp": 70.0},
        ),
        EMScenario(
            name="currency_devaluation_shock",
            description="Policy break drives abrupt devaluation and imported inflation repricing.",
            rates_bp={"front": 180.0, "belly": 140.0, "back": 90.0},
            fx_pct={"spot": 15.0, "vol": 35.0},
            basis_bp={"front": 50.0, "belly": 42.0, "back": 30.0},
            risk_off={"vix": 18.0, "credit_spread_bp": 95.0},
        ),
        EMScenario(
            name="sovereign_downgrade_liquidity_shock",
            description="Sovereign downgrade with impaired market depth and wider funding basis.",
            rates_bp={"front": 90.0, "belly": 130.0, "back": 160.0},
            fx_pct={"spot": 10.0, "vol": 25.0},
            basis_bp={"front": 40.0, "belly": 55.0, "back": 65.0},
            risk_off={"vix": 15.0, "credit_spread_bp": 120.0},
        ),
    ]


def validate_scenario(scenario: EMScenario) -> None:
    for key in TENOR_SHOCK_KEYS:
        if key not in scenario.rates_bp or key not in scenario.basis_bp:
            raise ValueError(f"Scenario '{scenario.name}' missing tenor key '{key}'.")
    for key in ["spot", "vol"]:
        if key not in scenario.fx_pct:
            raise ValueError(f"Scenario '{scenario.name}' missing FX key '{key}'.")


def export_scenario_templates(output_dir: str | Path) -> List[Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    out = []
    for s in em_scenario_library():
        validate_scenario(s)
        f = path / f"{s.name}.json"
        f.write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")
        out.append(f)
    return out
