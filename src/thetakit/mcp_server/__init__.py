"""MCP server — a stateless tool surface over the engine.

The actual MCP SDK is an optional dependency. `tools.py` exposes the tool
functions as plain Python so they're callable directly (from the CLI, from
tests, or from a host that embeds the server).
"""

from thetakit.mcp_server.tools import (
    BacktestHandle,
    get_backtest_results,
    get_backtest_status,
    get_calendar_events,
    get_template as get_template_tool,
    get_trade_log,
    list_templates as list_templates_tool,
    run_backtest_tool,
    summarize_backtest,
    validate_rule,
)

__all__ = [
    "BacktestHandle",
    "get_backtest_results",
    "get_backtest_status",
    "get_calendar_events",
    "get_template_tool",
    "get_trade_log",
    "list_templates_tool",
    "run_backtest_tool",
    "summarize_backtest",
    "validate_rule",
]
