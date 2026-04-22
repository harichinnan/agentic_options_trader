# Contributing to thetakit

Thanks for your interest. thetakit is still in early development; the
smallest, clearest PRs are the most likely to land quickly.

## Ground rules

- **Tests must pass.** `pytest` from the repo root.
- **No backtest-result regressions.** Snapshot tests for reference
  backtests fail loudly on engine changes. If a snapshot change is
  intentional, update it in the same PR and explain why.
- **Match existing style.** `ruff check` and `ruff format`. 100-char lines.
  Type hints on public APIs.
- **Docstrings on public functions** — a line or two explaining the
  purpose, not a recap of the signature.
- **No vendor credentials in the repo.** Ever.

## Getting set up

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Adding a new bundled template

1. Drop a `.yaml` file in `src/thetakit/templates/`.
2. Add a parametrized case in `tests/unit/test_dsl_loader.py` and
   `tests/unit/test_dsl_validator.py` so the template loads and validates
   cleanly.
3. Update the templates list in `README.md` if relevant.

## Adding a new data adapter

1. Implement the `DataAdapter` Protocol from `thetakit.data.adapter`.
   Only `get_trading_days`, `get_underlying_bar`, and `get_option_chain`
   are strictly required.
2. Include a small fixture dataset or a replay harness so contributors
   without vendor credentials can still run the tests.
3. Add an integration test that drives your adapter through a one-week
   backtest.

## PR expectations

- Include a test that would have failed before your change.
- Call out any changes to slippage, exit, or roll logic explicitly —
  these are load-bearing for backtest validity and need careful review.
- If your change affects the MCP tool surface, update `SKILL.md`.
- Mention any docs you updated or need to update.

## What is out of scope

- Live-trading or broker-integration PRs are not accepted. thetakit is
  a research toolkit; order routing is not on the roadmap.
- UI / web-dashboard PRs are out of scope for Phase 1.
- Distributional (Monte Carlo / HMM) evaluation belongs in the Phase 2
  proprietary service and is deliberately not accepted here.

## Reporting bugs

Include:
- Input rule YAML (minimally reproducible)
- Expected vs actual behavior
- Backtest window and symbols
- Python version and adapter in use
