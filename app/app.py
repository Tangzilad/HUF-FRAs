from __future__ import annotations

from typing import Any, Dict

from .helpers import build_curve_table, run_cip_path, run_pricing_engine, run_risk_engine
from .state import build_state


def boot(state_overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Boot app engines and return their deterministic outputs."""

    payload = build_state(state_overrides)
    return {
        "curves": build_curve_table(payload),
        "pricing": run_pricing_engine(payload),
        "risk": run_risk_engine(payload),
        "cip": run_cip_path(payload),
    }
