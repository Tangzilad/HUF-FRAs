# Guide 01 — Parametric Curves (Nelson-Siegel and Svensson)

## Model purpose
The parametric curve module fits smooth term structures to observed market yields while balancing fit quality against parameter stability. It provides production-friendly NS/Svensson estimators with optional quote-quality weighting.

## Algorithm summary
- Candidate models: `nelson_siegel` and `svensson`.
- Objective: weighted mean squared residual + L2 regularization term.
- Weighting options:
  - `uniform`: equal weight by tenor.
  - `bid_ask`: inverse bid-ask width (tighter quotes weighted more).
  - `liquidity`: direct liquidity-score weighting.
- Solver: `scipy.optimize.minimize` with `L-BFGS-B` bounds when SciPy is available.
- Fallback: returns initial bounded guess and objective score if SciPy is unavailable.

## Input schema expectations
- `tenors`: 1D numeric array in years (`np.ndarray`-compatible).
- `yields`: 1D numeric array with same length as `tenors`, in decimal rates.
- `model`: one of `"nelson_siegel" | "svensson"`.
- `weight_mode`: one of `"uniform" | "bid_ask" | "liquidity"`.
- `bid_ask` (optional): 1D array required when `weight_mode="bid_ask"`.
- `liquidity` (optional): 1D array required when `weight_mode="liquidity"`.
- `regularization_lambda`: small positive scalar controlling parameter shrinkage.

## Output interpretation
- `FitResult.params`: calibrated parameter vector in model-specific order.
- `FitResult.success`: optimizer convergence indicator (or `False` on SciPy fallback path).
- `FitResult.objective_value`: final weighted+regularized objective.
- `FitResult.curve(tenors)`: convenience evaluator for new tenor grids.

## Assumptions and limitations
- Bounds are hard-coded and represent practical priors; extreme regimes may need custom ranges.
- The objective is local-optimizer based and may be sensitive to starting values in stressed data.
- Weight vectors are not automatically normalized for outlier robustness beyond clipping safeguards.
- Smoothness is controlled implicitly via parametric form and L2 penalty, not via spline curvature penalties.

## Relevant source links
- Core implementation: `src/curves/parametric.py`
- Visualization support: `src/visualization/market_diagnostics.py`

## Notebook walkthrough
- Primary walkthrough: `notebooks/huf_usd_end_to_end_calibration.ipynb`
- Complementary diagnostics context: `notebooks/simulation_and_convexity_workflow.ipynb`
