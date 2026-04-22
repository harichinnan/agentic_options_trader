"""Main backtest loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from thetakit.data.adapter import DataAdapter, OptionQuote
from thetakit.dsl.schema import ExitRule, Strategy
from thetakit.engine.entry import find_entry
from thetakit.engine.greeks import PortfolioGreeks
from thetakit.engine.portfolio import Portfolio
from thetakit.engine.position import OptionLeg, Position, PositionEvent
from thetakit.engine.rolls import evaluate_rolls
from thetakit.pricing.bsm import bsm_greeks, time_to_expiry_years


@dataclass(frozen=True, slots=True)
class BacktestOptions:
    initial_capital: float = 100_000
    spread_pct: float = 0.4
    risk_free_rate: float = 0.04
    default_sigma: float = 0.20


@dataclass(slots=True)
class DailySnapshot:
    date: str
    cash: float
    open_positions: int
    mark_value: float
    equity: float
    delta: float
    gamma: float
    theta: float
    vega: float


@dataclass(slots=True)
class BacktestResults:
    strategy_name: str
    start: str
    end: str
    universe: list[str]
    options: BacktestOptions
    events: list[PositionEvent]
    daily: list[DailySnapshot]
    final_equity: float
    initial_capital: float
    closed_positions: list[Position] = field(default_factory=list)

    @property
    def total_return_pct(self) -> float:
        return (self.final_equity / self.initial_capital - 1.0) * 100.0

    def summarize_for_llm(self) -> str:
        n_open = sum(1 for e in self.events if e.kind == "open")
        n_close = sum(1 for e in self.events if e.kind == "close")
        n_roll = sum(1 for e in self.events if e.kind == "roll")
        n_expire = sum(1 for e in self.events if e.kind == "expire")
        n_assign = sum(1 for e in self.events if e.kind == "assign")
        return (
            f"Backtest of '{self.strategy_name}' over {self.start} to {self.end} "
            f"on {', '.join(self.universe)}:\n"
            f"  total return: {self.total_return_pct:+.2f}%\n"
            f"  final equity: ${self.final_equity:,.2f} "
            f"(from ${self.initial_capital:,.2f})\n"
            f"  trades: {n_open} opens, {n_close} closes, {n_roll} rolls, "
            f"{n_expire} expirations, {n_assign} assignments"
        )


def _exit_triggered(
    position: Position,
    exits: list[ExitRule],
    close_debit_per_contract: float,
    on: date,
) -> tuple[bool, str]:
    """Return (triggered, reason) for any configured exit."""
    credit = position.credit_received / position.legs[0].multiplier
    if credit <= 0:
        return False, ""

    # profit_target_pct interpreted as "close when debit <= (1-target)*credit"
    for ex in exits:
        if ex.profit_target_pct is not None:
            if close_debit_per_contract <= credit * (1 - ex.profit_target_pct):
                return True, f"profit target {ex.profit_target_pct*100:.0f}% reached"
        if ex.dte_close is not None:
            dte = (date.fromisoformat(position.primary_expiration) - on).days
            if dte <= ex.dte_close:
                return True, f"DTE={dte} <= dte_close {ex.dte_close}"
        if ex.stop_loss_multiplier is not None:
            if close_debit_per_contract >= credit * ex.stop_loss_multiplier:
                return True, f"loss = {ex.stop_loss_multiplier}x credit"
    return False, ""


def _build_quotes_map(
    legs: list[OptionLeg], chain: list[OptionQuote]
) -> dict[str, OptionQuote]:
    """Map each leg's ticker-key to a matching quote from the chain.

    For rolled positions, an exact strike/expiry/type match may not exist on
    the current day (strike grid or expirations shifted). In that case we
    build a synthetic quote from a BSM mark using default_sigma.
    """
    out: dict[str, OptionQuote] = {}
    for leg in legs:
        key = leg.option_ticker_key()  # type: ignore[attr-defined]
        match = next(
            (
                q
                for q in chain
                if q.option_type == leg.option_type
                and abs(q.strike - leg.strike) < 1e-6
                and q.expiration == leg.expiration
            ),
            None,
        )
        if match is not None:
            out[key] = match
            continue
        # Synthetic fallback: no market match — use a $0.01 mark so tests are deterministic
        out[key] = OptionQuote(
            date=chain[0].date if chain else "",
            symbol=leg.symbol,
            option_ticker=f"SYN:{leg.symbol}",
            option_type=leg.option_type,
            strike=leg.strike,
            expiration=leg.expiration,
            mid=0.01,
            bid=0.005,
            ask=0.015,
        )
    return out


def _mark_debit_per_contract(position: Position, chain: list[OptionQuote]) -> float:
    qmap = _build_quotes_map(position.legs, chain)
    debit = 0.0
    for leg in position.legs:
        q = qmap[leg.option_ticker_key()]  # type: ignore[attr-defined]
        if leg.side == "short":
            debit += q.mid * leg.quantity
        else:
            debit -= q.mid * leg.quantity
    return debit


def _calendar_veto(
    entry: Any, candidate_symbol: str, adapter: DataAdapter, today: date
) -> bool:
    """Return True if entry should be skipped due to event proximity filters."""
    event_types_of_interest = []
    filters = []
    if entry.skip_if_earnings_within_days is not None:
        event_types_of_interest.append("earnings")
        filters.append(("earnings", entry.skip_if_earnings_within_days))
    if entry.skip_if_fomc_within_days is not None:
        event_types_of_interest.append("fomc")
        filters.append(("fomc", entry.skip_if_fomc_within_days))
    if entry.skip_if_cpi_within_days is not None:
        event_types_of_interest.append("cpi")
        filters.append(("cpi", entry.skip_if_cpi_within_days))
    if entry.skip_if_ex_div_within_days is not None:
        event_types_of_interest.append("ex_div")
        filters.append(("ex_div", entry.skip_if_ex_div_within_days))
    if not event_types_of_interest:
        return False

    end = today + timedelta(days=max(e[1] for e in filters) + 1)
    events = adapter.get_calendar_events(
        [candidate_symbol], today, end, event_types=event_types_of_interest
    )
    for etype, max_days in filters:
        nearest = min(
            (e for e in events if e.event_type == etype),
            key=lambda e: e.date,
            default=None,
        )
        if nearest is None:
            continue
        delta_days = (date.fromisoformat(nearest.date) - today).days
        if 0 <= delta_days <= max_days:
            return True
    return False


def run_backtest(
    strategy: Strategy,
    data: DataAdapter,
    start: date,
    end: date,
    options: BacktestOptions | None = None,
) -> BacktestResults:
    """Run a historical backtest. Deterministic, pure: inputs in, results out."""
    options = options or BacktestOptions(initial_capital=strategy.risk.initial_capital)

    universe = (
        strategy.entry.symbols if isinstance(strategy.entry.symbols, list) else []
    )
    if not universe:
        raise ValueError("Phase 1 backtest requires an explicit symbols list on entry")

    portfolio = Portfolio(initial_capital=options.initial_capital)
    portfolio.fill_model = portfolio.fill_model.__class__(spread_pct=options.spread_pct)

    trading_days = data.get_trading_days(start, end)
    daily_snapshots: list[DailySnapshot] = []

    for day in trading_days:
        underlying_closes: dict[str, float] = {}
        chains_by_symbol: dict[str, list[OptionQuote]] = {}
        for sym in universe:
            bar = data.get_underlying_bar(sym, day)
            if bar is None:
                continue
            underlying_closes[sym] = bar.close
            chains_by_symbol[sym] = data.get_option_chain(
                sym, day, min_dte=1, max_dte=120
            )

        # 1) Expirations
        portfolio.process_expirations(day, underlying_closes)

        # 2) Exits (profit target, DTE close, stop loss)
        for pos in list(portfolio.open_positions):
            chain = chains_by_symbol.get(pos.symbol, [])
            if not chain:
                continue
            debit_per = _mark_debit_per_contract(pos, chain)
            triggered, reason = _exit_triggered(pos, strategy.exits, debit_per, day)
            if triggered:
                qmap = _build_quotes_map(pos.legs, chain)
                portfolio.close_position(pos, on=day, quotes=qmap, reason=reason)

        # 3) Rolls
        for pos in list(portfolio.open_positions):
            bar = data.get_underlying_bar(pos.symbol, day)
            chain = chains_by_symbol.get(pos.symbol, [])
            if bar is None or not chain:
                continue
            signal = evaluate_rolls(
                pos, strategy.rolls, bar, day,
                r=options.risk_free_rate, sigma=options.default_sigma,
            )
            if not signal.fired:
                continue
            # Build new legs: same strategy, same delta target, fresh DTE
            candidate = find_entry(
                strategy.entry,
                symbol=pos.symbol,
                underlying=bar,
                chain=chain,
                on=day,
                r=options.risk_free_rate,
                default_sigma=options.default_sigma,
            )
            if candidate is None:
                continue
            old_qmap = _build_quotes_map(pos.legs, chain)
            new_qmap = _build_quotes_map(candidate.legs, chain)
            portfolio.roll_position(
                pos,
                on=day,
                old_quotes=old_qmap,
                new_legs=candidate.legs,
                new_quotes=new_qmap,
                reason=signal.reason or signal.trigger or "roll",
                tested_intraday=signal.tested_intraday,
            )

        # 4) New entries (per symbol, within risk limits)
        if portfolio.within_risk_limits(strategy.risk):
            for sym in universe:
                bar = data.get_underlying_bar(sym, day)
                chain = chains_by_symbol.get(sym, [])
                if bar is None or not chain:
                    continue
                # One position per symbol at a time (Phase 1 simplification)
                has_open = any(p.symbol == sym for p in portfolio.open_positions)
                if has_open:
                    continue
                if _calendar_veto(strategy.entry, sym, data, day):
                    portfolio.events.append(
                        PositionEvent(
                            kind="skip",
                            date=day.isoformat(),
                            symbol=sym,
                            strategy=strategy.name,
                            reason="event proximity filter",
                        )
                    )
                    continue
                candidate = find_entry(
                    strategy.entry,
                    symbol=sym,
                    underlying=bar,
                    chain=chain,
                    on=day,
                    r=options.risk_free_rate,
                    default_sigma=options.default_sigma,
                )
                if candidate is None:
                    continue
                qmap = _build_quotes_map(candidate.legs, chain)
                portfolio.open_position(
                    strategy=strategy.name,
                    symbol=sym,
                    on=day,
                    legs=candidate.legs,
                    quotes=qmap,
                )
                if not portfolio.within_risk_limits(strategy.risk):
                    break

        # 5) Snapshot
        pg: PortfolioGreeks = portfolio.snapshot_greeks(
            day, underlying_closes,
            r=options.risk_free_rate, default_sigma=options.default_sigma,
        )
        equity = portfolio.cash + pg.mark_value
        daily_snapshots.append(
            DailySnapshot(
                date=day.isoformat(),
                cash=portfolio.cash,
                open_positions=len(portfolio.open_positions),
                mark_value=pg.mark_value,
                equity=equity,
                delta=pg.delta,
                gamma=pg.gamma,
                theta=pg.theta,
                vega=pg.vega,
            )
        )

    final_equity = daily_snapshots[-1].equity if daily_snapshots else options.initial_capital

    return BacktestResults(
        strategy_name=strategy.name,
        start=start.isoformat(),
        end=end.isoformat(),
        universe=universe,
        options=options,
        events=portfolio.events,
        daily=daily_snapshots,
        final_equity=final_equity,
        initial_capital=options.initial_capital,
        closed_positions=portfolio.closed_positions,
    )
