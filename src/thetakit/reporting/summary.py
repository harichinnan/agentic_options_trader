"""Summary statistics for a BacktestResults."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thetakit.engine.backtest import BacktestResults


@dataclass(frozen=True, slots=True)
class BacktestStats:
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    sortino: float
    max_drawdown_pct: float
    max_drawdown_days: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_trades: int
    avg_dte_entry: float
    avg_days_in_trade: float


def _daily_returns(equity: list[float]) -> list[float]:
    out: list[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        cur = equity[i]
        if prev == 0:
            out.append(0.0)
        else:
            out.append(cur / prev - 1.0)
    return out


def _max_drawdown(equity: list[float]) -> tuple[float, int]:
    if not equity:
        return 0.0, 0
    peak = equity[0]
    peak_idx = 0
    max_dd = 0.0
    max_dd_days = 0
    for i, v in enumerate(equity):
        if v > peak:
            peak = v
            peak_idx = i
        dd = (v / peak - 1.0) if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
            max_dd_days = i - peak_idx
    return max_dd * 100.0, max_dd_days


def _annualize(returns: list[float]) -> tuple[float, float, float]:
    """Return (mean_daily, std_daily, trading_days)."""
    if not returns:
        return 0.0, 0.0, 0.0
    n = len(returns)
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / max(n - 1, 1)
    std = math.sqrt(var)
    return mean, std, float(n)


def compute_stats(results: BacktestResults) -> BacktestStats:
    daily = results.daily
    if not daily:
        return BacktestStats(
            total_return_pct=0.0,
            cagr_pct=0.0,
            sharpe=0.0,
            sortino=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_days=0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_dte_entry=0.0,
            avg_days_in_trade=0.0,
        )

    equity = [d.equity for d in daily]
    returns = _daily_returns(equity)

    total_return_pct = (equity[-1] / results.initial_capital - 1.0) * 100.0

    years = max(len(daily) / 252.0, 1 / 252.0)
    cagr = ((equity[-1] / results.initial_capital) ** (1 / years) - 1.0) * 100.0

    mean, std, _ = _annualize(returns)
    sharpe = (mean / std * math.sqrt(252.0)) if std > 0 else 0.0

    downside = [r for r in returns if r < 0]
    _, d_std, _ = _annualize(downside) if downside else (0.0, 0.0, 0.0)
    sortino = (mean / d_std * math.sqrt(252.0)) if d_std > 0 else 0.0

    max_dd_pct, max_dd_days = _max_drawdown(equity)

    pnls = [p.realized_pnl for p in results.closed_positions if p.realized_pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = (len(wins) / len(pnls) * 100.0) if pnls else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0

    open_events = [e for e in results.events if e.kind == "open" and e.dte_at_event is not None]
    avg_dte = (sum(e.dte_at_event or 0 for e in open_events) / len(open_events)) if open_events else 0.0

    from datetime import date as _date
    durations: list[int] = []
    for pos in results.closed_positions:
        if pos.closed_on:
            durations.append((_date.fromisoformat(pos.closed_on) - _date.fromisoformat(pos.opened_on)).days)
    avg_days_in_trade = (sum(durations) / len(durations)) if durations else 0.0

    return BacktestStats(
        total_return_pct=total_return_pct,
        cagr_pct=cagr,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_pct=max_dd_pct,
        max_drawdown_days=max_dd_days,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        total_trades=len(pnls),
        avg_dte_entry=avg_dte,
        avg_days_in_trade=avg_days_in_trade,
    )
