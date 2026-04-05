"""Usage example: market quotes -> calibrated bundle -> collateralized PV comparison."""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.curves.cross_currency import (
    CurveInstrumentSet,
    calibrate_cross_currency_bundle,
    discount_factor,
)


def main() -> None:
    tenors = [0.25, 0.5, 1.0, 2.0, 3.0]
    ois_huf = {t: 0.07 - 0.002 * t for t in tenors}
    ois_usd = {t: 0.05 - 0.0015 * t for t in tenors}
    ois_eur = {t: 0.03 - 0.001 * t for t in tenors}

    spot = 360.0
    true_basis = {t: 0.0010 + 0.0003 * t for t in tenors}
    dom_df = {t: 1.0 / (1.0 + ois_huf[t] * t) for t in tenors}
    for_df = {t: 1.0 / (1.0 + ois_usd[t] * t) for t in tenors}
    fx_forwards = {t: spot * dom_df[t] / (for_df[t] * (2.718281828 ** (-true_basis[t] * t))) for t in tenors}

    instruments = CurveInstrumentSet(
        ois_by_ccy={"HUF": ois_huf, "USD": ois_usd, "EUR": ois_eur},
        irs_by_ccy={"HUF": ois_huf, "USD": ois_usd, "EUR": ois_eur},
        fx_spot={"HUF/USD": spot},
        fx_forwards={"HUF/USD": fx_forwards},
        xccy_basis_by_pair={"HUF/USD": true_basis},
    )

    bundle = calibrate_cross_currency_bundle(instruments)
    bundle.basis_term_structures["HUF-EUR"] = {t: -0.0008 for t in tenors}

    maturity = 2.0
    cashflow_huf = 100_000_000.0
    for coll in ["HUF", "USD", "EUR"]:
        df = discount_factor(bundle, "HUF", maturity, coll)
        pv = cashflow_huf * df
        print(f"HUF cashflow PV under {coll} collateral: {pv:,.2f} (DF={df:.6f})")

    if bundle.diagnostics:
        print(f"Calibration RMS error: {bundle.diagnostics.rms_error:.8f}")
        print(f"Calibration max tenor error: {bundle.diagnostics.max_tenor_error:.8f}")


if __name__ == "__main__":
    main()
