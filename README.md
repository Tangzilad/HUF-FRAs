# HUF FRA Analytics Toolkit

A research and production-oriented toolkit for HUF/USD FRA analysis, curve calibration,
short-rate simulation, and risk diagnostics.

## Learning & Explanation Layer

The repository includes an explanation workflow to turn model outputs into concise,
interpretable summaries for researchers, quants, and risk stakeholders.

### Quick start: `scripts/explain.py`

Run from repository root:

```bash
python scripts/explain.py --help
```

```bash
python scripts/explain.py \
  --input notebooks/huf_usd_end_to_end_calibration.ipynb \
  --mode summary
```

```bash
python scripts/explain.py \
  --input docs/project_guide.md \
  --mode teaching \
  --audience junior-quant
```

### Learning resources

- Guide: [Learning layer overview](docs/guide_learning_layer.md)
- Guide: [Explainers module reference](docs/guide_explainers.md)
- Notebook: [HUF/USD end-to-end calibration](notebooks/huf_usd_end_to_end_calibration.ipynb)
- Notebook: [Simulation and convexity workflow](notebooks/simulation_and_convexity_workflow.ipynb)
- Notebook: [Short-rate FRA workflow](notebooks/short_rate_fra_workflow.ipynb)
- Notebook: [Hedging and stress-testing workflow](notebooks/hedging_and_stress_testing_workflow.ipynb)

## Core project docs

- [Project guide and roadmap](docs/project_guide.md)
- [API quickstart](docs/api_quickstart.md)
- [Theory notes](docs/theory_notes.md)
- [Practitioner notes](docs/practitioner_notes.md)
