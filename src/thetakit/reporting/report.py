"""Single-page HTML report assembly."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from thetakit.reporting.summary import compute_stats

if TYPE_CHECKING:
    from thetakit.engine.backtest import BacktestResults


def render_html_report(results: "BacktestResults", out_path: str | Path) -> Path:
    """Render a full HTML report: summary stats + plots."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    stats = compute_stats(results)
    daily = results.daily
    dates = [d.date for d in daily]
    equity = [d.equity for d in daily]

    # Equity curve
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=dates, y=equity, name="Equity"))
    fig1.update_layout(title="Equity curve", height=350)
    equity_html = fig1.to_html(full_html=False, include_plotlyjs="cdn")

    # Greeks
    fig2 = make_subplots(
        rows=1, cols=3, subplot_titles=("Delta", "Theta (per day)", "Vega")
    )
    fig2.add_trace(go.Scatter(x=dates, y=[d.delta for d in daily]), row=1, col=1)
    fig2.add_trace(go.Scatter(x=dates, y=[d.theta for d in daily]), row=1, col=2)
    fig2.add_trace(go.Scatter(x=dates, y=[d.vega for d in daily]), row=1, col=3)
    fig2.update_layout(title="Portfolio greeks", height=350, showlegend=False)
    greeks_html = fig2.to_html(full_html=False, include_plotlyjs=False)

    # Trade log (last 50)
    rows = []
    for e in results.events[-50:]:
        rows.append(
            f"<tr><td>{e.date}</td><td>{e.kind}</td><td>{e.symbol}</td>"
            f"<td>{e.reason}</td><td>{(e.pnl or 0):.2f}</td></tr>"
        )
    trade_log_html = "<table class='tl'>" + "".join(rows) + "</table>"

    html = f"""<!doctype html>
<html><head>
<meta charset='utf-8'>
<title>{results.strategy_name} — thetakit report</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 24px; color: #222; }}
  h1 {{ margin: 0 0 6px; }}
  .sub {{ color: #666; margin-bottom: 18px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 18px 0; }}
  .stat {{ border: 1px solid #eee; padding: 10px; border-radius: 6px; }}
  .stat .k {{ color: #888; font-size: 12px; text-transform: uppercase; }}
  .stat .v {{ font-size: 22px; font-weight: 600; margin-top: 4px; }}
  table.tl {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.tl td {{ border-bottom: 1px solid #eee; padding: 4px 8px; }}
  section {{ margin: 28px 0; }}
</style>
</head><body>
<h1>{results.strategy_name}</h1>
<div class='sub'>{results.start} → {results.end} · {", ".join(results.universe)}</div>

<div class='stats'>
  <div class='stat'><div class='k'>Total return</div><div class='v'>{stats.total_return_pct:+.2f}%</div></div>
  <div class='stat'><div class='k'>CAGR</div><div class='v'>{stats.cagr_pct:+.2f}%</div></div>
  <div class='stat'><div class='k'>Sharpe</div><div class='v'>{stats.sharpe:.2f}</div></div>
  <div class='stat'><div class='k'>Max DD</div><div class='v'>{stats.max_drawdown_pct:.2f}%</div></div>
  <div class='stat'><div class='k'>Win rate</div><div class='v'>{stats.win_rate:.1f}%</div></div>
  <div class='stat'><div class='k'>Profit factor</div><div class='v'>{stats.profit_factor:.2f}</div></div>
  <div class='stat'><div class='k'>Trades</div><div class='v'>{stats.total_trades}</div></div>
  <div class='stat'><div class='k'>Avg DIT</div><div class='v'>{stats.avg_days_in_trade:.1f}d</div></div>
</div>

<section>{equity_html}</section>
<section>{greeks_html}</section>

<section>
  <h2>Recent events (last 50)</h2>
  {trade_log_html}
</section>
</body></html>
"""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
