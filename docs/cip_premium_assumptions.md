# CIP Premium Analytics Assumptions

## Instrument conventions
- Spot/forward FX is quoted as **domestic currency per unit of foreign currency**.
- Forward-implied rates use **simple annual compounding** for covered parity mapping:
  \(r_{dom} = (((F/S)(1+r_{for}T))-1)/T\).
- Input rates in analytics code are decimal yields (e.g., 0.05 = 5%).
- CDS and treasury-OIS inputs are in basis points and converted to decimals only when combining into yield components.

## Interpolation choices
- Curves are linearly interpolated by tenor in year space.
- Extrapolation at edges is clamped to endpoint values (behavior of `numpy.interp`).
- Missing nodes are dropped before interpolation; if all nodes are missing the loader will fail upstream and should be handled by caller.

## Proxy hierarchy when data is sparse
1. **Primary:** tenor-matched supranational proxy curve.
2. **Secondary:** nearest-tenor linear interpolation within available supranational tenors.
3. **Fallback:** sovereign-tenor proxy with explicit credit/liquidity add-on via CDS + treasury-OIS adjustment curve.
4. **Last resort:** previous-day carried forward proxy for rolling workflows.

## Decomposition identity
Observed local yields are decomposed as:

\[
\text{observed} = \text{risk free} + \text{credit/liquidity} + \text{residual term premium}
\]

The identity is enforced exactly in tests and should hold up to floating-point precision.

## Purified vs raw CIP interpretation
- **Raw basis** includes local sovereign credit/liquidity contamination.
- **Purified basis** removes cross-country local credit differential computed from sovereign minus supranational spreads.
- During funding stress, purified basis is expected to be less extreme than raw basis when local credit widening dominates.
