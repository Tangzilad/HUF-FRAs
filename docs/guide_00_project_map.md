# Guide 00 — Project Map and Module Explainers

## Purpose
This guide provides a high-level map of the repository so new contributors can quickly find where model logic, data loading, analytics, and risk tooling live.

## Module map

### `src/data/`
- `loaders/core.py`: schema helpers and shared loading primitives.
- `loaders/market_loaders.py`: market snapshot ingestion and basic normalization.
- Use this layer whenever adding new input connectors or data cleaning rules.

### `src/curves/`
- `parametric.py`: Nelson-Siegel/Svensson fitting, weighting, and regularized objective.
- `cross_currency.py`: discount/projection curve construction, FX-implied basis extraction, and XCCY basis calibration.
- Use this layer for all curve generation and term-structure interpolation concerns.

### `src/models/short_rate/`
- `base.py`: abstract short-rate model interface and simulation result schema.
- `ho_lee.py`: Ho-Lee drift fitting, volatility calibration, and path simulation.
- `hull_white.py`: Hull-White 1F mean-reverting setup, calibration, and path simulation.
- `fra.py`: FRA distribution simulation and convexity adjustment summaries.
- `calibration.py`: multi-start calibration wrapper and confidence-proxy diagnostics.
- `utils.py`: curve preprocessing, forward extraction, and helper numerics.

### `src/analytics/`
- `cip_premium.py`: raw/purified CIP basis analytics, credit-liquidity adjustment curves, and term-premium decomposition.

### `src/risk/`
- `portfolio_shocks.py`: scenario propagation from factor shocks to trade-level P&L.
- `hedging_optimizer.py`: constrained quadratic hedge optimization under carry/liquidity penalties.
- `tail_risk.py`: VaR/ES and component-attribution utilities.
- `factor_models.py`, `backtesting.py`: model monitoring and risk-control support workflows.

### `src/visualization/`
- `market_diagnostics.py`: plotting-ready diagnostics for term structures and premium/basis monitoring.

## Algorithm map (quick reference)
- **Curve fitting:** weighted least squares + L2 regularization for NS/Svensson parameters.
- **Short-rate simulation:** Euler/OU discretization with deterministic drift reconstruction from initial curve.
- **Cross-currency basis:** iterative residual minimization against FX forwards and quoted XCCY basis nodes.
- **CIP analytics:** decomposition from raw FX-implied basis to purified basis and residual term premium.
- **Risk & hedging:** linearized shock propagation + quadratic objective with practical notional/concentration constraints.

## Input schema expectations (cross-module)
- Tenors are represented in **years** and should be numeric (`float`-compatible).
- Rates are stored as **decimal annualized yields** (`0.05 == 5%`) unless a field name explicitly includes `_bp`.
- Time-series panels are expected to use aligned `pandas` indexes when arithmetic combines multiple curves.
- Missing values should be handled upstream before calibration; downstream code assumes sufficiently clean arrays/frames.

## Output interpretation
- Curves are usually returned as tenor-to-value mappings, arrays, or DataFrames that can be consumed directly by notebooks.
- Calibration routines return fit status plus objective/diagnostic fields to support model risk review.
- Risk outputs are decomposition-friendly tables to support factor/instrument attribution and hedge explainability.

## Assumptions and limitations
- Most core numerics assume static snapshots (single-date curve fits) unless explicitly using rolling windows.
- Several optimizers use SciPy when available, with deterministic fallback behavior when SciPy is unavailable.
- Interpolation/extrapolation choices can materially influence long-end outputs; document any alternative scheme changes in PR notes.

## Notebook walkthrough links
- End-to-end calibration: `notebooks/huf_usd_end_to_end_calibration.ipynb`
- Short-rate/FRA workflow: `notebooks/short_rate_fra_workflow.ipynb`
- Simulation and convexity workflow: `notebooks/simulation_and_convexity_workflow.ipynb`
- Hedging and stress testing workflow: `notebooks/hedging_and_stress_testing_workflow.ipynb`

## Source links
- `src/data/loaders/core.py`
- `src/data/loaders/market_loaders.py`
- `src/curves/parametric.py`
- `src/curves/cross_currency.py`
- `src/models/short_rate/base.py`
- `src/models/short_rate/ho_lee.py`
- `src/models/short_rate/hull_white.py`
- `src/models/short_rate/fra.py`
- `src/models/short_rate/calibration.py`
- `src/analytics/cip_premium.py`
- `src/risk/portfolio_shocks.py`
- `src/risk/hedging_optimizer.py`
- `src/risk/tail_risk.py`
- `src/visualization/market_diagnostics.py`
