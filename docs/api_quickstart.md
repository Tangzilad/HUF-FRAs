# API Quickstart

## Data ingestion (`src/data/loaders/`)
```python
from src.data.loaders import load_fx_forwards
quotes = load_fx_forwards("data/fx_forwards.csv", required_tenors=["1M", "3M", "6M", "12M"])
frame = quotes.to_frame()
```

## Parametric curves (`src/curves/parametric.py`)
```python
from src.curves.parametric import fit_parametric_curve
result = fit_parametric_curve(tenors, yields, model="svensson", weight_mode="liquidity", liquidity=liq)
fitted = result.curve(tenors)
```

## Market diagnostics (`src/visualization/market_diagnostics.py`)
```python
from src.visualization.market_diagnostics import plot_fitted_vs_observed
plot_fitted_vs_observed(tenors, observed, fitted, "artifacts/fitted_vs_observed.png")
```
