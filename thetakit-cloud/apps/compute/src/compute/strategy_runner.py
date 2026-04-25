"""Run a Phase 1 strategy against a simulated price path.

Builds a DataAdapter on-the-fly from a SimulatedPath and delegates to the
`thetakit.engine.run_backtest` engine. This is how the compute layer
reuses the OSS toolkit as the core strategy lifecycle engine.
"""

from __future__ import annotations

from datetime import date, timedelta
from math import log

from compute.aggregator import PathOutcome
from compute.path_simulator import SimulatedPath
from thetakit.data.adapter import CalendarEvent, OptionQuote, UnderlyingBar
from thetakit.data.calendar import CalendarProvider
from thetakit.dsl.schema import Strategy
from thetakit.engine.backtest import BacktestOptions, run_backtest
from thetakit.pricing.bsm import bsm_price


class PathDataAdapter:
    """DataAdapter built from a single SimulatedPath."""

    def __init__(
        self,
        path: SimulatedPath,
        risk_free_rate: float = 0.04,
        implied_vol: float = 0.22,
    ):
        self.path = path
        self.risk_free_rate = risk_free_rate
        self.iv = implied_vol
        self.calendar = CalendarProvider.default()
        self._date_index = {d: i for i, d in enumerate(path.dates)}

    def get_trading_days(self, start: date, end: date) -> list[date]:
        return [
            date.fromisoformat(d)
            for d in self.path.dates
            if start.isoformat() <= d <= end.isoformat()
        ]

    def get_underlying_bar(self, symbol: str, on: date) -> UnderlyingBar | None:
        idx = self._date_index.get(on.isoformat())
        if idx is None or symbol not in self.path.prices:
            return None
        close = self.path.prices[symbol][idx]
        # Synthetic intraday: +/- 0.5% around close
        high = close * 1.005
        low = close * 0.995
        open_ = (self.path.prices[symbol][max(idx - 1, 0)] + close) / 2
        return UnderlyingBar(
            date=on.isoformat(), symbol=symbol,
            open=round(open_, 2), high=round(high, 2),
            low=round(low, 2), close=round(close, 2), volume=1_000_000,
        )

    def get_option_chain(
        self, symbol: str, on: date, *, min_dte: int = 0, max_dte: int = 120,
        option_type: str | None = None,
    ) -> list[OptionQuote]:
        bar = self.get_underlying_bar(symbol, on)
        if bar is None:
            return []
        spot = bar.close
        spacing = spot * 0.025
        strikes = [round(spot + (i - 20) * spacing, 1) for i in range(41)]
        strikes = [k for k in strikes if k > 0]

        out: list[OptionQuote] = []
        for dte in (7, 14, 21, 30, 45, 60):
            if dte < min_dte or dte > max_dte:
                continue
            expiry = on + timedelta(days=dte)
            t = dte / 365.0
            for k in strikes:
                for kind in ("call", "put"):
                    if option_type and kind != option_type:
                        continue
                    price = bsm_price(spot, k, t, self.risk_free_rate, self.iv, kind)  # type: ignore[arg-type]
                    price = max(price, 0.01)
                    out.append(
                        OptionQuote(
                            date=on.isoformat(), symbol=symbol,
                            option_ticker=f"O:{symbol}{expiry.strftime('%y%m%d')}{'C' if kind == 'call' else 'P'}{int(k * 1000):08d}",
                            option_type=kind, strike=k, expiration=expiry.isoformat(),
                            mid=round(price, 3),
                            bid=round(max(price * 0.975, 0.01), 3),
                            ask=round(price * 1.025, 3),
                            implied_volatility=self.iv,
                            volume=100, open_interest=1000,
                        )
                    )
        return out

    def get_calendar_events(
        self, symbols: list[str] | None, start: date, end: date,
        event_types: list[str] | None = None,
    ) -> list[CalendarEvent]:
        return self.calendar.events_in_range(
            start, end, symbols=symbols, event_types=event_types,
        )


def run_strategy_on_path(
    strategy: Strategy, path: SimulatedPath, *, initial_capital: float = 100_000
) -> PathOutcome:
    """Run the Phase 1 engine against one simulated path. Returns one outcome."""
    adapter = PathDataAdapter(path)
    start = date.fromisoformat(path.dates[0])
    end = date.fromisoformat(path.dates[-1])
    options = BacktestOptions(initial_capital=initial_capital)
    results = run_backtest(strategy, adapter, start, end, options)

    daily = results.daily
    if not daily:
        return PathOutcome(
            path_id=path.path_id, total_return_pct=0.0, max_drawdown_pct=0.0,
            cagr_pct=0.0, trades=0, win_rate=0.0, dominant_regime=0,
        )

    equity = [d.equity for d in daily]
    total_return = (equity[-1] / initial_capital - 1.0) * 100.0
    years = max(len(equity) / 252.0, 1e-3)
    cagr = ((equity[-1] / initial_capital) ** (1 / years) - 1.0) * 100.0

    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (v / peak - 1.0) * 100.0
        if dd < max_dd:
            max_dd = dd

    closed = results.closed_positions
    wins = sum(1 for p in closed if (p.realized_pnl or 0) > 0)
    win_rate = (wins / len(closed) * 100.0) if closed else 0.0

    regimes = path.regimes
    dominant = int(max(set(regimes), key=regimes.count)) if regimes else 0

    return PathOutcome(
        path_id=path.path_id,
        total_return_pct=total_return,
        max_drawdown_pct=max_dd,
        cagr_pct=cagr,
        trades=len(closed),
        win_rate=win_rate,
        dominant_regime=dominant,
    )
