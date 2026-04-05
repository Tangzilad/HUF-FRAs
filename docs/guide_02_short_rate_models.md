# Guide 02 — Short-Rate Models (Ho-Lee, Hull-White 1F, FRA Analytics)

## Model purpose
This stack supports short-rate simulation, option-volatility calibration, and FRA/futures convexity analysis for pricing and risk diagnostics.

## Algorithm summary
- **Interface layer (`base.py`)**
  - Defines the common lifecycle: fit initial curve → calibrate to option market → simulate paths.
- **Ho-Lee (`ho_lee.py`)**
  - Reconstructs drift `theta(t)` from instantaneous forward curve gradients.
  - Supports constant or piecewise-constant volatility term structures.
  - Simulates with additive Gaussian increments.
- **Hull-White 1F (`hull_white.py`)**
  - Uses mean reversion parameter `a` and volatility `sigma` to derive model drift.
  - Supports constant and term-dependent volatility calibration.
  - Simulates Ornstein-Uhlenbeck-style dynamics in exact-discretization form per step.
- **Calibration helper (`calibration.py`)**
  - Multi-start bounded optimization wrapper with finite-difference Hessian proxy.
  - Returns approximate parameter uncertainty diagnostics and bootstrap objective variability.
- **FRA analytics (`fra.py`)**
  - Simulates FRA payoff distributions and convexity adjustments across tenor/volatility regimes.

## Input schema expectations
- Initial curve inputs are `pandas.DataFrame` objects with tenor/time and zero-rate information (prepared by `utils.py`).
- Option calibration markets require at least:
  - `expiry` (years, numeric)
  - `normal_vol` (decimal volatility)
- FRA simulation requires:
  - `start`, `end` tenors in years,
  - model implementing `ShortRateModel`,
  - curve DataFrame on consistent tenor grid.
- Calibration wrappers accept objective callables of shape `objective(params_dict, market_df) -> float`.

## Output interpretation
- Path generators return `SimulationResult(time_grid, short_rates)`.
- Option calibration returns dictionaries containing fitted parameters and RMSE diagnostics.
- Multi-start calibration returns `CalibrationReport` with:
  - `params`,
  - best `objective`,
  - `confidence_proxy` (stderr proxies + bootstrap objective std),
  - `starts` count.
- FRA analytics return pathwise P&L, forward rates, futures proxies, and summary quantiles.

## Assumptions and limitations
- Time discretization granularity materially affects path statistics and convexity estimates.
- Euler-like discretizations approximate continuous dynamics; very coarse grids can bias moments.
- Finite-difference Hessian confidence proxies are heuristic and may be unstable in flat objectives.
- If SciPy is unavailable, calibration can degrade to non-optimized fallback behavior.

## Relevant source links
- `src/models/short_rate/base.py`
- `src/models/short_rate/utils.py`
- `src/models/short_rate/ho_lee.py`
- `src/models/short_rate/hull_white.py`
- `src/models/short_rate/calibration.py`
- `src/models/short_rate/fra.py`

## Notebook walkthrough
- Primary workflow: `notebooks/short_rate_fra_workflow.ipynb`
- Simulation deep dive: `notebooks/simulation_and_convexity_workflow.ipynb`
