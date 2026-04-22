# thetakit architecture

This is a living reference for contributors. It explains the module
boundaries, key design decisions, and how to extend the most common
surfaces (new data adapters, new strategy types). For the full Phase 1
product spec see [docs/spec-phase-1.md](docs/spec-phase-1.md).

## Module layout

```
src/thetakit/
  dsl/           # Pydantic schema + YAML loader + semantic validator
  templates/     # Bundled YAML strategy templates (loaded via importlib.resources)
  pricing/       # Black-Scholes, IV solver, American-exercise heuristic
  engine/        # Portfolio state, position lifecycle, rolls, events, backtest loop
  data/          # DataAdapter protocol + synthetic / parquet / vendor-stub impls
  reporting/     # Summary stats, plotly charts, HTML report
  mcp_server/    # Framework-neutral tool implementations + MCP SDK wrapper
  skill/         # SKILL.md — conversational playbook for MCP hosts
  cli.py         # typer-based command-line
```

## The contract that glues the pieces together

The engine is a **pure function**: `run_backtest(strategy, data, start, end, options) -> results`.
- `strategy` is a validated `thetakit.dsl.Strategy`.
- `data` is any object satisfying the `DataAdapter` protocol.
- `results` is a `BacktestResults` value object.

No filesystem, no network, no global state. That is what lets the same
engine run from a CLI call, from pytest, from the MCP server, and later
from a queued job in Phase 2.

## DSL → Strategy

`dsl.schema` contains Pydantic v2 models. `dsl.loader` reads YAML, resolves
`extends: <template-name>` by merging parent fields (child keys override,
scalar values replace lists wholesale), and re-validates against the
schema. `dsl.validator` runs extra semantic checks (delta sanity per
strategy type, exit consistency, symbol list non-empty, etc.) and
distinguishes errors from warnings. Warnings surface but don't fail unless
`--strict` is set.

Extending the DSL with a new strategy type:
1. Add a new `StrategyType` enum value in `dsl/schema.py`.
2. If the new strategy needs unique fields (e.g., a butterfly needs two
   wing widths), extend `EntryRule` with optional fields and a
   `model_validator` that enforces presence for that type.
3. Add a handler branch in `engine/entry.py::find_entry`.
4. Add a bundled template under `templates/`.
5. Add unit tests.

## Engine loop

Implemented in `engine/backtest.py` following the spec's day-loop pseudocode:
1. Mark-to-market existing positions.
2. Process expirations / assignments (cash-settled for Phase 1).
3. Run exit checks (profit target, DTE close, stop loss).
4. Run roll checks (short-strike-tested, delta breach, DTE threshold).
5. Apply calendar vetoes (earnings/FOMC/CPI/ex-div proximity).
6. Find and open new entries within risk limits.
7. Snapshot portfolio greeks.

### Fill modeling

Default: fill at `mid ± (spread_pct × half_spread)` with `spread_pct = 0.4`.
When a roll fires from an intraday strike test, slippage is multiplied by
`intraday_roll_penalty` (default 1.1). If a quote carries no bid/ask, a
synthetic `5%` spread is imposed. These defaults are configurable on
`BacktestOptions` and `FillModel`.

### Greeks

Per-position greeks are computed in `engine/greeks.py` by BSM-pricing each
leg at the daily close with `default_sigma` (or a ticker-level override
map, if provided). Portfolio greeks are the signed sum across legs and
positions. The engine does not attempt to use vendor-reported IV unless the
adapter populates `OptionQuote.implied_volatility`.

### Assignment

Phase 1 uses cash settlement. Any ITM short leg on expiration flips the
position's status to `ASSIGNED`; the cash delta from settlement is booked.
Physical assignment and the corresponding underlying-share mechanics are
deferred to a later phase. An American early-exercise heuristic is in
`pricing/american.py` but is not yet wired into the daily loop — extension
point for future work.

## Data adapters

Implement the `DataAdapter` Protocol in `data/adapter.py`. Only the three
methods used by the engine are required:

- `get_trading_days(start, end)`
- `get_underlying_bar(symbol, on)`
- `get_option_chain(symbol, on, min_dte=, max_dte=, option_type=)`

`get_calendar_events` can delegate to `data.calendar.CalendarProvider`.

Shipped adapters:
- **SyntheticDataAdapter** — GBM prices + BSM-priced chains, seeded for
  determinism. Used for tests, CI, and local examples.
- **LocalParquetAdapter** — reads pre-downloaded Parquet files with a
  fixed directory convention. Works offline.
- **MarketDataAppAdapter** — stub. Completing it is a discrete contribution
  opportunity.

## MCP server

`mcp_server/tools.py` contains framework-neutral Python functions (no MCP
import). The CLI uses these directly. `mcp_server/server.py` wraps them
with `@server.tool()` decorators; it requires the optional `mcp` extra.
This split keeps the tools testable without the MCP runtime and keeps
the MCP dep off the critical path for contributors who don't care about
it.

Tool handles are opaque in-memory strings. Backtests are synchronous in
Phase 1 (everything completes in seconds on a laptop); Phase 2 will make
the handle persistent and add `wait=false` async semantics without
changing the surface.

## Known limits (honest list)

- **Synthetic data is clean.** Backtest returns on synthetic data will
  look unrealistically high. This is intentional — the synthetic path
  exists so tests and CI work offline. For any serious analysis, plug in
  a real adapter. The `SKILL.md` file tells LLM hosts to warn users about
  this.
- **Cash settlement only.** Covered calls do not yet move underlying
  shares; short puts don't yet create long-stock positions on assignment.
- **Daily-bar only.** Intraday rolls are approximated by looking at the
  daily high/low against the short strike. True intraday rolling needs
  minute-bar data (Phase 5+).
- **Single position per symbol.** The entry loop only opens one position
  per underlying at a time to avoid concentration errors. Removing this
  requires sizing rules the DSL doesn't yet express.
- **No IV surface modeling.** Greeks use a flat `default_sigma` or
  per-ticker overrides. Real vendor data can supply IV directly — hook
  it through `OptionQuote.implied_volatility`.
