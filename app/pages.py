"""Page rendering adapters that consume precomputed pipeline outputs only."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def valuation_page(outputs: Mapping[str, Any]) -> Dict[str, Any]:
    pricing = outputs["pricing"]
    model = outputs["model"]
    return {
        "fra_pair": pricing["fra_pair"],
        "forward_rate": pricing["forward_rate"],
        "pv": pricing["pv"],
        "model_choice": model["model_choice"],
        "calibration": model["calibration"],
    }


def risk_page(outputs: Mapping[str, Any]) -> Dict[str, Any]:
    risk = outputs["risk"]
    return {
        "scenario": risk["scenario_used"]["name"],
        "pnl": risk["pnl"],
        "decomposition": risk["pnl_decomposition"],
        "hedge_solution": risk["hedge"]["solution"],
    }


def xccy_page(outputs: Mapping[str, Any]) -> Dict[str, Any]:
    xccy = outputs["xccy"]
    return {
        "cip_series": xccy["cip_raw_deviation"],
        "cip_mean_bp": xccy["cip_summary_bp"],
    }
