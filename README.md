# HUF-FRAs

A compact toolkit for Hungarian forint (HUF) forward rate agreement analytics, cross-currency curve work, and stress-testing workflows.

## Project map
- [Guide 00: Project map](docs/guide_00_project_map.md)
- [Project guide and roadmap](docs/project_guide.md)
- [API quickstart](docs/api_quickstart.md)
- [Practitioner notes](docs/practitioner_notes.md)
- [Theory notes](docs/theory_notes.md)
- [CIP premium assumptions](docs/cip_premium_assumptions.md)

## Notebooks
- [HUF-USD end-to-end calibration](notebooks/huf_usd_end_to_end_calibration.ipynb)
- [Short-rate FRA workflow](notebooks/short_rate_fra_workflow.ipynb)
- [Simulation and convexity workflow](notebooks/simulation_and_convexity_workflow.ipynb)
- [Hedging and stress-testing workflow](notebooks/hedging_and_stress_testing_workflow.ipynb)

## Package layout
- `src/analytics`: CIP premium analytics and yield decomposition.
- `src/curves`: Parametric and cross-currency curve calibration utilities.
- `src/data`: Market data loaders and validation.
- `src/models`: Short-rate and FRA pricing models.
- `src/risk`: Scenario propagation, optimisation, and tail metrics.
- `src/visualization`: Diagnostics plots.

## Assumptions and limitations
- The code base is educational and research-oriented, not production trading infrastructure.
- Numerical outputs depend on conventions documented in `docs/cip_premium_assumptions.md`.
- Some workflows require optional scientific plotting dependencies.
