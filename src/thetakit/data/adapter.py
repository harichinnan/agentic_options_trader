"""DataAdapter protocol — the contract every vendor implementation must satisfy.

This protocol keeps the engine pure: the backtest core takes an adapter
as input and never touches the network or filesystem directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class UnderlyingBar:
    date: str  # ISO
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class OptionQuote:
    """Snapshot of a single option contract on a given date."""

    date: str
    symbol: str  # underlying
    option_ticker: str  # e.g., O:SPY250321C00500000
    option_type: str  # 'call' | 'put'
    strike: float
    expiration: str  # ISO
    # Pricing (close of day)
    mid: float
    bid: float | None = None
    ask: float | None = None
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float | None = None  # decimal (0.25 = 25%)


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    date: str  # ISO
    event_type: str  # 'earnings' | 'fomc' | 'opex' | 'cpi' | 'nfp' | 'ex_div'
    symbol: str | None = None  # symbol-specific events (earnings, ex_div) vs market-wide
    detail: str | None = None


@runtime_checkable
class DataAdapter(Protocol):
    """The full data contract. Adapters may raise NotImplementedError for
    methods they don't support, but `get_trading_days`, `get_underlying_bar`,
    and `get_option_chain` are required for the backtest engine."""

    def get_trading_days(self, start: date, end: date) -> list[date]:
        """Return all market trading days in [start, end] inclusive."""
        ...

    def get_underlying_bar(self, symbol: str, on: date) -> UnderlyingBar | None:
        """Return OHLCV for the underlying on a given date (None if no trading)."""
        ...

    def get_option_chain(
        self,
        symbol: str,
        on: date,
        *,
        min_dte: int = 0,
        max_dte: int = 120,
        option_type: str | None = None,
    ) -> list[OptionQuote]:
        """Return the full option chain for symbol as of `on`, filtered by DTE/type."""
        ...

    def get_calendar_events(
        self,
        symbols: list[str] | None,
        start: date,
        end: date,
        event_types: list[str] | None = None,
    ) -> list[CalendarEvent]:
        """Return known events in [start, end]. Adapters may delegate to CalendarProvider."""
        ...
