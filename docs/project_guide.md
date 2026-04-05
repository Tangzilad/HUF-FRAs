# Project Guide and Roadmap

## Module map

- `src/data/loaders/`: Market data ingestion utilities and schema normalization helpers.
- `src/curves/`: Parametric and cross-currency curve construction modules.
- `src/analytics/`: Pricing analytics including CIP premium decomposition.
- `src/models/short_rate/`: Short-rate model base types, calibration routines, and FRA simulation tools.
- `src/risk/`: Scenario, factor, tail-risk, backtesting, and hedging optimization engines.
- `src/visualization/`: Market diagnostic charting and reporting plots.
- `src/explainers/`: Human-readable interpretation layer for calibration and risk outputs.

### Explainer classes (`src/explainers/`)

- `CurveFitExplainer`: Interprets calibration residuals, parameter shapes, and fit stability signals.
- `RiskScenarioExplainer`: Converts shock outputs into concise PnL/risk-factor impact narratives.
- `PolicyNarrativeExplainer`: Expresses model conclusions in macro-policy language for broad audiences.

## Milestones

### M1 — Data ingestion foundation
- **Dependencies:** Source CSV/feeds for bond yields, FX forwards, swap spreads, CDS.
- **Estimated effort:** 2-3 days.
- **Acceptance criteria:** Unified schema + validation checks for missing tenors, stale quotes, units.

### M2 — Parametric curve fitting
- **Dependencies:** Clean cross-sectional market snapshots.
- **Estimated effort:** 3-4 days.
- **Acceptance criteria:** Nelson-Siegel and Svensson estimators with weighted objective, bounds, regularization.

### M3 — Diagnostics and plotting
- **Dependencies:** Calibrated curve outputs and CIP/basis datasets.
- **Estimated effort:** 2 days.
- **Acceptance criteria:** Export-ready plots for curve fit, CIP deviations, basis + term premium panel.

### M4 — Notebook playbooks
- **Dependencies:** Stable APIs from ingestion/fitting/diagnostics.
- **Estimated effort:** 2 days.
- **Acceptance criteria:** Reusable notebooks for calibration, convexity simulation, hedging stress test.

### M5 — Regression checks
- **Dependencies:** Example datasets and deterministic plotting routines.
- **Estimated effort:** 1-2 days.
- **Acceptance criteria:** Notebook integrity smoke checks + plot generation consistency checks.

## Choose-your-path progression

### Calibration-first
1. Start with ingestion validators.
2. Fit NS/Svensson curves.
3. Add diagnostic plots.

### Risk-first
1. Use notebooks to stand up stress-test logic.
2. Integrate fitted curves for shock propagation.
3. Add basis/CIP monitoring overlays.

### Research-first
1. Read theory + practitioner notes.
2. Prototype alternative weighting/regularization ideas.
3. Contribute new diagnostics or decomposition experiments.
