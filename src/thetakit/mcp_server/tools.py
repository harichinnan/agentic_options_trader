"""Tool implementations, framework-neutral.

Each function takes primitive arguments (strings/dicts/numbers) so a thin
MCP server wrapper can expose them verbatim, and they also work as a
library for CLI and tests.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from thetakit.data.adapter import DataAdapter
from thetakit.data.synthetic import SyntheticDataAdapter
from thetakit.dsl import (
    StrategyLoadError,
    ValidationError,
    get_template,
    list_templates,
    load_strategy,
    validate_strategy,
)
from thetakit.engine.backtest import BacktestOptions, BacktestResults, run_backtest
from thetakit.reporting.summary import compute_stats


BacktestHandle = str

_CACHE: dict[BacktestHandle, BacktestResults] = {}


def _make_handle(rule_hash: str, universe: list[str], start: str, end: str) -> BacktestHandle:
    raw = f"{rule_hash}|{','.join(sorted(universe))}|{start}|{end}|{uuid.uuid4().hex[:8]}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def validate_rule(rule_yaml: str) -> dict[str, Any]:
    """Parse + semantically validate a rule file."""
    try:
        strat = validate_strategy(rule_yaml)
    except ValidationError as e:
        return {
            "valid": False,
            "errors": [{"path": i.path, "message": i.message, "severity": i.severity} for i in e.issues],
        }
    except StrategyLoadError as e:
        return {"valid": False, "errors": [{"path": "<root>", "message": str(e), "severity": "error"}]}
    return {
        "valid": True,
        "name": strat.name,
        "strategy_type": strat.entry.strategy.value,
        "delta_target": strat.entry.delta_target,
        "dte_target": strat.entry.dte_target,
    }


def list_templates_tool() -> list[dict[str, str]]:
    """Return bundled templates as [{name, strategy_type, description}]."""
    out: list[dict[str, str]] = []
    for name in list_templates():
        try:
            strat = load_strategy(get_template(name))
        except Exception:  # pragma: no cover
            continue
        out.append({
            "name": name,
            "strategy_type": strat.entry.strategy.value,
            "description": (strat.description or "").strip(),
        })
    return out


def get_template_tool(name: str) -> str:
    """Return raw YAML of a bundled template."""
    return get_template(name)


def _default_adapter(
    universe: list[str], start: str, end: str, seed: int = 42
) -> DataAdapter:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    return SyntheticDataAdapter(
        symbols=universe,
        start=start_d,
        end=end_d,
        seed=seed,
    )


def run_backtest_tool(
    rule_yaml: str,
    universe: list[str],
    start: str,
    end: str,
    options: dict[str, Any] | None = None,
    adapter: DataAdapter | None = None,
) -> dict[str, Any]:
    """Run a backtest synchronously. Returns handle + basic stats.

    In Phase 1, backtests complete in-process. The handle is opaque and
    can later be remapped to a persistent job id in Phase 2.
    """
    options = options or {}
    strat = validate_strategy(rule_yaml)
    # Override symbols if needed
    if isinstance(strat.entry.symbols, list) and universe:
        strat.entry.symbols = universe

    adapter = adapter or _default_adapter(universe, start, end)

    bt_options = BacktestOptions(
        initial_capital=options.get("initial_capital", strat.risk.initial_capital),
        spread_pct=options.get("spread_pct", 0.4),
        risk_free_rate=options.get("risk_free_rate", 0.04),
        default_sigma=options.get("default_sigma", 0.20),
    )

    results = run_backtest(
        strat, adapter, date.fromisoformat(start), date.fromisoformat(end), bt_options
    )

    rule_hash = hashlib.sha1(rule_yaml.encode()).hexdigest()[:10]
    handle = _make_handle(rule_hash, universe, start, end)
    _CACHE[handle] = results
    return {
        "handle": handle,
        "status": "complete",
        "strategy_name": results.strategy_name,
        "total_return_pct": results.total_return_pct,
        "final_equity": results.final_equity,
    }


def get_backtest_status(handle: BacktestHandle) -> dict[str, Any]:
    if handle not in _CACHE:
        return {"handle": handle, "status": "unknown"}
    return {"handle": handle, "status": "complete"}


def get_backtest_results(handle: BacktestHandle) -> dict[str, Any]:
    results = _CACHE.get(handle)
    if results is None:
        raise KeyError(f"unknown handle: {handle}")
    stats = compute_stats(results)
    return {
        "handle": handle,
        "strategy_name": results.strategy_name,
        "start": results.start,
        "end": results.end,
        "universe": results.universe,
        "stats": asdict(stats),
        "final_equity": results.final_equity,
        "initial_capital": results.initial_capital,
        "event_count": len(results.events),
        "closed_position_count": len(results.closed_positions),
    }


def summarize_backtest(handle: BacktestHandle) -> dict[str, Any]:
    results = _CACHE.get(handle)
    if results is None:
        raise KeyError(f"unknown handle: {handle}")
    stats = compute_stats(results)
    return {
        "summary_text": (
            results.summarize_for_llm()
            + f"\n  sharpe: {stats.sharpe:.2f}  max dd: {stats.max_drawdown_pct:.2f}%  "
            f"win rate: {stats.win_rate:.1f}%"
        ),
        "stats": asdict(stats),
    }


def get_trade_log(
    handle: BacktestHandle, kind: str | None = None, symbol: str | None = None, limit: int = 500
) -> list[dict[str, Any]]:
    results = _CACHE.get(handle)
    if results is None:
        raise KeyError(f"unknown handle: {handle}")
    events = results.events
    if kind:
        events = [e for e in events if e.kind == kind]
    if symbol:
        events = [e for e in events if e.symbol == symbol]
    out = []
    for e in events[-limit:]:
        out.append({
            "date": e.date,
            "kind": e.kind,
            "symbol": e.symbol,
            "strategy": e.strategy,
            "reason": e.reason,
            "fill_price": e.fill_price,
            "pnl": e.pnl,
            "legs": [
                {
                    "type": leg.option_type,
                    "strike": leg.strike,
                    "expiration": leg.expiration,
                    "side": leg.side,
                    "qty": leg.quantity,
                }
                for leg in e.legs
            ],
        })
    return out


def get_calendar_events(
    symbols: list[str] | None, start: str, end: str, event_types: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return calendar events in a date range (uses the default synthetic calendar)."""
    from thetakit.data.calendar import CalendarProvider

    cal = CalendarProvider.default()
    events = cal.events_in_range(
        date.fromisoformat(start),
        date.fromisoformat(end),
        symbols=symbols,
        event_types=event_types,
    )
    return [
        {"date": e.date, "event_type": e.event_type, "symbol": e.symbol, "detail": e.detail}
        for e in events
    ]


def clear_cache() -> None:
    """Test helper: clear the in-memory handle cache."""
    _CACHE.clear()


# ---- Phase 2 hosted-eval tools ----------------------------------------------
# These are gated on the presence of thetakit-cloud-client + credentials file.
# If either is missing, the tool returns a clear not_configured response so the
# MCP host can fall back to local backtests gracefully.


def _cloud_or_none():
    try:
        from thetakit_cloud_client import CloudClient, load_credentials  # type: ignore[import-not-found]
    except ImportError:
        return None
    creds = load_credentials()
    if creds is None:
        return None
    return CloudClient(api_key=creds.api_key, base_url=creds.base_url)


def run_smoke_eval(
    rule_yaml: str, universe: list[str], start: str, end: str
) -> dict[str, Any]:
    """Submit a hosted smoke eval. Returns {'handle', 'status', 'eval_type'}."""
    from datetime import date as _date  # noqa: PLC0415

    client = _cloud_or_none()
    if client is None:
        return {
            "error": "not_configured",
            "detail": (
                "thetakit-cloud is not configured. Run `thetakit auth --key <key>` "
                "after provisioning an API key in the hosted service."
            ),
        }
    return client.run_smoke_eval(
        rule_yaml=rule_yaml, universe=universe,
        start=_date.fromisoformat(start), end=_date.fromisoformat(end),
    )


def run_full_eval(
    rule_yaml: str, universe: list[str], start: str, end: str
) -> dict[str, Any]:
    """Submit a hosted full eval."""
    from datetime import date as _date  # noqa: PLC0415

    client = _cloud_or_none()
    if client is None:
        return {"error": "not_configured"}
    return client.run_full_eval(
        rule_yaml=rule_yaml, universe=universe,
        start=_date.fromisoformat(start), end=_date.fromisoformat(end),
    )


def get_eval_status(handle: str) -> dict[str, Any]:
    client = _cloud_or_none()
    if client is None:
        return {"error": "not_configured"}
    return client.get_eval(handle)


def get_eval_results(handle: str) -> dict[str, Any]:
    """Alias for get_eval_status — hosted evals return full results from the same endpoint."""
    return get_eval_status(handle)


def summarize_eval(handle: str) -> dict[str, Any]:
    client = _cloud_or_none()
    if client is None:
        return {"error": "not_configured"}
    result = client.get_eval(handle)
    return {
        "summary_text": result.get("summary_text", ""),
        "stats": result.get("stats"),
        "status": result.get("status"),
    }
