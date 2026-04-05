# Guide 05 — Risk, Scenario Propagation, and Hedging Optimization

## Model purpose
The risk stack translates macro/factor shocks into trade-level and portfolio-level P&L, measures tail risk, and proposes constrained hedge overlays balancing variance reduction against carry/liquidity costs.

## Algorithm summary
- **Scenario propagation (`portfolio_shocks.py`):**
  - Applies tenor-bucketed rate/basis shocks and spot-FX shocks to instrument sensitivities (`dv01`, `basis01`, `fx_delta`).
  - Aggregates and decomposes P&L by instrument, factor bucket, and hedge overlay flags.
- **Hedging optimizer (`hedging_optimizer.py`):**
  - Solves a regularized quadratic objective for hedge notionals.
  - Includes penalties for transaction cost, carry drag, and liquidity usage.
  - Applies practical caps on notional and tenor concentration.
- **Tail risk (`tail_risk.py`):**
  - Computes parametric and historical VaR.
  - Computes expected shortfall (historical or parametric).
  - Produces marginal/component VaR/ES style decomposition outputs.

## Input schema expectations
- Portfolio representation: iterable of `Trade` dataclass entries with sensitivities and tenor bucket tags.
- Scenario object: `EMScenario` with maps for `rates_bp`, `basis_bp`, and `fx_pct`.
- Hedging optimizer arrays:
  - `exposure_vector` shape `(n_factors,)`,
  - `hedge_matrix` shape `(n_factors, n_instruments)`,
  - carry/liquidity vectors length `n_instruments`.
- Tail risk inputs:
  - return or P&L `pd.Series` for scalar VaR/ES,
  - `pd.DataFrame` for component decomposition with a designated total column.

## Output interpretation
- Scenario runs return trade-level P&L tables and grouped decomposition views for attribution reporting.
- Hedging optimizer returns a solution DataFrame per instrument (optimal notional, costs, constraint flags) plus objective metrics.
- Tail-risk utilities return scalar loss metrics and decomposition tables for risk committee explainability.

## Assumptions and limitations
- Revaluation is linear-in-sensitivity and does not include higher-order Greeks.
- Constraint enforcement in optimizer is pragmatic and may require extension for institution-grade mandate rules.
- Parametric VaR assumes approximately normal returns; historical VaR/ES assume representative sample history.
- Component attribution is linearized and should be treated as explanatory, not exact nonlinear allocation.

## Relevant source links
- `src/risk/portfolio_shocks.py`
- `src/risk/hedging_optimizer.py`
- `src/risk/tail_risk.py`
- `src/risk/scenarios/em_scenarios.py`
- `src/risk/factor_models.py`
- `src/risk/backtesting.py`

## Notebook walkthrough
- Primary workflow: `notebooks/hedging_and_stress_testing_workflow.ipynb`
- Supporting model context: `notebooks/huf_usd_end_to_end_calibration.ipynb`
