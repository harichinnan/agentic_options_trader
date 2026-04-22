"""Plotly-based chart rendering."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thetakit.engine.backtest import BacktestResults


def render_equity_curve(results: "BacktestResults", out_path: str | Path) -> Path:
    """Render an interactive equity + drawdown chart to HTML."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    daily = results.daily
    if not daily:
        raise ValueError("no daily snapshots to plot")

    dates = [d.date for d in daily]
    equity = [d.equity for d in daily]

    peak_so_far = []
    peak = equity[0]
    for v in equity:
        if v > peak:
            peak = v
        peak_so_far.append(peak)
    drawdown = [(e / p - 1.0) * 100.0 if p > 0 else 0.0 for e, p in zip(equity, peak_so_far)]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        subplot_titles=("Equity curve", "Drawdown (%)"),
        vertical_spacing=0.08,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=equity, name="Equity", line={"color": "#2e86de"}),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates, y=drawdown, name="Drawdown %",
            fill="tozeroy", line={"color": "#e74c3c"},
        ),
        row=2, col=1,
    )
    fig.update_layout(
        title=f"{results.strategy_name} — {results.start} to {results.end}",
        height=700,
        showlegend=False,
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path


def render_greeks_over_time(results: "BacktestResults", out_path: str | Path) -> Path:
    """Render net delta/theta/vega over time."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    daily = results.daily
    if not daily:
        raise ValueError("no daily snapshots to plot")

    dates = [d.date for d in daily]
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=("Portfolio delta", "Portfolio theta (per day)", "Portfolio vega"),
    )
    fig.add_trace(go.Scatter(x=dates, y=[d.delta for d in daily]), row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=[d.theta for d in daily]), row=2, col=1)
    fig.add_trace(go.Scatter(x=dates, y=[d.vega for d in daily]), row=3, col=1)
    fig.update_layout(
        title=f"{results.strategy_name} — portfolio greeks", height=800, showlegend=False
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path
