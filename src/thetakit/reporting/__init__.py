"""Reporting — summary stats, plots, and HTML reports."""

from thetakit.reporting.summary import BacktestStats, compute_stats
from thetakit.reporting.plots import render_equity_curve, render_greeks_over_time
from thetakit.reporting.report import render_html_report

__all__ = [
    "BacktestStats",
    "compute_stats",
    "render_equity_curve",
    "render_greeks_over_time",
    "render_html_report",
]
