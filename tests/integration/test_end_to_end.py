"""End-to-end: run a full backtest on synthetic data via the MCP tool layer."""

from __future__ import annotations

from datetime import date

import pytest

from thetakit.data.synthetic import SyntheticDataAdapter
from thetakit.dsl import get_template, load_strategy
from thetakit.engine.backtest import BacktestOptions, run_backtest
from thetakit.mcp_server.tools import (
    clear_cache,
    get_backtest_results,
    get_trade_log,
    list_templates_tool,
    run_backtest_tool,
    summarize_backtest,
    validate_rule,
)


@pytest.fixture(autouse=True)
def _clear() -> None:
    clear_cache()


class TestMCPToolSurface:
    def test_validate_rule_accepts_bundled_template(self) -> None:
        result = validate_rule(get_template("wheel"))
        assert result["valid"] is True
        assert result["strategy_type"] == "CSP"

    def test_validate_rule_rejects_broken_yaml(self) -> None:
        result = validate_rule("name: bad\nentry: [not, a, mapping]")
        assert result["valid"] is False
        assert result["errors"]

    def test_list_templates_returns_all_five(self) -> None:
        names = {t["name"] for t in list_templates_tool()}
        assert {
            "wheel", "iron_condor_spy", "credit_spread_equities",
            "covered_call_basic", "csp_dividend_stocks",
        }.issubset(names)

    def test_run_backtest_completes_on_synthetic_data(self) -> None:
        yaml_text = get_template("wheel")
        result = run_backtest_tool(
            yaml_text,
            universe=["SPY", "QQQ", "IWM"],
            start="2024-01-01",
            end="2024-01-31",
        )
        assert result["status"] == "complete"
        assert result["handle"]
        handle = result["handle"]

        summary = summarize_backtest(handle)
        assert "Wheel" in summary["summary_text"]

        details = get_backtest_results(handle)
        assert details["stats"]["total_trades"] >= 0

    def test_get_trade_log_filter(self) -> None:
        result = run_backtest_tool(
            get_template("wheel"),
            universe=["SPY"],
            start="2024-01-01",
            end="2024-01-15",
        )
        handle = result["handle"]
        opens = get_trade_log(handle, kind="open")
        for e in opens:
            assert e["kind"] == "open"


class TestBacktestDeterminism:
    def test_same_seed_same_result(self) -> None:
        def one_run() -> float:
            adapter = SyntheticDataAdapter(
                symbols=["SPY"],
                start=date(2024, 1, 1),
                end=date(2024, 2, 15),
                initial_price={"SPY": 450},
                seed=7,
            )
            strat = load_strategy(get_template("wheel"))
            r = run_backtest(
                strat, adapter, date(2024, 1, 1), date(2024, 2, 15),
                BacktestOptions(initial_capital=100_000),
            )
            return r.final_equity

        a = one_run()
        b = one_run()
        assert a == b
