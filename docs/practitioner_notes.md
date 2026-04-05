# Practitioner Notes

## Assumptions
- Quotes are mapped to a unified schema (`timestamp`, `tenor`, `quote_type`, source metadata).
- Staleness thresholds are product-specific and applied at ingestion time.
- Units are normalized (`percent`, `points`, `bps`) to avoid cross-feed interpretation errors.

## Limitations
- Current parametric fitting is static-in-time (single cross-section calibration).
- Weighting relies on available bid-ask/liquidity proxies; sparse metadata weakens robustness.
- Notebook workflows are tutorial templates, not production orchestration pipelines.

## Data caveats
- Missing tenors trigger hard validation failure.
- Stale quotes are flagged for downstream filtering (not auto-dropped).
- Unit mismatches raise validation exceptions.

## Interpretation guidance
Use CIP and basis panels jointly: isolated short-end spikes often indicate microstructure stress, while broad persistent shifts more likely indicate systemic funding/balance-sheet pressure.
