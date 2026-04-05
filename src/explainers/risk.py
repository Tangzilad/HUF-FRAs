from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class RiskExplainer:
    """Generate desk-oriented narrative for the EM rates risk stack.

    The explainer turns model outputs into a concise report with four required
    sections used by tests and practitioner workflows.
    """

    confidence: float = 0.99

    def explain(
        self,
        returns: Optional[pd.Series] = None,
        scenario_name: Optional[str] = None,
        scenario_pnl: Optional[pd.DataFrame] = None,
        factor_decomposition: Optional[Dict[str, np.ndarray]] = None,
        hedge_output: Optional[Dict[str, pd.DataFrame | float]] = None,
    ) -> str:
        """Build a structured risk report.

        Parameters are optional so the explainer can be used in tests and in
        interactive notebooks where only a subset of artifacts is available.
        """

        sections = [
            self._var_es_section(returns),
            self._stress_section(scenario_name, scenario_pnl),
            self._factor_section(factor_decomposition),
            self._hedge_section(hedge_output),
            self._desk_interpretation(scenario_pnl),
        ]
        return "\n\n".join(sections)

    def _var_es_section(self, returns: Optional[pd.Series]) -> str:
        method = (
            "Historical simulation with empirical tails and a Gaussian parametric cross-check."
            if returns is not None and len(returns) > 0
            else "Configured for historical simulation with a Gaussian parametric reference."
        )
        assumptions = (
            "Assumptions: stationarity over the lookback window, stable liquidity, and linearized first-order sensitivities (DV01 and basis01) around current marks."
        )
        return (
            "## VaR/ES methodology and assumptions\n"
            f"- VaR confidence: {self.confidence:.1%}.\n"
            "- ES is computed as the conditional mean loss beyond the VaR cutoff, emphasizing tail severity rather than just threshold breaches.\n"
            f"- Methodology: {method}\n"
            f"- {assumptions}\n"
            "- Convexity caveat: nonlinear payoffs can make realized losses exceed linear VaR/ES approximations in gap moves."
        )

    def _stress_section(self, scenario_name: Optional[str], scenario_pnl: Optional[pd.DataFrame]) -> str:
        scn = scenario_name or "EM macro stress scenario"
        pnl_line = ""
        if scenario_pnl is not None and not scenario_pnl.empty and "pnl_total" in scenario_pnl.columns:
            total = float(scenario_pnl["pnl_total"].sum())
            pnl_line = f"\n- Scenario aggregate P&L: {total:,.2f}."

        return (
            "## Stress scenario mechanics and macro regime-shift interpretation\n"
            f"- Scenario framework: {scn}.\n"
            "- Mechanics: shocks propagate through rates curve buckets, FX spot/vol, and cross-currency basis to produce trade-level and book-level P&L.\n"
            "- Regime-shift interpretation: capital outflow, devaluation, or sovereign-liquidity stress implies a transition from carry-friendly conditions to funding-fragile markets with wider basis and reduced depth."
            f"{pnl_line}\n"
            "- Desk lens: large losses concentrated in front-end DV01 or basis exposures indicate vulnerability to policy surprise and funding squeezes."
        )

    def _factor_section(self, factor_decomposition: Optional[Dict[str, np.ndarray]]) -> str:
        factor_line = ""
        if factor_decomposition and "explained_variance" in factor_decomposition:
            ev = factor_decomposition["explained_variance"]
            if len(ev) > 0:
                first = float(ev[0])
                factor_line = f"\n- First principal factor explained variance: {first:.2%}."

        return (
            "## Factor model decomposition and basis/funding channels\n"
            "- PCA decomposition separates directional curve risk from macro co-movements (inflation expectations, FX level/volatility, and risk-off indicators).\n"
            "- Basis/funding channels: widening cross-currency basis captures offshore USD funding stress and translates into carry drag plus mark-to-market losses.\n"
            "- Interpretation: when basis and front-end rates load together, funding pressure is likely the dominant transmission channel rather than pure duration repricing."
            f"{factor_line}\n"
            "- Convexity reminder: second-order rate effects can distort a pure linear factor attribution during violent curve twists."
        )

    def _hedge_section(self, hedge_output: Optional[Dict[str, pd.DataFrame | float]]) -> str:
        hedge_line = ""
        if hedge_output and "total_objective" in hedge_output:
            hedge_line = f"\n- Optimizer total objective: {float(hedge_output['total_objective']):,.4f}."

        return (
            "## Hedging optimiser outputs and implementation caveats\n"
            "- Output summary: optimal notionals by instrument/tenor, expected carry cost, liquidity usage, and binding constraints.\n"
            "- Implementation caveats: transaction-cost regularization, max-notional caps, and tenor concentration limits can force residual risk even when model fit is strong.\n"
            "- Slippage warning: execution timing, bid/offer widening, and hedge rebalance latency can produce hedge slippage versus optimizer assumptions."
            f"{hedge_line}\n"
            "- Governance: treat optimizer as decision support; trader judgment is required when basis liquidity thins or convexity risk is elevated."
        )

    def _desk_interpretation(self, scenario_pnl: Optional[pd.DataFrame]) -> str:
        tail_hint = ""
        if scenario_pnl is not None and not scenario_pnl.empty and "pnl_total" in scenario_pnl.columns:
            q01 = float(np.quantile(scenario_pnl["pnl_total"], 0.01))
            tail_hint = f" Observed desk tail marker (1% trade-level quantile): {q01:,.2f}."

        return (
            "## Desk-oriented interpretation: tails, slippage, and model risk\n"
            "- P&L tails: compare realized downside episodes to VaR and ES exceedances; recurring breaches suggest unstable correlations or hidden jump risk.\n"
            "- Hedge slippage: monitor realized vs projected hedge P&L by execution window to isolate market impact and liquidity regime effects.\n"
            "- Model risk: challenge assumptions on stationarity, basis liquidity, and linear DV01 mapping; stress nonlinear convexity and basis dislocations explicitly."
            f"{tail_hint}\n"
            "- Mandatory risk terms tracked in this narrative: VaR, ES, DV01, basis, convexity."
        )
