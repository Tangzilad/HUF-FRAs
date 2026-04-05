"""Narrative explainer for cross-currency curve construction and risk interpretation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CrossCurrencyExplainer:
    """Build a practical walkthrough of cross-currency discounting and basis risk."""

    base_pair: str = "HUF/USD"
    domestic_collateral: str = "HUF"
    foreign_collateral: str = "USD"

    def _conceptual_walkthrough(self) -> str:
        return (
            "## 1) Domestic/foreign discounting and basis construction\n"
            "- Start from domestic and foreign OIS discount factors, where each tenor point is converted "
            "to a simple-compounded discount factor by `1 / (1 + r*t)`.\n"
            "- For a currency pair `DOM/FOR`, CIP implies `F(t) = S * DF_dom(t) / DF_for(t)` when there is no basis.\n"
            "- In practice, a basis term structure `b(t)` adjusts the foreign leg so the modeled forward becomes "
            "`F_model(t) = S * DF_dom(t) / (DF_for(t) * exp(-b(t)*t))`.\n"
            "- Calibration jointly fits FX forwards and quoted xccy basis swaps at shared tenors, then smooths the curve "
            "using a second-difference penalty.\n"
            "- The output basis is therefore a market-consistent wedge between idealized CIP and observed funding "
            "conditions across maturities.\n"
        )

    def _market_inputs(self) -> str:
        return (
            "## 2) Required market inputs and data contracts\n"
            "- **FX spot and forwards:** spot for each pair (`fx_spot[pair]`) and forward quotes by tenor (`fx_forwards[pair]`).\n"
            "- **OIS discount proxies:** `ois_by_ccy` for domestic and foreign discounting anchors.\n"
            "- **IBOR/IRS projection proxies:** `irs_by_ccy` for projection curves where needed for floating leg interpretation.\n"
            "- **Quoted basis swaps:** `xccy_basis_by_pair[pair]` in decimal rate units by tenor.\n"
            "- **Tenor completeness:** `validate_quotes` enforces required tenors and can reject incomplete curves.\n"
            "- **Quote typing and units (loader contract):**\n"
            "  - FX forwards should load as `quote_type='forward'` with `unit='points'` (stale threshold: 30 minutes).\n"
            "  - Swap proxies should load as `quote_type='spread'` with `unit='bps'` (stale threshold: 90 minutes).\n"
            "  - Yield proxies should load as `quote_type='yield'` with `unit='percent'`.\n"
            "- **Quality metadata:** bid/ask, liquidity score, and quality flags support filtering stale/NaN observations before calibration.\n"
        )

    def _interpolation_and_edge_cases(self) -> str:
        return (
            "## 3) Interpolation, extrapolation, and edge cases\n"
            "- Discount-curve interpolation can be run in log-discount-factor or zero-rate space.\n"
            "- Preferred scheme is monotone cubic; if monotonicity is violated (or too few points), the implementation "
            "falls back to linear interpolation for stability.\n"
            "- Extrapolation at endpoints is flat in transformed space via boundary interval reuse, which is conservative "
            "but can understate tail convexity.\n"
            "- Edge cases to monitor:\n"
            "  - Missing tenor keys across spot/forwards/discount curves (hard failures or misalignment).\n"
            "  - Non-positive discount factors (invalid for log-DF mode).\n"
            "  - Very short maturities where `t -> 0` can magnify numerical noise in implied basis residuals.\n"
            "  - Overfitting if smoothness is set too low with sparse or noisy quotes.\n"
        )

    def _pricing_and_hedging_interpretation(self) -> str:
        return (
            "## 4) How to interpret outputs for pricing and hedging\n"
            "- **Basis level (`b(t)`):** signed funding premium/discount required to reconcile FX forwards with both discount curves.\n"
            "- **Basis slope/curvature:** term-funding pressure; steepening often signals maturity-specific balance-sheet constraints.\n"
            "- **Collateralized discount factors:** changing collateral currency remaps PV through `exp(±b(t)*t)` adjustments.\n"
            "- **Cross-currency DV01 mapping:** map a trade's PV sensitivity to basis-node bumps and local OIS-node bumps, "
            "then translate into hedge notionals in traded basis maturities (e.g., 2Y/5Y/10Y).\n"
            "- **Risk decomposition:** separate FX delta, domestic rates DV01, foreign rates DV01, and basis DV01 to avoid "
            "double counting in macro hedges.\n"
        )

    def _residual_usd_exposure(self) -> str:
        return (
            "## 5) Managing residual USD exposure in practice\n"
            "- Even after primary xccy hedges, desks often retain residual USD PV01 due to tenor mismatch, interpolation, "
            "and balance-sheet constraints.\n"
            "- Practical workflow:\n"
            "  1. Compute residual USD DV01 bucketed by liquid maturities.\n"
            "  2. Select liquid basis instruments (short-dated FX swaps, 1Y/2Y/5Y xccy basis swaps, occasionally CCS packs).\n"
            "  3. Solve hedge ratios using a constrained least-squares fit from instrument DV01 matrix to residual targets.\n"
            "  4. Re-check post-hedge sensitivity under parallel and curve-shape basis shocks.\n"
            "- Rule-of-thumb hedge ratio for a single bucket: `notional_hedge ~= residual_DV01 / instrument_DV01_per_notional`.\n"
            "- Keep a liquidity-adjusted penalty so hedge optimization prefers tight bid/ask tenors over theoretically perfect but "
            "illiquid points.\n"
        )

    def _warnings(self) -> str:
        return (
            "## 6) Warnings and model-risk controls\n"
            "- **Liquidity gaps:** basis tenors can be discontinuous; interpolated segments may look smooth but be untradeable.\n"
            "- **Stale quotes:** FX forwards can stale quickly; loader validation flags stale entries that should be excluded "
            "or down-weighted.\n"
            "- **Tenor mismatch risk:** pricing tenor grid may not align with hedge tenor grid, creating residual carry and "
            "re-hedging drag.\n"
            "- **Proxy risk:** when OIS/IBOR inputs are proxies, interpret absolute basis levels with caution and emphasize "
            "relative moves.\n"
        )

    def explain(self) -> str:
        """Return a structured markdown explainer ready for reports or notebooks."""

        header = (
            "# Cross-Currency Curve Explainer\n"
            f"Pair focus: **{self.base_pair}** | Collateral views: "
            f"**{self.domestic_collateral}** vs **{self.foreign_collateral}**\n"
        )
        return "\n\n".join(
            [
                header,
                self._conceptual_walkthrough(),
                self._market_inputs(),
                self._interpolation_and_edge_cases(),
                self._pricing_and_hedging_interpretation(),
                self._residual_usd_exposure(),
                self._warnings(),
            ]
        )
