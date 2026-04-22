"""Deterministic synthetic market data for tests, CI, and example runs.

Generates:
- Geometric Brownian Motion underlying price paths
- A full option chain per day priced via Black-Scholes at a configurable
  vol surface (flat by default)
- Optional ex-div events

Everything is seeded for determinism. This lets the engine be tested and
exercised without any vendor credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from math import exp, sqrt

import numpy as np

from thetakit.data.adapter import CalendarEvent, OptionQuote, UnderlyingBar
from thetakit.data.calendar import CalendarProvider
from thetakit.pricing.bsm import bsm_price


@dataclass
class SyntheticDataAdapter:
    """In-memory deterministic options data. Implements DataAdapter protocol."""

    symbols: list[str]
    start: date
    end: date
    initial_price: dict[str, float] = field(default_factory=dict)
    annual_drift: float = 0.05
    annual_vol: float = 0.20
    risk_free_rate: float = 0.04
    dividend_yield: float = 0.0
    seed: int = 42
    calendar: CalendarProvider = field(default_factory=CalendarProvider.default)

    # Option chain grid
    strike_spacing_pct: float = 0.025  # 2.5% of spot per strike
    strike_count_each_side: int = 20
    expiration_dtes: tuple[int, ...] = (7, 14, 21, 30, 45, 60, 90)

    _bars: dict[tuple[str, str], UnderlyingBar] = field(default_factory=dict, init=False)
    _trading_days: list[date] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        for sym in self.symbols:
            self.initial_price.setdefault(sym, 100.0)
        self._generate_paths()

    def _generate_paths(self) -> None:
        rng = np.random.default_rng(self.seed)
        days = [
            self.start + timedelta(days=i)
            for i in range((self.end - self.start).days + 1)
            if (self.start + timedelta(days=i)).weekday() < 5
        ]
        self._trading_days = days

        dt = 1.0 / 252.0
        for sym_idx, sym in enumerate(self.symbols):
            s = self.initial_price[sym]
            sym_rng = np.random.default_rng(self.seed + sym_idx * 7919)
            for d in days:
                drift = (self.annual_drift - 0.5 * self.annual_vol ** 2) * dt
                shock = self.annual_vol * sqrt(dt) * float(sym_rng.standard_normal())
                s = s * exp(drift + shock)
                high = s * (1 + abs(sym_rng.normal(0, 0.005)))
                low = s * (1 - abs(sym_rng.normal(0, 0.005)))
                open_ = s * (1 + sym_rng.normal(0, 0.003))
                vol = int(sym_rng.integers(500_000, 5_000_000))
                self._bars[(sym, d.isoformat())] = UnderlyingBar(
                    date=d.isoformat(),
                    symbol=sym,
                    open=round(open_, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(s, 2),
                    volume=vol,
                )

    # ---- DataAdapter protocol -----------------------------------------------

    def get_trading_days(self, start: date, end: date) -> list[date]:
        return [d for d in self._trading_days if start <= d <= end]

    def get_underlying_bar(self, symbol: str, on: date) -> UnderlyingBar | None:
        return self._bars.get((symbol, on.isoformat()))

    def get_option_chain(
        self,
        symbol: str,
        on: date,
        *,
        min_dte: int = 0,
        max_dte: int = 120,
        option_type: str | None = None,
    ) -> list[OptionQuote]:
        bar = self.get_underlying_bar(symbol, on)
        if bar is None:
            return []

        spot = bar.close
        chain: list[OptionQuote] = []

        # Build strike grid
        spacing = spot * self.strike_spacing_pct
        strikes = [
            round(spot + (i - self.strike_count_each_side) * spacing, 1)
            for i in range(2 * self.strike_count_each_side + 1)
        ]
        strikes = [k for k in strikes if k > 0]

        for dte in self.expiration_dtes:
            if dte < min_dte or dte > max_dte:
                continue
            expiry = on + timedelta(days=dte)
            t = dte / 365.0
            for k in strikes:
                for kind in ("call", "put"):
                    if option_type and kind != option_type:
                        continue
                    price = bsm_price(
                        s=spot,
                        k=k,
                        t=t,
                        r=self.risk_free_rate,
                        sigma=self.annual_vol,
                        option_type=kind,  # type: ignore[arg-type]
                        q=self.dividend_yield,
                    )
                    price = max(price, 0.01)
                    spread = price * 0.05
                    bid = max(price - spread / 2, 0.01)
                    ask = price + spread / 2
                    ticker = self._make_ticker(symbol, expiry, kind, k)
                    chain.append(
                        OptionQuote(
                            date=on.isoformat(),
                            symbol=symbol,
                            option_ticker=ticker,
                            option_type=kind,
                            strike=k,
                            expiration=expiry.isoformat(),
                            mid=round(price, 3),
                            bid=round(bid, 3),
                            ask=round(ask, 3),
                            implied_volatility=self.annual_vol,
                            volume=100,
                            open_interest=1000,
                        )
                    )
        return chain

    def get_calendar_events(
        self,
        symbols: list[str] | None,
        start: date,
        end: date,
        event_types: list[str] | None = None,
    ) -> list[CalendarEvent]:
        return self.calendar.events_in_range(
            start, end, symbols=symbols, event_types=event_types
        )

    # ---- Helpers ------------------------------------------------------------

    @staticmethod
    def _make_ticker(symbol: str, expiry: date, kind: str, strike: float) -> str:
        cp = "C" if kind == "call" else "P"
        yymmdd = expiry.strftime("%y%m%d")
        strike_int = int(round(strike * 1000))
        return f"O:{symbol}{yymmdd}{cp}{strike_int:08d}"
