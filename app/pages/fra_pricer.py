from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from app.calculation_windows import render_equation_window
from src.models.short_rate.calibration import calibrate_with_multistart
from src.models.short_rate.fra import simulate_fra_distribution
from src.models.short_rate.ho_lee import HoLeeModel
from src.models.short_rate.hull_white import HullWhite1FModel

Direction = Literal["Pay fixed", "Receive fixed"]
ModelName = Literal["Ho-Lee", "Hull-White 1F"]


@dataclass(frozen=True)
class FRAInstrument:
    start: float
    end: float
    contract_rate: float
    notional: float
    direction: Direction
    day_count: str = "ACT/360"
    payment_lag_days: int = 2

    @property
    def tau(self) -> float:
        return self.end - self.start

    @property
    def sign(self) -> float:
        return 1.0 if self.direction == "Receive fixed" else -1.0


def _default_curve() -> pd.DataFrame:
    tenors = np.array([0.25, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0], dtype=float)
    zero = np.array([0.062, 0.063, 0.064, 0.0645, 0.065, 0.0655, 0.066, 0.0665], dtype=float)
    return pd.DataFrame({"t": tenors, "zero_rate": zero})


def _discount(curve: pd.DataFrame, t: float) -> float:
    r = float(np.interp(t, curve["t"], curve["zero_rate"]))
    return float(np.exp(-r * t))


def _implied_forward(curve: pd.DataFrame, start: float, end: float) -> float:
    tau = max(end - start, 1e-10)
    p1 = _discount(curve, start)
    p2 = _discount(curve, end)
    return (p1 / p2 - 1.0) / tau


def _fra_pv(curve: pd.DataFrame, fra: FRAInstrument) -> float:
    fwd = _implied_forward(curve, fra.start, fra.end)
    return fra.sign * fra.notional * fra.tau * (fwd - fra.contract_rate) * _discount(curve, fra.end)


def _calibration_market(curve: pd.DataFrame) -> pd.DataFrame:
    expiries = np.array([0.25, 0.5, 1.0, 1.5, 2.0], dtype=float)
    forwards = np.array([_implied_forward(curve, t, t + 0.25) for t in expiries], dtype=float)
    normal_vol = 0.01 + 0.002 * np.exp(-0.5 * expiries)
    return pd.DataFrame({"expiry": expiries, "forward": forwards, "normal_vol": normal_vol})


def _calibrate_model(model_name: ModelName, curve: pd.DataFrame, market: pd.DataFrame):
    if model_name == "Ho-Lee":

        def objective(params: dict[str, float], market_data: pd.DataFrame) -> float:
            model = HoLeeModel(sigma=params["sigma"])
            model.calibrate_to_options(market_data)
            model_vol = np.full(len(market_data), model.sigma)
            err = model_vol - market_data["normal_vol"].to_numpy(float)
            return float(np.mean(err**2))

        report = calibrate_with_multistart(
            objective=objective,
            market=market,
            initial_guess={"sigma": 0.01},
            bounds={"sigma": (1e-4, 0.10)},
            n_starts=10,
            bootstrap_samples=64,
        )
        model = HoLeeModel(sigma=report.params["sigma"])
    else:

        def objective(params: dict[str, float], market_data: pd.DataFrame) -> float:
            model = HullWhite1FModel(a=params["a"], sigma=params["sigma"])
            out = model.calibrate_to_options(market_data, a0=params["a"], sigma0=params["sigma"])
            return float(out["rmse"] ** 2)

        report = calibrate_with_multistart(
            objective=objective,
            market=market,
            initial_guess={"a": 0.15, "sigma": 0.01},
            bounds={"a": (0.01, 1.50), "sigma": (1e-4, 0.10)},
            n_starts=12,
            bootstrap_samples=64,
        )
        model = HullWhite1FModel(a=report.params["a"], sigma=report.params["sigma"])

    model.fit_initial_curve(curve)
    return model, report


def _risk_metrics(curve: pd.DataFrame, fra: FRAInstrument) -> dict[str, float]:
    base = _fra_pv(curve, fra)

    bumped_up = curve.copy()
    bumped_dn = curve.copy()
    bumped_up["zero_rate"] += 1e-4
    bumped_dn["zero_rate"] -= 1e-4

    pv_up = _fra_pv(bumped_up, fra)
    pv_dn = _fra_pv(bumped_dn, fra)
    dv01 = (pv_dn - pv_up) / 2.0
    gamma_1bp = pv_up - 2.0 * base + pv_dn

    return {"dv01": dv01, "gamma_1bp": gamma_1bp}


def _carry_roll(curve: pd.DataFrame, fra: FRAInstrument, horizon: float = 1.0 / 12.0) -> tuple[float, float]:
    base_pv = _fra_pv(curve, fra)

    if fra.start <= horizon:
        return 0.0, 0.0

    rolled = FRAInstrument(
        start=fra.start - horizon,
        end=fra.end - horizon,
        contract_rate=fra.contract_rate,
        notional=fra.notional,
        direction=fra.direction,
        day_count=fra.day_count,
        payment_lag_days=fra.payment_lag_days,
    )
    rolled_pv = _fra_pv(curve, rolled)
    roll_down = rolled_pv - base_pv

    implied = _implied_forward(curve, fra.start, fra.end)
    carry = fra.sign * fra.notional * fra.tau * (implied - fra.contract_rate) * horizon
    return carry, roll_down


def _valuation_summary(model_name: ModelName, curve: pd.DataFrame, fra: FRAInstrument, n_paths: int, seed: int) -> dict[str, float]:
    market = _calibration_market(curve)
    model, report = _calibrate_model(model_name, curve, market)

    sim = simulate_fra_distribution(
        model=model,
        curve=curve,
        start=fra.start,
        end=fra.end,
        n_paths=n_paths,
        seed=seed,
        notional=fra.notional * fra.sign,
    )

    implied_forward = _implied_forward(curve, fra.start, fra.end)
    model_forward = float(np.mean(sim.fra_forward))
    convexity_adj = float(np.mean(sim.futures_rate) - np.mean(sim.fra_forward))
    pv = _fra_pv(curve, fra)
    carry, roll_down = _carry_roll(curve, fra)
    risk = _risk_metrics(curve, fra)

    out = {
        "contract_rate": fra.contract_rate,
        "implied_forward": implied_forward,
        "model_forward": model_forward,
        "pv": pv,
        "carry": carry,
        "roll_down": roll_down,
        "convexity_adjustment": convexity_adj,
        "dv01": risk["dv01"],
        "gamma_1bp": risk["gamma_1bp"],
        "calib_objective": report.objective,
    }

    if model_name == "Ho-Lee":
        out["sigma"] = float(report.params["sigma"])
    else:
        out["a"] = float(report.params["a"])
        out["sigma"] = float(report.params["sigma"])

    return out


def _render_streamlit() -> None:
    st = __import__("streamlit")

    st.set_page_config(page_title="FRA Pricer", layout="wide")
    st.title("FRA Pricer (Short-Rate Models)")

    col1, col2, col3 = st.columns([1.2, 1.2, 1.6])
    with col1:
        model_name = st.selectbox("Model", ["Ho-Lee", "Hull-White 1F"])
        direction = st.selectbox("Direction", ["Pay fixed", "Receive fixed"])
        notional = st.number_input("Notional", min_value=100_000.0, value=10_000_000.0, step=100_000.0)
    with col2:
        tenor = st.selectbox("Tenor", ["3x6", "6x9", "9x12", "12x15"], index=1)
        contract_rate = st.number_input("Contract rate", min_value=-0.05, max_value=0.30, value=0.065, step=0.0005, format="%.4f")
        n_paths = st.slider("Simulation paths", min_value=2_000, max_value=50_000, value=15_000, step=1_000)
    with col3:
        seed = st.number_input("Random seed", min_value=0, max_value=9_999_999, value=42, step=1)

    t1, t2 = tenor.split("x")
    fra = FRAInstrument(
        start=float(t1) / 12.0,
        end=float(t2) / 12.0,
        contract_rate=float(contract_rate),
        notional=float(notional),
        direction=direction,
    )
    curve = _default_curve()

    if st.button("Price FRA", type="primary"):
        results = _valuation_summary(model_name=model_name, curve=curve, fra=fra, n_paths=int(n_paths), seed=int(seed))

        st.subheader("Compact Trade Summary")
        summary = pd.DataFrame(
            [
                {
                    "tenor": tenor,
                    "direction": fra.direction,
                    "notional": f"{fra.notional:,.0f}",
                    "day_count": fra.day_count,
                    "payment_lag_days": fra.payment_lag_days,
                }
            ]
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)

        st.subheader("Key Outputs")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Contract rate", f"{results['contract_rate']:.4%}")
        m2.metric("Implied forward", f"{results['implied_forward']:.4%}")
        m3.metric("PV", f"{results['pv']:,.0f}")
        m4.metric("Convexity adjustment", f"{results['convexity_adjustment']*1e4:.2f} bps")

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Carry (1M)", f"{results['carry']:,.0f}")
        p2.metric("Roll-down (1M)", f"{results['roll_down']:,.0f}")
        p3.metric("DV01", f"{results['dv01']:,.2f}")
        p4.metric("Gamma (1bp)", f"{results['gamma_1bp']:,.2f}")
        render_equation_window(
            title="How FRA pricing and risk metrics are calculated",
            equations=[
                r"F(t_1,t_2)=\frac{P(0,t_1)/P(0,t_2)-1}{\tau}",
                r"PV = s \times N \times \tau \times (F-K)\times P(0,t_2)",
                r"DV01 \approx \frac{PV(r-1bp)-PV(r+1bp)}{2}",
                r"\Gamma_{1bp}=PV(r+1bp)-2PV(r)+PV(r-1bp)",
            ],
            notes=[
                f"s (direction sign) = {fra.sign:.1f}, N = {fra.notional:,.0f}, τ = {fra.tau:.6f}",
                f"Model-implied forward = {results['model_forward']:.6%}, contract rate K = {results['contract_rate']:.6%}",
                f"PV = {results['pv']:,.2f}, DV01 = {results['dv01']:,.4f}, Gamma(1bp) = {results['gamma_1bp']:,.4f}",
            ],
        )

        calib_cols = ["sigma", "a", "calib_objective"]
        calib_display = {k: v for k, v in results.items() if k in calib_cols}
        if calib_display:
            st.caption("Calibration snapshot")
            st.json(calib_display)


if __name__ == "__main__":
    _render_streamlit()
