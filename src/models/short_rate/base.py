from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SimulationResult:
    time_grid: np.ndarray
    short_rates: np.ndarray


class ShortRateModel(ABC):
    """Common short-rate model interface."""

    @abstractmethod
    def fit_initial_curve(self, curve: pd.DataFrame) -> None:
        """Fit/reconstruct deterministic functions so model matches initial term structure."""

    @abstractmethod
    def calibrate_to_options(self, market_caps_floors_or_futures: pd.DataFrame, **kwargs: Any) -> dict[str, Any]:
        """Calibrate model parameters to option market quotes."""

    @abstractmethod
    def simulate_paths(self, n_paths: int, time_grid: np.ndarray, seed: int | None = None) -> SimulationResult:
        """Generate short-rate paths on provided time grid."""
