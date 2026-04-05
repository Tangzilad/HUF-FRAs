# Guide 03 — Cross-Currency Curves and Basis Calibration

## Model purpose
The cross-currency module constructs projection/discount curves and calibrates tenor-dependent XCCY basis structures using FX forwards and quoted basis swap nodes.

## Algorithm summary
- Builds simple-compounded discount factors from rate-by-tenor maps for projection and OIS discount curves.
- Extracts FX-implied foreign discount factors and basis residuals from spot/forward relations.
- Calibrates a smooth basis node curve by minimizing a combined residual vector:
  - FX forward mispricing residuals,
  - XCCY quote fitting residuals,
  - second-difference smoothness penalty.
- Uses custom iterative updates and Jacobian approximations to reduce squared residual objective.
- Includes interpolation helpers (`CurveInterpolator`) with linear or monotone-cubic schemes in transformed space.

## Input schema expectations
- Currency pair naming convention: `"DOM/FOR"` (e.g., `"HUF/USD"`).
- Spot and forward quotes:
  - `spot`: scalar FX level,
  - `forward_by_tenor`: mapping `{tenor_years: forward_level}`.
- Curves:
  - `domestic_discount_curve`, `foreign_discount_curve`: mappings `{tenor_years: discount_factor}`.
- Quoted basis nodes:
  - `quoted_basis_by_tenor`: mapping `{tenor_years: basis_decimal}` with tenor overlap preferred.
- Interpolator inputs require unique tenor points and positive values when using log-DF mode.

## Output interpretation
- Basis calibration returns:
  - tenor-to-basis map for calibrated nodes,
  - `CurveDiagnostics` containing RMS error, max tenor error, and residual detail by instrument type.
- Extraction helpers return per-tenor dictionaries including implied/market foreign discount factors and residual basis.
- Curve bundle/data classes standardize calibrated outputs for downstream analytics.

## Assumptions and limitations
- Discount bootstrapping uses simple-compounding approximations, not full coupon-bootstrapped conventions.
- Calibration quality depends on tenor coverage overlap across forwards, OIS curves, and XCCY quotes.
- Smoothness weight materially impacts front-end fit vs long-end stability trade-off.
- Interpolation fallback behavior can switch to linear if monotone-cubic constraints are violated in transformed space.

## Relevant source links
- `src/curves/cross_currency.py`
- `src/data/loaders/market_loaders.py`
- `src/visualization/market_diagnostics.py`

## Notebook walkthrough
- End-to-end calibration context: `notebooks/huf_usd_end_to_end_calibration.ipynb`
- Stress/risk linkage: `notebooks/hedging_and_stress_testing_workflow.ipynb`
