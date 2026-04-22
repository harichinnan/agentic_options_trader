"""Portfolio state container — holds open positions, cash, and the event log.

All mutations go through explicit methods so that state transitions are
auditable and easy to log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from itertools import count
from typing import Iterable

from thetakit.data.adapter import OptionQuote
from thetakit.dsl.schema import RiskConstraints
from thetakit.engine.events import settle_at_expiration, is_expiring_today
from thetakit.engine.fills import FillModel
from thetakit.engine.greeks import (
    PortfolioGreeks,
    PositionGreeks,
    aggregate_portfolio,
    compute_position_greeks,
)
from thetakit.engine.position import (
    OptionLeg,
    Position,
    PositionEvent,
    PositionStatus,
)


@dataclass
class Portfolio:
    initial_capital: float
    cash: float = field(init=False)
    positions: list[Position] = field(default_factory=list)
    closed_positions: list[Position] = field(default_factory=list)
    events: list[PositionEvent] = field(default_factory=list)
    fill_model: FillModel = field(default_factory=FillModel)
    _id_counter: "count[int]" = field(default_factory=count, init=False, repr=False)

    def __post_init__(self) -> None:
        self.cash = float(self.initial_capital)

    # ---- Queries ------------------------------------------------------------

    @property
    def open_positions(self) -> list[Position]:
        return [p for p in self.positions if p.status is PositionStatus.OPEN]

    def exposure_by_symbol(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.open_positions:
            for leg in p.legs:
                out[leg.symbol] = out.get(leg.symbol, 0) + leg.quantity
        return out

    def within_risk_limits(self, risk: RiskConstraints) -> bool:
        return len(self.open_positions) < risk.max_concurrent_positions

    def can_open_symbol(
        self, symbol: str, added_contracts: int, risk: RiskConstraints
    ) -> bool:
        cap = risk.initial_capital * risk.max_capital_per_symbol_pct
        # Crude approximation: 1 contract ~ $100 * strike of underlying notional.
        # For Phase 1 we cap by contract-count proxy proportional to symbol cap.
        max_contracts = max(int(cap / 1000), 1)
        exposure = self.exposure_by_symbol().get(symbol, 0)
        return exposure + added_contracts <= max_contracts

    # ---- Mutations ----------------------------------------------------------

    def _next_id(self) -> str:
        return f"pos-{next(self._id_counter):05d}"

    def open_position(
        self,
        *,
        strategy: str,
        symbol: str,
        on: date,
        legs: list[OptionLeg],
        quotes: dict[str, OptionQuote],
    ) -> Position:
        """Open a multi-leg short-premium position, booking the net credit."""
        credit_per_contract = 0.0
        for leg in legs:
            q = quotes[leg.option_ticker_key()]
            fill = self.fill_model.effective_fill(
                mid=q.mid,
                direction="sell_to_open" if leg.side == "short" else "buy_to_open",
                bid=q.bid,
                ask=q.ask,
            )
            if leg.side == "short":
                credit_per_contract += fill * leg.quantity
            else:
                credit_per_contract -= fill * leg.quantity

        multiplier = legs[0].multiplier
        total_credit = credit_per_contract * multiplier
        self.cash += total_credit

        pos = Position(
            id=self._next_id(),
            strategy=strategy,
            symbol=symbol,
            opened_on=on.isoformat(),
            legs=legs,
            credit_received=total_credit,
        )
        self.positions.append(pos)
        self.events.append(
            PositionEvent(
                kind="open",
                date=on.isoformat(),
                symbol=symbol,
                strategy=strategy,
                reason="entry signal",
                legs=legs,
                fill_price=total_credit / multiplier,
            )
        )
        return pos

    def close_position(
        self,
        position: Position,
        *,
        on: date,
        quotes: dict[str, OptionQuote],
        reason: str,
        tested_intraday: bool = False,
    ) -> PositionEvent:
        debit_per_contract = 0.0
        for leg in position.legs:
            q = quotes[leg.option_ticker_key()]
            fill = self.fill_model.effective_fill(
                mid=q.mid,
                direction="buy_to_close" if leg.side == "short" else "sell_to_close",
                bid=q.bid,
                ask=q.ask,
                roll_tested=tested_intraday,
            )
            if leg.side == "short":
                debit_per_contract += fill * leg.quantity
            else:
                debit_per_contract -= fill * leg.quantity

        multiplier = position.legs[0].multiplier
        total_debit = debit_per_contract * multiplier
        self.cash -= total_debit

        pnl = position.credit_received - total_debit
        position.status = PositionStatus.CLOSED
        position.closed_on = on.isoformat()
        position.close_price = total_debit / multiplier
        position.realized_pnl = pnl

        event = PositionEvent(
            kind="close",
            date=on.isoformat(),
            symbol=position.symbol,
            strategy=position.strategy,
            reason=reason,
            legs=position.legs,
            fill_price=total_debit / multiplier,
            pnl=pnl,
        )
        self.events.append(event)
        self.closed_positions.append(position)
        return event

    def process_expirations(self, today: date, underlying_closes: dict[str, float]) -> list[PositionEvent]:
        out: list[PositionEvent] = []
        for pos in list(self.open_positions):
            if not is_expiring_today(pos, today):
                continue
            spot = underlying_closes.get(pos.symbol)
            if spot is None:
                continue
            result = settle_at_expiration(pos, spot)
            pnl = pos.credit_received + result.settlement_value * pos.legs[0].multiplier
            self.cash += result.settlement_value * pos.legs[0].multiplier
            pos.status = result.status
            pos.closed_on = today.isoformat()
            pos.realized_pnl = pnl
            event = PositionEvent(
                kind="expire" if result.status is PositionStatus.EXPIRED else "assign",
                date=today.isoformat(),
                symbol=pos.symbol,
                strategy=pos.strategy,
                reason=result.reason,
                legs=pos.legs,
                fill_price=abs(result.settlement_value),
                pnl=pnl,
            )
            self.events.append(event)
            self.closed_positions.append(pos)
            out.append(event)
        return out

    def roll_position(
        self,
        position: Position,
        *,
        on: date,
        old_quotes: dict[str, OptionQuote],
        new_legs: list[OptionLeg],
        new_quotes: dict[str, OptionQuote],
        reason: str,
        tested_intraday: bool,
    ) -> PositionEvent:
        """Close the existing position and open a replacement in a single event."""
        close_event = self.close_position(
            position,
            on=on,
            quotes=old_quotes,
            reason=f"roll: {reason}",
            tested_intraday=tested_intraday,
        )
        # Open new
        self.open_position(
            strategy=position.strategy,
            symbol=position.symbol,
            on=on,
            legs=new_legs,
            quotes=new_quotes,
        )
        # Replace kind on the event pair: mark the close as a 'roll'
        close_event.kind = "roll"
        return close_event

    # ---- Snapshots ----------------------------------------------------------

    def snapshot_greeks(
        self,
        on: date,
        underlying_closes: dict[str, float],
        *,
        r: float = 0.04,
        default_sigma: float = 0.20,
        sigma_by_ticker: dict[str, float] | None = None,
    ) -> PortfolioGreeks:
        per_position: list[PositionGreeks] = []
        for pos in self.open_positions:
            spot = underlying_closes.get(pos.symbol)
            if spot is None:
                continue
            per_position.append(
                compute_position_greeks(
                    pos, spot=spot, on=on, r=r,
                    sigma_by_ticker=sigma_by_ticker, default_sigma=default_sigma,
                )
            )
        return aggregate_portfolio(per_position)


# --- Ticker-key helper for OptionLeg ------------------------------------------


def _leg_key(self: OptionLeg) -> str:
    return f"{self.symbol}|{self.option_type}|{self.strike:.4f}|{self.expiration}"


# Monkey-patch a convenience method onto OptionLeg so portfolio can look up
# quotes with a stable key. We avoid editing the frozen dataclass directly.
OptionLeg.option_ticker_key = _leg_key  # type: ignore[attr-defined]
