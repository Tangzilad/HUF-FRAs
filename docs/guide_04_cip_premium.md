# Guide 04 — CIP Premium Analytics

## Model purpose
This module quantifies covered interest parity deviations, strips local credit contamination via supranational proxies, and decomposes local yields into risk-free, credit/liquidity, and residual term-premium components.

## Algorithm summary
- **Layer 1 (raw CIP):**
  - Computes FX-implied domestic rates from spot/forward/foreign rates.
  - Forms raw basis in basis points vs domestic OIS benchmark.
- **Layer 2 (purified CIP):**
  - Computes local credit spreads as sovereign minus supranational curves.
  - Subtracts domestic-vs-foreign credit differential (bp) from raw basis.
- **Layer 3 (decomposition + term premium):**
  - Builds credit/liquidity adjustment curves from CDS and treasury-OIS spreads.
  - Enforces decomposition identity:
    `observed = risk_free + credit_liquidity + residual_term_premium`.
  - Provides rolling-window factor-regression interface for term-premium tracking.

## Input schema expectations
- Spot FX: `pd.Series` indexed by date (domestic-per-foreign convention).
- Forwards and benchmark curves: tenor-column `pd.DataFrame` objects with aligned dates and tenors in years.
- Sovereign/supranational inputs for purification: aligned DataFrames in decimal rates.
- CDS and treasury-OIS spreads:
  - DataFrames with tenor columns (`tenor_years`) and spread columns in bp.
- Factor-model estimation:
  - `X`: predictor DataFrame,
  - `y`: target Series,
  - both index-aligned with sufficient history for chosen rolling window.

## Output interpretation
- Raw and purified functions return MultiIndex-column DataFrames suitable for point-in-time snapshots and panel visualization.
- Mapping and adjustment builders output tenor-indexed Series (decimal rates for adjustment curves).
- Decomposition returns component-level DataFrame with explicit residual term premium.
- Rolling model returns coefficient time series and out-of-sample tracking errors.

## Assumptions and limitations
- Formulae use simple annual compounding in the covered parity mapping.
- Interpolation uses linear tenor mapping; endpoint behavior follows `numpy.interp` clamping.
- Purification quality depends on proxy curve representativeness and data alignment quality.
- Rolling OLS diagnostics are explanatory rather than structural causal estimates.

## Relevant source links
- `src/analytics/cip_premium.py`
- `docs/cip_premium_assumptions.md`
- `src/curves/cross_currency.py`

## Notebook walkthrough
- Primary end-to-end context: `notebooks/huf_usd_end_to_end_calibration.ipynb`
- Risk integration context: `notebooks/hedging_and_stress_testing_workflow.ipynb`
