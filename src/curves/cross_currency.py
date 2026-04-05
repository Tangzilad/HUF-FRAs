"""Cross-currency curve construction and calibration primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Mapping, Sequence, Tuple

import numpy as np


SUPPORTED_CURRENCIES = {"HUF", "USD", "EUR"}


@dataclass(frozen=True)
class CurveInstrumentSet:
    """Container for market quotes used by cross-currency bootstrapping/calibration."""

    ois_by_ccy: Dict[str, Dict[float, float]]
    irs_by_ccy: Dict[str, Dict[float, float]]
    fx_spot: Dict[str, float]
    fx_forwards: Dict[str, Dict[float, float]]
    xccy_basis_by_pair: Dict[str, Dict[float, float]]


@dataclass(frozen=True)
class CollateralSpec:
    collateral_ccy: Literal["HUF", "USD", "EUR"]

    def __post_init__(self) -> None:
        if self.collateral_ccy not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported collateral currency: {self.collateral_ccy}")


@dataclass
class CurveDiagnostics:
    rms_error: float
    max_tenor_error: float
    residuals: Dict[str, Dict[float, float]]


@dataclass
class CrossCurrencyCurveBundle:
    projection_curves: Dict[str, Dict[float, float]]
    discount_curves: Dict[str, Dict[float, float]]
    basis_term_structures: Dict[str, Dict[float, float]]
    diagnostics: CurveDiagnostics | None = None


@dataclass(frozen=True)
class InterpolationConfig:
    method: Literal["log_df", "zero_rate"] = "log_df"
    scheme: Literal["monotonic_cubic", "linear"] = "monotonic_cubic"


@dataclass
class CurveInterpolator:
    times: np.ndarray
    values: np.ndarray
    config: InterpolationConfig = field(default_factory=InterpolationConfig)

    def __post_init__(self) -> None:
        if len(self.times) != len(self.values):
            raise ValueError("times and values must have same length")
        order = np.argsort(self.times)
        self.times = np.asarray(self.times, dtype=float)[order]
        self.values = np.asarray(self.values, dtype=float)[order]
        if np.unique(self.times).size != self.times.size:
            raise ValueError("times must be unique")

    def _transform(self) -> np.ndarray:
        if self.config.method == "log_df":
            if np.any(self.values <= 0.0):
                raise ValueError("Discount factors must be positive for log-DF interpolation")
            return np.log(self.values)
        return -np.log(self.values) / np.maximum(self.times, 1e-12)

    def _inverse_transform(self, y: np.ndarray, t: np.ndarray) -> np.ndarray:
        if self.config.method == "log_df":
            return np.exp(y)
        return np.exp(-y * t)

    @staticmethod
    def _monotone_slopes(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        h = np.diff(x)
        delta = np.diff(y) / h
        n = len(x)
        m = np.zeros(n)
        m[0] = delta[0]
        m[-1] = delta[-1]
        for i in range(1, n - 1):
            if delta[i - 1] == 0.0 or delta[i] == 0.0 or np.sign(delta[i - 1]) != np.sign(delta[i]):
                m[i] = 0.0
            else:
                w1 = 2.0 * h[i] + h[i - 1]
                w2 = h[i] + 2.0 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
        return m

    @staticmethod
    def _cubic_eval(x: np.ndarray, y: np.ndarray, m: np.ndarray, xq: np.ndarray) -> np.ndarray:
        out = np.empty_like(xq)
        for j, q in enumerate(xq):
            if q <= x[0]:
                i = 0
            elif q >= x[-1]:
                i = len(x) - 2
            else:
                i = np.searchsorted(x, q) - 1
            h = x[i + 1] - x[i]
            s = (q - x[i]) / h
            h00 = (2 * s**3) - (3 * s**2) + 1
            h10 = (s**3) - (2 * s**2) + s
            h01 = (-2 * s**3) + (3 * s**2)
            h11 = (s**3) - (s**2)
            out[j] = h00 * y[i] + h10 * h * m[i] + h01 * y[i + 1] + h11 * h * m[i + 1]
        return out

    def evaluate(self, t: float | np.ndarray) -> float | np.ndarray:
        t_arr = np.atleast_1d(np.asarray(t, dtype=float))
        y = self._transform()
        if self.config.scheme == "linear" or len(self.times) < 3:
            interp = np.interp(t_arr, self.times, y)
        else:
            m = self._monotone_slopes(self.times, y)
            interp = self._cubic_eval(self.times, y, m, t_arr)
            if np.any(np.diff(interp) > 0.0) and self.config.method == "log_df":
                interp = np.interp(t_arr, self.times, y)
        out = self._inverse_transform(interp, t_arr)
        return float(out[0]) if np.isscalar(t) else out


def _bootstrap_df_from_rates(rate_by_tenor: Mapping[float, float]) -> Dict[float, float]:
    tenors = sorted(rate_by_tenor)
    dfs: Dict[float, float] = {}
    for t in tenors:
        r = rate_by_tenor[t]
        dfs[t] = 1.0 / (1.0 + r * t)
    return dfs


def build_projection_curve(ibor_by_tenor: Mapping[float, float]) -> Dict[float, float]:
    """Build simple-compounded projection curve from IBOR/term rates."""
    return _bootstrap_df_from_rates(ibor_by_tenor)


def build_discount_curve(ois_by_tenor: Mapping[float, float]) -> Dict[float, float]:
    """Build OIS discount curve under simple compounding approximation."""
    return _bootstrap_df_from_rates(ois_by_tenor)


def _pair_ccy(pair: str) -> Tuple[str, str]:
    dom, foreign = pair.split("/")
    return dom.upper(), foreign.upper()


def extract_fx_implied_basis(
    spot: float,
    forward_by_tenor: Mapping[float, float],
    domestic_df_curve: Mapping[float, float],
    foreign_ois_df_curve: Mapping[float, float],
) -> Dict[float, Dict[str, float]]:
    """Extract tenor-wise CIP implied foreign discount factors and basis residual."""
    out: Dict[float, Dict[str, float]] = {}
    for t, fwd in sorted(forward_by_tenor.items()):
        dom_df = domestic_df_curve[t]
        mkt_for_df = foreign_ois_df_curve[t]
        imp_for_df = spot * dom_df / fwd
        basis_residual = -(np.log(imp_for_df) - np.log(mkt_for_df)) / t
        out[t] = {
            "implied_foreign_df": imp_for_df,
            "market_foreign_df": mkt_for_df,
            "basis_residual": basis_residual,
        }
    return out


def _basis_from_nodes(times: Sequence[float], node_times: np.ndarray, node_basis: np.ndarray) -> np.ndarray:
    return np.interp(np.asarray(times, dtype=float), node_times, node_basis)


def _calibration_residual_vector(
    basis_nodes: np.ndarray,
    node_times: np.ndarray,
    pair: str,
    spot: float,
    forwards: Mapping[float, float],
    quoted_basis: Mapping[float, float],
    dom_df_curve: Mapping[float, float],
    for_df_curve: Mapping[float, float],
    smooth_weight: float,
) -> Tuple[np.ndarray, Dict[str, Dict[float, float]]]:
    fw_times = np.array(sorted(forwards))
    xccy_times = np.array(sorted(quoted_basis))
    basis_fw = _basis_from_nodes(fw_times, node_times, basis_nodes)
    basis_xc = _basis_from_nodes(xccy_times, node_times, basis_nodes)

    fw_res = []
    fw_detail = {}
    for i, t in enumerate(fw_times):
        adj_for_df = for_df_curve[t] * np.exp(-basis_fw[i] * t)
        model_fwd = spot * dom_df_curve[t] / adj_for_df
        err = model_fwd - forwards[t]
        fw_res.append(err)
        fw_detail[t] = err

    xc_res = []
    xc_detail = {}
    for i, t in enumerate(xccy_times):
        err = basis_xc[i] - quoted_basis[t]
        xc_res.append(err)
        xc_detail[t] = err

    smooth = np.diff(basis_nodes, n=2)
    residual = np.concatenate([np.asarray(fw_res), np.asarray(xc_res), smooth_weight * smooth])
    detail = {"fx_forward": fw_detail, f"xccy_{pair}": xc_detail}
    return residual, detail


def calibrate_xccy_basis_curve(
    pair: str,
    spot: float,
    forward_by_tenor: Mapping[float, float],
    quoted_basis_by_tenor: Mapping[float, float],
    domestic_discount_curve: Mapping[float, float],
    foreign_discount_curve: Mapping[float, float],
    smooth_weight: float = 1e-4,
    max_iter: int = 25,
) -> Tuple[Dict[float, float], CurveDiagnostics]:
    """Jointly calibrate basis to FX forwards + XCCY basis swap quotes."""
    node_times = np.array(sorted(set(forward_by_tenor) | set(quoted_basis_by_tenor)), dtype=float)
    basis_nodes = np.zeros_like(node_times)

    for _ in range(max_iter):
        res, _ = _calibration_residual_vector(
            basis_nodes,
            node_times,
            pair,
            spot,
            forward_by_tenor,
            quoted_basis_by_tenor,
            domestic_discount_curve,
            foreign_discount_curve,
            smooth_weight,
        )
        base_obj = float(np.dot(res, res))
        jac = np.zeros((res.size, basis_nodes.size))
        eps = 1e-6
        for j in range(basis_nodes.size):
            bumped = basis_nodes.copy()
            bumped[j] += eps
            res_b, _ = _calibration_residual_vector(
                bumped,
                node_times,
                pair,
                spot,
                forward_by_tenor,
                quoted_basis_by_tenor,
                domestic_discount_curve,
                foreign_discount_curve,
                smooth_weight,
            )
            jac[:, j] = (res_b - res) / eps
        lhs = jac.T @ jac + 1e-8 * np.eye(basis_nodes.size)
        rhs = jac.T @ res
        step = np.linalg.solve(lhs, rhs)
        trial = basis_nodes - step
        trial_res, _ = _calibration_residual_vector(
            trial,
            node_times,
            pair,
            spot,
            forward_by_tenor,
            quoted_basis_by_tenor,
            domestic_discount_curve,
            foreign_discount_curve,
            smooth_weight,
        )
        trial_obj = float(np.dot(trial_res, trial_res))
        basis_nodes = trial if trial_obj < base_obj else basis_nodes - 0.3 * step
        if np.linalg.norm(step) < 1e-9:
            break

    final_res, detail = _calibration_residual_vector(
        basis_nodes,
        node_times,
        pair,
        spot,
        forward_by_tenor,
        quoted_basis_by_tenor,
        domestic_discount_curve,
        foreign_discount_curve,
        smooth_weight,
    )
    diag = CurveDiagnostics(
        rms_error=float(np.sqrt(np.mean(final_res**2))),
        max_tenor_error=float(np.max(np.abs(final_res))),
        residuals=detail,
    )
    return {float(t): float(b) for t, b in zip(node_times, basis_nodes)}, diag


def discount_factor(
    curve_bundle: CrossCurrencyCurveBundle,
    ccy: str,
    t: float,
    collateral_ccy: str,
) -> float:
    ccy = ccy.upper()
    collateral_ccy = collateral_ccy.upper()
    if ccy not in curve_bundle.discount_curves:
        raise KeyError(f"Missing discount curve for currency {ccy}")

    base_curve = curve_bundle.discount_curves[ccy]
    base_df = float(np.interp(t, sorted(base_curve), [base_curve[x] for x in sorted(base_curve)]))
    if collateral_ccy == ccy:
        return base_df

    key = f"{ccy}-{collateral_ccy}"
    inv_key = f"{collateral_ccy}-{ccy}"
    if key in curve_bundle.basis_term_structures:
        basis_curve = curve_bundle.basis_term_structures[key]
        basis = float(np.interp(t, sorted(basis_curve), [basis_curve[x] for x in sorted(basis_curve)]))
        return base_df * np.exp(-basis * t)
    if inv_key in curve_bundle.basis_term_structures:
        basis_curve = curve_bundle.basis_term_structures[inv_key]
        basis = float(np.interp(t, sorted(basis_curve), [basis_curve[x] for x in sorted(basis_curve)]))
        return base_df * np.exp(basis * t)
    raise KeyError(f"No basis term structure found for {ccy}/{collateral_ccy}")


def calibrate_cross_currency_bundle(instruments: CurveInstrumentSet) -> CrossCurrencyCurveBundle:
    projection_curves = {ccy: build_projection_curve(quotes) for ccy, quotes in instruments.irs_by_ccy.items()}
    discount_curves = {ccy: build_discount_curve(quotes) for ccy, quotes in instruments.ois_by_ccy.items()}

    basis_term_structures: Dict[str, Dict[float, float]] = {}
    residuals: Dict[str, Dict[float, float]] = {}
    rms_values: List[float] = []
    max_values: List[float] = []

    for pair, forward_quotes in instruments.fx_forwards.items():
        dom, foreign = _pair_ccy(pair)
        quoted_basis = instruments.xccy_basis_by_pair.get(pair, {})
        basis_curve, diag = calibrate_xccy_basis_curve(
            pair=pair,
            spot=instruments.fx_spot[pair],
            forward_by_tenor=forward_quotes,
            quoted_basis_by_tenor=quoted_basis,
            domestic_discount_curve=discount_curves[dom],
            foreign_discount_curve=discount_curves[foreign],
        )
        basis_term_structures[f"{dom}-{foreign}"] = basis_curve
        residuals.update(diag.residuals)
        rms_values.append(diag.rms_error)
        max_values.append(diag.max_tenor_error)

    diagnostics = CurveDiagnostics(
        rms_error=float(np.mean(rms_values)) if rms_values else 0.0,
        max_tenor_error=float(np.max(max_values)) if max_values else 0.0,
        residuals=residuals,
    )
    return CrossCurrencyCurveBundle(
        projection_curves=projection_curves,
        discount_curves=discount_curves,
        basis_term_structures=basis_term_structures,
        diagnostics=diagnostics,
    )
