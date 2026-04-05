"""Yield-curve strategy position generator.

Generates randomised portfolios of :class:`Trade` objects that correspond to
canonical fixed-income strategies, each with an educational rationale.

Supported strategies:

* **Bull Steepener** — long front-end FRAs, short back-end; profits when short
  rates fall faster than long rates (e.g. aggressive central-bank easing).
* **Bear Steepener** — short front-end, long back-end; profits when long rates
  rise on inflation expectations or growth surprises.
* **Bull Flattener** — short front-end, long back-end *receiver*; profits when
  long rates fall more (flight-to-quality, recession fears).
* **Bear Flattener** — long front-end, short back-end; profits when short rates
  rise faster from central-bank hikes.
* **Butterfly (Curvature)** — long wings (front + back), short belly; profits
  when mid-segment moves differently from the wings.
* **Carry / Roll-Down** — long medium-tenor FRAs on an upward-sloping curve;
  earns positive carry and benefits from roll-down.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from .portfolio_shocks import Trade

# ---------------------------------------------------------------------------
# Strategy metadata (rationale exposed in UI tooltips)
# ---------------------------------------------------------------------------

STRATEGY_CHOICES: dict[str, str] = {
    "Bull Steepener": (
        "Long short-tenor FRAs + short long-tenor FRAs. "
        "Profits when central-bank easing cuts front-end yields, widening the "
        "long-short spread. Typical macro trigger: aggressive rate cuts."
    ),
    "Bear Steepener": (
        "Short short-tenor FRAs + long long-tenor FRAs. "
        "Profits when long-term yields rise on inflation expectations or strong "
        "growth while front-end rates stay anchored."
    ),
    "Bull Flattener": (
        "Short short-tenor + long long-tenor receiver positions. "
        "Profits when long-term yields fall more than short-term — e.g. recession "
        "fears or flight-to-quality compress the spread."
    ),
    "Bear Flattener": (
        "Long short-tenor + short long-tenor FRAs. "
        "Profits when short-term yields rise faster (hawkish central-bank hikes) "
        "while long rates lag."
    ),
    "Butterfly (Curvature)": (
        "Long front + back wings, short belly. "
        "Profits when the mid-segment moves differently from the wings — "
        "e.g. the belly cheapens relative to front and back."
    ),
    "Carry / Roll-Down": (
        "Long medium-tenor FRAs to earn positive carry and benefit from "
        "roll-down on an upward-sloping curve. A passive strategy that "
        "collects time-value as the position ages toward shorter tenors."
    ),
}

# Bucket → representative FRA pair → DV01 sign convention for each strategy.
# Positive DV01 = payer (profits when rates rise).
# Negative DV01 = receiver (profits when rates fall).

_STRATEGY_BLUEPRINTS: dict[str, list[dict]] = {
    "Bull Steepener": [
        {"tenor_bucket": "front", "instrument": "FRA", "dv01_sign": -1},   # receiver front
        {"tenor_bucket": "back",  "instrument": "FRA", "dv01_sign": +1},   # payer back
    ],
    "Bear Steepener": [
        {"tenor_bucket": "front", "instrument": "FRA", "dv01_sign": +1},   # payer front
        {"tenor_bucket": "back",  "instrument": "FRA", "dv01_sign": -1},   # receiver back
    ],
    "Bull Flattener": [
        {"tenor_bucket": "front", "instrument": "FRA", "dv01_sign": +1},   # payer front
        {"tenor_bucket": "back",  "instrument": "FRA", "dv01_sign": -1},   # receiver back
    ],
    "Bear Flattener": [
        {"tenor_bucket": "front", "instrument": "FRA", "dv01_sign": -1},   # receiver front
        {"tenor_bucket": "back",  "instrument": "FRA", "dv01_sign": +1},   # payer back
    ],
    "Butterfly (Curvature)": [
        {"tenor_bucket": "front", "instrument": "FRA", "dv01_sign": -1},   # receiver front (wing)
        {"tenor_bucket": "belly", "instrument": "FRA", "dv01_sign": +1},   # payer belly (body)
        {"tenor_bucket": "back",  "instrument": "FRA", "dv01_sign": -1},   # receiver back (wing)
    ],
    "Carry / Roll-Down": [
        {"tenor_bucket": "belly", "instrument": "FRA", "dv01_sign": -1},   # receiver belly (earn carry)
    ],
}

BASE_NOTIONAL: float = 10_000_000.0
NOTIONAL_VARIATION: float = 0.20      # ±20 % around base notional
DV01_PER_MILLION: float = 180.0       # ~1.8 bp per 1 M HUF notional (typical FRA)
CARRY_PER_MILLION: float = 150.0      # approximate daily carry per 1 M


def generate_random_positions(
    strategy: str,
    seed: Optional[int] = None,
    base_notional: float = BASE_NOTIONAL,
) -> List[Trade]:
    """Generate a randomised portfolio for *strategy*.

    Parameters
    ----------
    strategy:
        One of the keys in :data:`STRATEGY_CHOICES`.
    seed:
        Random seed for reproducibility.
    base_notional:
        Mean notional in HUF.  Actual notionals are drawn uniformly from
        ``[base * (1 - NOTIONAL_VARIATION), base * (1 + NOTIONAL_VARIATION)]``.

    Returns
    -------
    list[Trade]
        Ready-to-use Trade objects compatible with
        :func:`src.risk.portfolio_shocks.propagate_scenario`.
    """
    if strategy not in _STRATEGY_BLUEPRINTS:
        available = ", ".join(sorted(_STRATEGY_BLUEPRINTS))
        raise ValueError(f"Unknown strategy '{strategy}'. Choose from: {available}")

    rng = np.random.default_rng(seed)
    blueprint = _STRATEGY_BLUEPRINTS[strategy]
    trades: list[Trade] = []

    for idx, leg in enumerate(blueprint, start=1):
        low = base_notional * (1 - NOTIONAL_VARIATION)
        high = base_notional * (1 + NOTIONAL_VARIATION)
        notional = float(rng.uniform(low, high))

        dv01_magnitude = notional / 1_000_000.0 * DV01_PER_MILLION
        dv01 = leg["dv01_sign"] * dv01_magnitude

        carry_magnitude = notional / 1_000_000.0 * CARRY_PER_MILLION
        # Receivers earn positive carry; payers pay negative carry.
        carry = -leg["dv01_sign"] * carry_magnitude * float(rng.uniform(0.7, 1.3))

        trades.append(Trade(
            trade_id=f"GEN_{strategy[:4].upper()}_{idx}",
            instrument=leg["instrument"],
            notional=round(notional, 2),
            tenor_bucket=leg["tenor_bucket"],
            dv01=round(dv01, 2),
            carry=round(carry, 2),
        ))

    return trades
