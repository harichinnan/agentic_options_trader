"""Position and OptionLeg data models for the backtest engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ROLLED = "rolled"
    EXPIRED = "expired"
    ASSIGNED = "assigned"


LegSide = Literal["short", "long"]
OptionType = Literal["call", "put"]


@dataclass(frozen=True, slots=True)
class OptionLeg:
    """A single option leg (strike, expiration, call/put, short/long, quantity)."""

    symbol: str
    option_type: OptionType
    strike: float
    expiration: str  # ISO date
    side: LegSide
    quantity: int  # Always positive; side encodes short/long
    multiplier: int = 100

    @property
    def signed_quantity(self) -> int:
        return self.quantity if self.side == "long" else -self.quantity


@dataclass(slots=True)
class PositionEvent:
    """One row in the trade log."""

    kind: Literal["open", "roll", "close", "expire", "assign", "skip"]
    date: str
    symbol: str
    strategy: str
    reason: str
    legs: list[OptionLeg] = field(default_factory=list)
    fill_price: float | None = None  # per contract, net credit positive for opens
    delta_at_event: float | None = None
    dte_at_event: int | None = None
    pnl: float | None = None  # realized P&L for close/expire/assign


@dataclass(slots=True)
class Position:
    """An open (or historical) position composed of one or more legs.

    For single-leg short-premium strategies (CSP, CC) the list has one short
    leg. Spreads have two legs; iron condors have four. The engine treats
    all of them uniformly through this container.
    """

    id: str
    strategy: str
    symbol: str
    opened_on: str
    legs: list[OptionLeg]
    credit_received: float  # Net credit (positive for short premium)
    status: PositionStatus = PositionStatus.OPEN
    closed_on: str | None = None
    close_price: float | None = None  # Net debit paid to close
    realized_pnl: float | None = None

    @property
    def is_single_short_leg(self) -> bool:
        return len(self.legs) == 1 and self.legs[0].side == "short"

    @property
    def primary_expiration(self) -> str:
        """The nearest expiration across legs (used for DTE calculations)."""
        return min(leg.expiration for leg in self.legs)

    @property
    def total_quantity(self) -> int:
        """Sum of absolute contract counts across legs (for sizing checks)."""
        return sum(leg.quantity for leg in self.legs)
