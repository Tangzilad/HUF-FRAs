"""Tests for the yield-curve strategy position generator."""

from __future__ import annotations

import pytest

from src.risk.portfolio_shocks import Trade
from src.risk.strategies import STRATEGY_CHOICES, generate_random_positions


class TestGenerateRandomPositions:
    @pytest.mark.parametrize("strategy", list(STRATEGY_CHOICES.keys()))
    def test_returns_nonempty_trade_list(self, strategy: str):
        trades = generate_random_positions(strategy, seed=42)
        assert len(trades) > 0
        assert all(isinstance(t, Trade) for t in trades)

    @pytest.mark.parametrize("strategy", list(STRATEGY_CHOICES.keys()))
    def test_trades_have_valid_tenor_buckets(self, strategy: str):
        trades = generate_random_positions(strategy, seed=7)
        valid_buckets = {"front", "belly", "back"}
        for t in trades:
            assert t.tenor_bucket in valid_buckets, f"{t.trade_id}: bucket={t.tenor_bucket}"

    @pytest.mark.parametrize("strategy", list(STRATEGY_CHOICES.keys()))
    def test_notionals_vary_around_base(self, strategy: str):
        trades = generate_random_positions(strategy, seed=99, base_notional=10_000_000.0)
        for t in trades:
            assert 8_000_000 <= t.notional <= 12_000_000, (
                f"{t.trade_id}: notional={t.notional}"
            )

    def test_seed_reproducibility(self):
        a = generate_random_positions("Bull Steepener", seed=123)
        b = generate_random_positions("Bull Steepener", seed=123)
        assert len(a) == len(b)
        for ta, tb in zip(a, b):
            assert ta.notional == tb.notional
            assert ta.dv01 == tb.dv01

    def test_different_seeds_produce_different_notionals(self):
        a = generate_random_positions("Bull Steepener", seed=1)
        b = generate_random_positions("Bull Steepener", seed=2)
        notionals_a = [t.notional for t in a]
        notionals_b = [t.notional for t in b]
        assert notionals_a != notionals_b

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            generate_random_positions("NonExistent Strategy", seed=42)

    def test_bull_steepener_has_opposing_dv01_signs(self):
        """Bull steepener should be receiver-front (neg DV01) + payer-back (pos DV01)."""
        trades = generate_random_positions("Bull Steepener", seed=42)
        front = [t for t in trades if t.tenor_bucket == "front"]
        back = [t for t in trades if t.tenor_bucket == "back"]
        assert all(t.dv01 < 0 for t in front), "Front leg should be receiver (neg DV01)"
        assert all(t.dv01 > 0 for t in back), "Back leg should be payer (pos DV01)"

    def test_butterfly_has_three_legs(self):
        trades = generate_random_positions("Butterfly (Curvature)", seed=42)
        buckets = {t.tenor_bucket for t in trades}
        assert buckets == {"front", "belly", "back"}

    def test_carry_roll_down_is_single_belly_leg(self):
        trades = generate_random_positions("Carry / Roll-Down", seed=42)
        assert len(trades) == 1
        assert trades[0].tenor_bucket == "belly"

    def test_all_strategies_have_rationale_text(self):
        for name, rationale in STRATEGY_CHOICES.items():
            assert len(rationale) > 20, f"'{name}' rationale too short"
