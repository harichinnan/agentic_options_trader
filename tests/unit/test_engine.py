"""Engine unit tests: fills, rolls, events, position lifecycle."""

from __future__ import annotations

from datetime import date

import pytest

from thetakit.data.adapter import UnderlyingBar, OptionQuote
from thetakit.dsl.schema import RollRule
from thetakit.engine.events import settle_at_expiration
from thetakit.engine.fills import FillModel
from thetakit.engine.portfolio import Portfolio
from thetakit.engine.position import OptionLeg, PositionStatus
from thetakit.engine.rolls import evaluate_rolls


class TestFillModel:
    def test_sell_fills_below_mid(self) -> None:
        fm = FillModel(spread_pct=0.4)
        fill = fm.effective_fill(mid=1.0, direction="sell_to_open", bid=0.95, ask=1.05)
        assert fill < 1.0

    def test_buy_fills_above_mid(self) -> None:
        fm = FillModel(spread_pct=0.4)
        fill = fm.effective_fill(mid=1.0, direction="buy_to_close", bid=0.95, ask=1.05)
        assert fill > 1.0

    def test_intraday_roll_penalty_applied(self) -> None:
        fm = FillModel(spread_pct=0.4)
        normal = fm.effective_fill(mid=1.0, direction="buy_to_close", bid=0.95, ask=1.05)
        penalty = fm.effective_fill(
            mid=1.0, direction="buy_to_close", bid=0.95, ask=1.05, roll_tested=True
        )
        assert penalty > normal

    def test_synthetic_spread_used_when_no_bid_ask(self) -> None:
        fm = FillModel(spread_pct=0.4, synthetic_spread_pct=0.1)
        fill = fm.effective_fill(mid=1.0, direction="sell_to_open")
        # mid * 0.1 spread, cross 0.4 * half = 0.02
        assert abs(fill - (1.0 - 0.02)) < 1e-6


class TestExpirationSettlement:
    def _short_call_pos(self, strike: float = 100, expiry: str = "2025-01-17"):
        leg = OptionLeg(
            symbol="SPY",
            option_type="call",
            strike=strike,
            expiration=expiry,
            side="short",
            quantity=1,
        )
        from thetakit.engine.position import Position
        return Position(
            id="p1",
            strategy="test",
            symbol="SPY",
            opened_on="2024-12-01",
            legs=[leg],
            credit_received=100.0,
        )

    def test_short_call_otm_expires(self) -> None:
        pos = self._short_call_pos(strike=100)
        result = settle_at_expiration(pos, underlying_close=90.0)
        assert result.status is PositionStatus.EXPIRED

    def test_short_call_itm_assigned(self) -> None:
        pos = self._short_call_pos(strike=100)
        result = settle_at_expiration(pos, underlying_close=110.0)
        assert result.status is PositionStatus.ASSIGNED


class TestPortfolioBookkeeping:
    def test_open_short_credit_increases_cash(self) -> None:
        pf = Portfolio(initial_capital=10_000)
        leg = OptionLeg(
            symbol="SPY", option_type="put", strike=400, expiration="2025-03-21",
            side="short", quantity=1,
        )
        q = OptionQuote(
            date="2025-01-15", symbol="SPY", option_ticker="O:SPY250321P00400000",
            option_type="put", strike=400, expiration="2025-03-21",
            mid=3.0, bid=2.95, ask=3.05,
        )
        pf.open_position(
            strategy="test", symbol="SPY", on=date(2025, 1, 15),
            legs=[leg], quotes={leg.option_ticker_key(): q},  # type: ignore[attr-defined]
        )
        assert pf.cash > 10_000
        assert len(pf.open_positions) == 1


class TestRollTriggers:
    def test_short_call_high_tests_strike(self) -> None:
        leg = OptionLeg(
            symbol="SPY", option_type="call", strike=500, expiration="2025-02-21",
            side="short", quantity=1,
        )
        from thetakit.engine.position import Position
        pos = Position(
            id="p1", strategy="CC", symbol="SPY",
            opened_on="2025-01-15", legs=[leg], credit_received=200.0,
        )
        bar = UnderlyingBar(
            date="2025-01-20", symbol="SPY", open=495, high=501, low=490, close=498, volume=1000
        )
        rules = [RollRule(trigger="short_strike_tested")]
        sig = evaluate_rolls(pos, rules, bar, date(2025, 1, 20))
        assert sig.fired
        assert sig.tested_intraday

    def test_dte_threshold_fires_when_close(self) -> None:
        leg = OptionLeg(
            symbol="SPY", option_type="put", strike=400, expiration="2025-01-25",
            side="short", quantity=1,
        )
        from thetakit.engine.position import Position
        pos = Position(
            id="p1", strategy="CSP", symbol="SPY",
            opened_on="2024-12-01", legs=[leg], credit_received=200.0,
        )
        bar = UnderlyingBar(
            date="2025-01-20", symbol="SPY", open=420, high=422, low=419, close=420, volume=1000
        )
        rules = [RollRule(trigger="dte_threshold", dte_threshold=7)]
        sig = evaluate_rolls(pos, rules, bar, date(2025, 1, 20))
        assert sig.fired


class TestPositionInvariants:
    def test_signed_quantity_short_negative(self) -> None:
        leg = OptionLeg(
            symbol="SPY", option_type="call", strike=500, expiration="2025-02-21",
            side="short", quantity=2,
        )
        assert leg.signed_quantity == -2

    def test_signed_quantity_long_positive(self) -> None:
        leg = OptionLeg(
            symbol="SPY", option_type="call", strike=500, expiration="2025-02-21",
            side="long", quantity=3,
        )
        assert leg.signed_quantity == 3
