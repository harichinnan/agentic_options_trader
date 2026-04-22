"""Quickstart: run the Wheel template on synthetic SPY/QQQ/IWM data.

Run this from the repo root with:

    PYTHONPATH=src python examples/wheel_quickstart.py
"""

from datetime import date

from thetakit.data.synthetic import SyntheticDataAdapter
from thetakit.dsl import get_template, load_strategy
from thetakit.engine.backtest import BacktestOptions, run_backtest
from thetakit.reporting.report import render_html_report
from thetakit.reporting.summary import compute_stats


def main() -> None:
    # 1. Load the bundled Wheel template
    strategy = load_strategy(get_template("wheel"))

    # 2. Build a synthetic data adapter (no vendor credentials needed)
    adapter = SyntheticDataAdapter(
        symbols=["SPY", "QQQ", "IWM"],
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        initial_price={"SPY": 450, "QQQ": 380, "IWM": 190},
        annual_vol=0.22,
        seed=42,
    )

    # 3. Run the backtest
    results = run_backtest(
        strategy,
        adapter,
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        options=BacktestOptions(initial_capital=100_000),
    )

    # 4. Print a summary
    print(results.summarize_for_llm())
    stats = compute_stats(results)
    print(
        f"\n  Sharpe: {stats.sharpe:.2f}  "
        f"Win rate: {stats.win_rate:.1f}%  "
        f"Max DD: {stats.max_drawdown_pct:.2f}%"
    )

    # 5. Render an HTML report
    out = render_html_report(results, "wheel_quickstart_report.html")
    print(f"\nReport written to: {out}")
    print(
        "\nNote: synthetic data produces unrealistically clean returns. "
        "Plug in a real data adapter for meaningful analysis."
    )


if __name__ == "__main__":
    main()
