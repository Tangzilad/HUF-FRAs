# Theory Notes

## Cross-currency HJM intuition
A practical cross-currency HJM implementation combines domestic and foreign instantaneous forward dynamics with a basis drift adjustment that keeps discounted FX-converted bond prices arbitrage-free. In this project, the abstraction is operationalized through observable curve objects (discount/projection/basis) rather than full state-vector simulation.

## Basis calibration
Basis is backed out by fitting model-implied instrument prices to market quotes across IRS, FX forwards, and basis swaps. The parametric curve module supports smooth basis surface constraints through regularization and bounded parameters.

## CIP decomposition
CIP deviations are decomposed as:

- funding frictions,
- balance-sheet costs,
- collateral currency effects,
- residual market microstructure noise.

The diagnostics module focuses on tenor/time signatures, helping distinguish temporary dislocations from structural premia.

## Term-premium framework
Long-end yields are split into expected path + term premium. The panel tools support this decomposition for scenario analysis and relative-value narratives.
