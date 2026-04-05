from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd


@dataclass
class PCAPreprocessConfig:
    """Configuration for mixed-frequency macro preprocessing."""

    target_freq: str = "D"
    standardize: bool = True
    winsorize_std: Optional[float] = 5.0


DEFAULT_MACRO_COLUMNS = {
    "inflation_expectation": "level",
    "fx_level": "log_return",
    "fx_vol": "level",
    "risk_off_indicator": "diff",
}


def _to_datetime_index(frame: pd.DataFrame, index_col: str = "date") -> pd.DataFrame:
    df = frame.copy()
    if index_col in df.columns:
        df[index_col] = pd.to_datetime(df[index_col], errors="coerce")
        df = df.set_index(index_col)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Data must include a DatetimeIndex or a 'date' column.")
    if df.index.hasnans:
        raise ValueError("Datetime index contains invalid timestamps.")
    return df.sort_index()


def _standardize(series: pd.Series, winsorize_std: Optional[float] = 5.0) -> pd.Series:
    out = series.copy()
    mu = out.mean()
    sigma = out.std(ddof=0)
    if np.isclose(sigma, 0.0) or np.isnan(sigma):
        return out * 0.0
    z = (out - mu) / sigma
    if winsorize_std is not None:
        z = z.clip(-winsorize_std, winsorize_std)
    return z


def mixed_frequency_preprocess(
    rates_df: pd.DataFrame,
    macro_df: pd.DataFrame,
    macro_transform_map: Optional[Dict[str, str]] = None,
    config: PCAPreprocessConfig = PCAPreprocessConfig(),
) -> pd.DataFrame:
    """Align mixed-frequency rates + macro data to one sampling frequency.

    Supported transform values:
    - level
    - diff
    - pct_change
    - log_return
    """

    transform_map = dict(DEFAULT_MACRO_COLUMNS)
    if macro_transform_map:
        transform_map.update(macro_transform_map)

    rates = _to_datetime_index(rates_df)
    macro = _to_datetime_index(macro_df)

    rates_aligned = rates.resample(config.target_freq).last().interpolate(limit_direction="both")
    macro_aligned = macro.resample(config.target_freq).last().ffill().bfill()

    transformed = {}
    for col in macro_aligned.columns:
        method = transform_map.get(col, "level")
        s = macro_aligned[col].astype(float)
        if method == "level":
            t = s
        elif method == "diff":
            t = s.diff()
        elif method == "pct_change":
            t = s.pct_change()
        elif method == "log_return":
            t = np.log(s).diff()
        else:
            raise ValueError(f"Unsupported transform method: {method}")
        transformed[col] = t
    macro_transformed = pd.DataFrame(transformed, index=macro_aligned.index)

    merged = rates_aligned.join(macro_transformed, how="inner").dropna(how="any")
    if config.standardize:
        merged = merged.apply(lambda s: _standardize(s, config.winsorize_std), axis=0)
    return merged


def prepare_pca_inputs(
    rate_factor_df: pd.DataFrame,
    macro_df: pd.DataFrame,
    macro_transform_map: Optional[Dict[str, str]] = None,
    config: PCAPreprocessConfig = PCAPreprocessConfig(),
) -> pd.DataFrame:
    """Build PCA-ready matrix with rates + EM macro variables."""

    return mixed_frequency_preprocess(
        rates_df=rate_factor_df,
        macro_df=macro_df,
        macro_transform_map=macro_transform_map,
        config=config,
    )


def pca_decompose(matrix: pd.DataFrame, n_factors: int = 3) -> Dict[str, np.ndarray]:
    if matrix.empty:
        raise ValueError("PCA input matrix is empty.")
    x = matrix.to_numpy(dtype=float)
    x = x - x.mean(axis=0, keepdims=True)
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    var = (s**2) / np.sum(s**2)
    n = min(n_factors, vt.shape[0])
    return {
        "factor_loadings": vt[:n],
        "explained_variance": var[:n],
        "columns": np.array(matrix.columns),
    }
