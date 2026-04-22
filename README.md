# thetakit

Open source premium-selling backtest toolkit for serious retail options traders.

Author your strategies in a YAML DSL, validate them, backtest with realistic
fills and portfolio-level Greeks, and drive the whole thing from an MCP
tool surface so any MCP-compatible agent (Claude Code, Cowork, Claude
Desktop) can run it conversationally.

> **Status:** Phase 1 scaffolded end-to-end. See [docs/roadmap.md](docs/roadmap.md)
> for the full product plan, [docs/spec-phase-1.md](docs/spec-phase-1.md) for
> the authoritative spec, and [ARCHITECTURE.md](ARCHITECTURE.md) for
> contributor-facing module layout.

---

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# See bundled strategy templates
thetakit templates

# Validate a rule file
thetakit validate src/thetakit/templates/wheel.yaml

# Run a backtest on synthetic data (no vendor credentials needed)
thetakit backtest src/thetakit/templates/wheel.yaml \
  --universe SPY,QQQ,IWM --from 2024-01-01 --to 2024-06-30 \
  --report wheel_report.html

# Plot equity / greeks for a handle from the last backtest
thetakit plot <handle> --output equity.html
thetakit plot <handle> --output greeks.html --greeks
```

Or from Python ([examples/wheel_quickstart.py](examples/wheel_quickstart.py)):

```python
from datetime import date
from thetakit.dsl import load_strategy, get_template
from thetakit.engine.backtest import run_backtest, BacktestOptions
from thetakit.data.synthetic import SyntheticDataAdapter

strategy = load_strategy(get_template("wheel"))
adapter = SyntheticDataAdapter(
    symbols=["SPY", "QQQ", "IWM"],
    start=date(2024, 1, 1), end=date(2024, 6, 30),
)
results = run_backtest(strategy, adapter, date(2024, 1, 1), date(2024, 6, 30))
print(results.summarize_for_llm())
```

## What it does

- **Author strategies declaratively.** A Pydantic-validated YAML DSL with
  template inheritance (`extends: wheel`). Entry criteria (delta/DTE/IV
  rank, event-proximity filters), position sizing, roll triggers, exit
  rules, portfolio risk constraints.
- **Backtest honestly.** Daily-bar engine with configurable slippage,
  intraday-tested-strike penalty on rolls, profit-target / DTE-close /
  stop-loss exits, portfolio-level Greeks at every daily snapshot.
- **Expose an MCP tool surface.** `validate_rule`, `run_backtest`,
  `summarize_backtest`, `get_trade_log`, `get_calendar_events`. Every tool
  also works as plain Python, so the CLI and tests drive the same code
  paths as the MCP host.
- **Report.** Equity curves, drawdown, portfolio greek over time, summary
  stats (Sharpe, Sortino, max drawdown, win rate, profit factor) rendered
  to interactive Plotly HTML.

## What it explicitly doesn't do (yet)

- No live trading, broker integration, or order routing. Research tool only.
- No HMM / distributional / regime-aware evaluation. That's deliberate —
  see [docs/roadmap.md](docs/roadmap.md) for the open/proprietary split.
- No web UI. CLI + MCP + HTML reports.
- No intraday granularity. Daily-close rolls with an intraday-test
  approximation.

## Bundled templates

| Name | Strategy | Purpose |
|------|----------|---------|
| `wheel` | CSP | Classic Wheel: 0.30Δ, 45 DTE, 50% profit target, roll at 21 DTE |
| `iron_condor_spy` | IronCondor | 0.15Δ per side, $10 wings, 45 DTE |
| `credit_spread_equities` | BullPutSpread | 0.25Δ short, $5 wings on liquid large-caps |
| `covered_call_basic` | CC | 0.30Δ calls, 35 DTE, 50% profit, roll at 14 DTE |
| `csp_dividend_stocks` | CSP | 0.25Δ puts on dividend aristocrats |

Discover via `thetakit templates`; print raw YAML via `thetakit show <name>`.

## Project layout

```
src/thetakit/
  dsl/           Pydantic schema + YAML loader + semantic validator
  templates/     Bundled strategy YAMLs
  pricing/       Black-Scholes, IV solver, American-exercise heuristic
  engine/        Portfolio, positions, rolls, events, backtest loop
  data/          DataAdapter protocol + synthetic / parquet / vendor stub
  reporting/     Summary stats, plotly plots, HTML report
  mcp_server/    Framework-neutral tool impls + MCP SDK wrapper
  skill/         SKILL.md — conversational playbook for MCP hosts
  cli.py         typer CLI
tests/
  unit/          DSL, pricing, engine components
  integration/   End-to-end backtest via MCP tool layer
docs/            Roadmap + phase specs + architecture
examples/        Quickstart scripts
```

## Scripts from the earlier exploratory phase

The [src/](src/) directory also contains three data-download scripts
([fetch_contracts.py](src/fetch_contracts.py), [download_slv_options.py](src/download_slv_options.py),
[download_slv_flatfiles.py](src/download_slv_flatfiles.py)) from the SLV
covered-call exploration that kicked this project off. They are not part
of the `thetakit` package but remain in the repo as a worked example of
pulling options chain + bar data from Massive.com (Polygon.io). The SLV
strategy is the first real-world validation target; the contracts and
bars those scripts fetch will feed the `LocalParquetAdapter` once a
converter is written.

## Honest caveats

- **Synthetic data produces unrealistically clean backtest returns.** The
  synthetic adapter exists so tests and CI run offline; real analysis
  needs a real adapter.
- **Cash settlement only.** Short puts don't yet create long-stock
  positions on assignment; covered calls don't yet transfer shares on
  assignment. The engine books cash P&L correctly but share mechanics
  are a separate layer.
- **Single position per symbol.** Entry loop opens one position per
  underlying at a time to avoid naive over-concentration; expanding this
  needs richer sizing rules than the DSL currently expresses.

Full contributor docs: [ARCHITECTURE.md](ARCHITECTURE.md) · [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Apache 2.0. See [LICENSE](LICENSE).
