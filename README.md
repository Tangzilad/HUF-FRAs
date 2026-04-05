# HUF-FRAs

A compact toolkit for Hungarian forint (HUF) forward rate agreement analytics, cross-currency curve work, and stress-testing workflows.

## Project map
- [Guide 00: Project map](docs/guide_00_project_map.md)
- [Project guide and roadmap](docs/project_guide.md)
- [API quickstart](docs/api_quickstart.md)
- [Practitioner notes](docs/practitioner_notes.md)
- [Theory notes](docs/theory_notes.md)
- [CIP premium assumptions](docs/cip_premium_assumptions.md)

## Application launch and navigation

Launch the Streamlit interface from the repository root:

```bash
streamlit run app/app.py
```

Expected routed pages (exact order) and primary user inputs:

1. **Start here**: concise onboarding flow for traders, including recommended page order and interpretation guidance.
2. **CIP basis** *(parity)*: fast parity check using spot, forward points, tenor, and domestic/foreign OIS assumptions.
3. **Cross-currency** *(basis)*: residual-basis diagnostics to assess funding/basis dislocations and quote consistency.
4. **Short-rate FRA** *(model)*: FRA valuation and convexity analysis under static, Ho-Lee, and Hull-White model settings.
5. **Risk P&L** *(portfolio)*: scenario-propagated P&L decomposition, DV01 bucketing, and tail-risk views.
6. **Stress Lab** *(hedge)*: custom scenario shocks and hedge-optimization what-if analysis.

> Learning flow: `parity -> basis -> model -> portfolio -> hedge`.

> Rationale: Streamlit is used to consolidate previously notebook-scattered workflows into one cohesive interface while keeping domain logic modular in `src/*`.

## Notebooks (reference and validation, not primary UI)
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
