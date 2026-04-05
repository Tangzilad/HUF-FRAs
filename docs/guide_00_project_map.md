# Guide 00 — Project Map

This index links every core guide and source module so that navigation stays explicit and audit-friendly.

## Documentation guides
- [README](../README.md)
- [Project guide and roadmap](./project_guide.md)
- [API quickstart](./api_quickstart.md)
- [Practitioner notes](./practitioner_notes.md)
- [Theory notes](./theory_notes.md)
- [CIP premium assumptions](./cip_premium_assumptions.md)
- [Verification audit (2026-04-05)](./verification_audit_2026-04-05.md)

## App architecture and page-module map

```text
Streamlit app shell (`app/app.py`)
  -> shared state and widgets (session state, controls, upload/select inputs)
     -> page modules (start page, CIP basis, cross-currency diagnostics, FRA/short-rate valuation)
        -> analytics engines in `src/*`
```

Cross-links from routed app pages to underlying modules:

- **Start here**
  - [`app/pages/home.py`](../app/pages/home.py)
- **CIP basis**
  - [`src/analytics/cip_premium.py`](../src/analytics/cip_premium.py)
  - [`src/explainers/cip.py`](../src/explainers/cip.py)
- **Cross-currency**
  - [`src/curves/cross_currency.py`](../src/curves/cross_currency.py)
  - [`src/explainers/cross_currency.py`](../src/explainers/cross_currency.py)
- **Short-rate FRA page**
  - [`src/models/short_rate/calibration.py`](../src/models/short_rate/calibration.py)
  - [`src/models/short_rate/fra.py`](../src/models/short_rate/fra.py)
  - [`src/models/short_rate/ho_lee.py`](../src/models/short_rate/ho_lee.py)
  - [`src/models/short_rate/hull_white.py`](../src/models/short_rate/hull_white.py)
  - [`src/explainers/short_rate.py`](../src/explainers/short_rate.py)

> Note: `app/pages/risk_pnl.py` and `app/pages/stress_lab.py` exist but are not currently included in the routed navigation.

> Rationale note: Streamlit is used to unify previously notebook-scattered workflows into a single interface while preserving modular analytics code in `src/*`.

## Notebook workflows (reference and validation)
- [HUF-USD end-to-end calibration](../notebooks/huf_usd_end_to_end_calibration.ipynb) — parity check for calibration and CIP outputs.
- [Short-rate FRA workflow](../notebooks/short_rate_fra_workflow.ipynb) — validation notebook for FRA pricing/calibration behavior.
- [Simulation and convexity workflow](../notebooks/simulation_and_convexity_workflow.ipynb) — scenario and convexity validation reference.
- [Hedging and stress-testing workflow](../notebooks/hedging_and_stress_testing_workflow.ipynb) — stress/hedging output validation reference.

## Python package modules

### Top-level package
- [`src/__init__.py`](../src/__init__.py)

### Analytics
- [`src/analytics/__init__.py`](../src/analytics/__init__.py)
- [`src/analytics/cip_premium.py`](../src/analytics/cip_premium.py)

### Curves
- [`src/curves/__init__.py`](../src/curves/__init__.py)
- [`src/curves/parametric.py`](../src/curves/parametric.py)
- [`src/curves/cross_currency.py`](../src/curves/cross_currency.py)

### Data
- [`src/data/__init__.py`](../src/data/__init__.py)
- [`src/data/loaders/__init__.py`](../src/data/loaders/__init__.py)
- [`src/data/loaders/core.py`](../src/data/loaders/core.py)
- [`src/data/loaders/market_loaders.py`](../src/data/loaders/market_loaders.py)

### Models
- [`src/models/__init__.py`](../src/models/__init__.py)
- [`src/models/short_rate/__init__.py`](../src/models/short_rate/__init__.py)
- [`src/models/short_rate/base.py`](../src/models/short_rate/base.py)
- [`src/models/short_rate/calibration.py`](../src/models/short_rate/calibration.py)
- [`src/models/short_rate/fra.py`](../src/models/short_rate/fra.py)
- [`src/models/short_rate/ho_lee.py`](../src/models/short_rate/ho_lee.py)
- [`src/models/short_rate/hull_white.py`](../src/models/short_rate/hull_white.py)
- [`src/models/short_rate/utils.py`](../src/models/short_rate/utils.py)

### Risk
- [`src/risk/__init__.py`](../src/risk/__init__.py)
- [`src/risk/backtesting.py`](../src/risk/backtesting.py)
- [`src/risk/factor_models.py`](../src/risk/factor_models.py)
- [`src/risk/hedging_optimizer.py`](../src/risk/hedging_optimizer.py)
- [`src/risk/portfolio_shocks.py`](../src/risk/portfolio_shocks.py)
- [`src/risk/tail_risk.py`](../src/risk/tail_risk.py)
- [`src/risk/scenarios/em_scenarios.py`](../src/risk/scenarios/em_scenarios.py)

### Visualisation
- [`src/visualization/__init__.py`](../src/visualization/__init__.py)
- [`src/visualization/market_diagnostics.py`](../src/visualization/market_diagnostics.py)

## Command-line entrypoint
- [`fra_simulation.py`](../fra_simulation.py)

## Deliverables checklist
- Documentation entrypoint (`README.md`) present.
- Guide index (`docs/guide_00_project_map.md`) present.
- App architecture and page-to-module cross-links documented.
- Notebooks marked as reference/validation workflows rather than primary UI.
- All docs and notebook workflows linked from README and this map.
- All maintained source modules linked in this map.
- No orphan guide/module files in the tracked tree as of this update.
