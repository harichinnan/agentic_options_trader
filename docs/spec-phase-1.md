# Spec — Phase 1: Open Source Premium-Selling Backtest Toolkit

**Working name:** TBD (placeholder: `thetakit`)
**Phase:** 1 of 5 (per roadmap)
**Target ship:** Jun–Sep 2026
**Status:** Draft, intended to be buildable directly
**Audience:** Founder + 1 engineer, vibecoding from this doc

> This spec is deliberately written tight enough to code from. It scopes only the Phase 1 open source MVP. The proprietary HMM eval service (Phase 2), conversational rule authoring as a first-class experience (Phase 3), and directory distribution (Phase 4) are explicitly **not** in scope here, though the architecture must not preclude them.

---

## 1. Problem Statement

Serious retail options traders who run systematic premium-selling playbooks (the Wheel, defined-risk spreads, 45 DTE / 0.35 delta rule sets) have no good open source toolkit for authoring, validating, and backtesting their rules. Existing tools are either closed platforms with opinionated workflows (Option Alpha, Tastytrade), Python-quant frameworks that require writing strategies in code (QuantConnect, backtrader), or spreadsheet-and-brain setups that do not scale past a handful of positions. The gap is a developer-friendly, rule-first toolkit that takes a structured premium-selling strategy and runs an honest historical backtest against it, with calendar-aware context (earnings, Fed, OPEX) and portfolio-level Greeks.

The cost of not solving it: a sophisticated retail audience that wants rigor but cannot afford institutional tools, makes decisions on gut + forum consensus. Bad outcomes are externalized to users; the tooling category stays stuck in 2018.

---

## 2. Goals

1. **Author and validate strategies declaratively.** Users can describe a complete premium-selling strategy in a YAML/JSON rule DSL that captures entry criteria, position sizing, roll logic, exit criteria, and risk constraints, with schema validation and clear error messages.
2. **Run honest historical backtests.** Given a rule set and a symbol universe, produce a backtest with realistic fills, path-dependent rolling logic, dividend/assignment handling, and portfolio-level Greek tracking. Output includes P&L curves, drawdown analysis, trade logs, and per-trade diagnostics.
3. **Ground strategies in real calendar context.** Backtests automatically overlay earnings dates, Fed FOMC days, OPEX, CPI releases, and ex-dividend dates so users can see how their strategy performed around known events and filter trades based on event proximity.
4. **Ship as an MCP tool surface.** All core capabilities are exposed via an MCP server so that any MCP-compatible host (Claude Code, Cowork, Claude Desktop, custom agents) can drive the workflow through tool calls. A minimal skill makes the conversational path work out-of-the-box.
5. **Build community credibility.** At ship, the repo contains 5+ fully-worked reference strategies with reproducible backtest results, contribution guidelines, and enough example documentation that a new user can run their first backtest in under 10 minutes.

---

## 3. Non-Goals

1. **No HMM / distributional evaluation / Monte Carlo.** Historical backtests only in Phase 1. The proprietary eval service is Phase 2, and shipping it in open source would leak the moat.
2. **No live trading, no broker integration, no order routing.** The toolkit is strictly research and analysis. No button that executes a trade.
3. **No conversational rule authoring as a first-class product.** The MCP exposes the tools, the skill gives a minimal conversational path, but the polished rule-authoring agent with memory and continuous tuning is Phase 3.
4. **No hosted service, no billing, no auth in Phase 1.** Everything runs locally. Users bring their own data vendor credentials. If someone wants hosted compute, that's Phase 2.
5. **No web UI.** Phase 1 is CLI + MCP tools. Charts render to file (PNG/HTML via Plotly) for inspection. A web UI is Phase 2.
6. **No non-US equity options, no futures options, no crypto.** US equity options on liquid names only. Scope expansion is a Phase 5+ bet.
7. **No intraday granularity for rolls.** Daily-close data only. Intraday is Phase 5+ because it requires different data vendors and significantly more compute.
8. **No tax reporting, no P&L accounting beyond backtest diagnostics.** This is a backtest tool, not a portfolio manager.

---

## 4. Target Users

**Primary persona — "The systematic premium seller"**
Retail options trader, 5+ years of experience, runs a disciplined Wheel or defined-risk credit spread playbook. Has 10–40 open positions at any time. Comfortable with the command line and Python. Reads r/thetagang, listens to Tastytrade content critically, and has probably hand-written spreadsheets to track Greeks before giving up on them. Values rigor, distrusts bullshit, and will walk away instantly if the tool produces results that look too good.

**Secondary persona — "The quant-curious retail trader"**
Software engineer or data scientist by day, options trader on the side. Knows Python well, can read backtest code, wants to tweak the engine. Values hackability and open source. Likely to become a contributor.

**Explicit non-persona for Phase 1:**
The conversational-only user who never touches a CLI. They are the target for Phase 3, not Phase 1.

---

## 5. User Stories

**Rule authoring**

- As a premium seller, I want to declare my strategy in a structured file (YAML) so that my rules are versionable, reviewable, and reproducible.
- As a premium seller, I want validation errors that tell me exactly what is missing or contradictory in my rule set so that I can fix issues without reading source code.
- As a premium seller, I want to inherit and override rule templates (e.g., start from a "Wheel" template and customize delta targets) so that I do not have to write every parameter from scratch.

**Backtest execution**

- As a premium seller, I want to run a backtest on my strategy against a symbol universe over a date range with one command so that I can iterate quickly.
- As a premium seller, I want realistic fill modeling (bid-ask slippage, not mid-price) so that the backtest numbers reflect what I would actually have achieved.
- As a premium seller, I want rolling logic to fire when positions are tested intraday, even though the engine uses daily data, so that I get a conservative approximation of my roll behavior.
- As a premium seller, I want the backtest to handle assignment, early exercise around dividends, and expiration correctly so that I am not silently benefiting from unrealistic assumptions.

**Diagnostics and output**

- As a premium seller, I want a full trade log showing every entry, roll, and exit with reasons so that I can audit the engine's decisions.
- As a premium seller, I want portfolio-level Greeks over time so that I can see how my net delta/vega/theta exposure evolved.
- As a premium seller, I want the backtest results overlaid with earnings, Fed, and OPEX dates so that I can see how my strategy performed around known events.
- As a premium seller, I want equity curves, drawdown plots, and a summary stats table rendered to file so that I can review results visually.

**Extensibility and integration**

- As a developer, I want every core capability exposed as an MCP tool so that I can drive the workflow from any MCP-compatible agent.
- As a developer, I want a clean data adapter interface so that I can plug in a new options data vendor without touching the backtest engine.
- As a developer, I want the engine to be importable as a Python library so that I can use it in my own scripts and notebooks.

---

## 6. Requirements

### 6.1 Must-Have (P0) — Ship Blockers

**Rule DSL and validation**

- YAML-based rule DSL with Pydantic schema validation. At minimum supports: entry criteria (delta range, DTE range, IV rank threshold, symbol filter, event proximity filter), position sizing (fixed contracts, % of buying power, Kelly-lite), roll triggers (short strike tested, delta breach, DTE threshold), exit criteria (profit target %, DTE threshold, stop loss), and global risk constraints (max concurrent positions, max capital per symbol, max portfolio delta).
- Rule templates shipped in `thetakit/templates/`: at minimum Wheel, IronCondor-SPY, CreditSpread-Equities, CoveredCall-Basic, CSP-Dividend-Stocks.
- Rule validation produces actionable error messages with file paths and line numbers.
- **Acceptance:** Given a rule file with a contradictory constraint (e.g., delta > 0.5 but strategy is CSP), when the user runs `thetakit validate my-rules.yaml`, then the CLI exits non-zero with a clear error pointing to the offending field.

**Historical backtest engine**

- Data adapter interface (`DataAdapter` protocol) supporting pluggable vendors. Ship with at least one working adapter (MarketData.app preferred; ORATS as stretch) and a local Parquet adapter for pre-downloaded data.
- Daily-bar backtest engine with: realistic fill modeling (bid-ask spread sampling, configurable slippage in cents or % of spread), position lifecycle tracking (open → roll → close), dividend and early-assignment handling for ITM calls around ex-div dates, expiration settlement (cash and physical).
- Rolling logic approximation for "tested intraday": flag a roll trigger when the daily bar's high or low crosses the short strike, with a penalty on the roll fill to reflect the fact you'd have rolled at a worse price than the close.
- Portfolio-level Greek aggregation: net delta, gamma, theta, vega, computed from per-position Greeks at each daily snapshot.
- Trade log: one row per position event (open, roll, close, assign, expire) with timestamp, symbol, strike, DTE, delta at event, fill price, reason, and running P&L.
- **Acceptance:** Given the Wheel template applied to SPY over 2019–2023, when the user runs `thetakit backtest strategies/wheel-spy.yaml`, then the engine produces a trade log, equity curve, drawdown series, and summary stats within 60 seconds on a laptop.

**Calendar augmentation**

- Built-in data sources for: US earnings calendar (per-symbol), FOMC calendar, major macro releases (CPI, NFP, PPI), quarterly OPEX dates, ex-dividend dates.
- Entry rules can filter by event proximity: `skip_if_earnings_within_days: 7`, `skip_if_fomc_within_days: 2`.
- Backtest output annotates the equity curve with event markers.
- **Acceptance:** Given a rule that says `skip_if_earnings_within_days: 7` applied to AAPL, when the backtest runs, then no position is opened on AAPL in the 7 days before each earnings release, and this is visible in the trade log (entries are logged as "skipped: earnings proximity").

**MCP tool surface**

- Python MCP server exposing these tools:
  - `validate_rule(rule_yaml: str) -> ValidationResult`
  - `list_templates() -> list[TemplateMeta]`
  - `get_template(name: str) -> str`
  - `run_backtest(rule_yaml: str, universe: list[str], start: date, end: date, options: BacktestOptions) -> BacktestHandle`
  - `get_backtest_status(handle: str) -> BacktestStatus`
  - `get_backtest_results(handle: str) -> BacktestResults`
  - `summarize_backtest(handle: str) -> BacktestSummary` (returns LLM-friendly text summary)
  - `get_trade_log(handle: str, filter: TradeLogFilter) -> list[TradeEvent]`
  - `get_calendar_events(symbols: list[str], start: date, end: date, event_types: list[str]) -> list[CalendarEvent]`
- MCP server runs over stdio by default (for local Claude Code / Cowork use) and optionally over SSE/HTTP for remote consumption.
- **Acceptance:** Given the MCP server is installed and configured in Claude Code, when the user asks "run the Wheel template on SPY from 2020 to 2023," then Claude can sequence `get_template` → `run_backtest` → `get_backtest_status` → `summarize_backtest` and present the results conversationally.

**CLI**

- `thetakit validate <file>` — validate a rule file
- `thetakit backtest <file> --universe SPY,QQQ --from 2019-01-01 --to 2023-12-31` — run a backtest
- `thetakit show <handle>` — print summary of a completed backtest
- `thetakit plot <handle> --output out.html` — render interactive plots (Plotly HTML)
- `thetakit templates` — list bundled templates

**Output and visualization**

- Equity curve, drawdown series, per-trade P&L histogram, net Greek exposure over time. Rendered to interactive Plotly HTML by default; PNG as option.
- Summary stats table: total return, CAGR, Sharpe, Sortino, max drawdown, drawdown duration, win rate, avg win/loss, profit factor, number of trades, avg DTE, avg days in trade.

**Testing**

- Unit tests for rule DSL parsing and validation (>90% coverage on the DSL module).
- Integration tests for the backtest engine: a small set of known strategies on known periods with snapshot-tested outputs. Changes to these snapshots require explicit review.
- A "reference backtest" suite that runs the 5 shipped templates on fixed universes and date ranges, locked to specific output hashes. Any change to the engine that affects results breaks these tests and requires an intentional update.

**Docs and community**

- README with 10-minute quickstart (install → run a bundled template → read results)
- ARCHITECTURE.md explaining the module boundaries and how to add a data adapter
- CONTRIBUTING.md with test requirements and PR expectations
- 5 worked example strategies with results committed to the repo
- Apache 2.0 license

### 6.2 Nice-to-Have (P1) — Ship If Time Permits

- A `thetakit report` command that generates a single HTML report with all plots, summary, and trade log.
- Configurable slippage models (fixed cents, % of spread, empirical from historical fills).
- Walk-forward optimization helper (grid search over rule parameters with out-of-sample testing).
- Jupyter integration: notebook-friendly `BacktestResults` object with nice repr.
- Second data adapter (ORATS or CBOE) shipped alongside MarketData.app.
- GitHub Actions CI running the reference backtest suite on every PR.

### 6.3 Future Considerations (P2) — Explicitly Out of Scope, Design For

- Remote backtest execution (Phase 2): the engine should be callable as a pure function `run_backtest(rules, data, options) -> results` with no filesystem assumptions so that Phase 2 can trivially wrap it in a job queue.
- Distributional evaluation (Phase 2): the core engine should accept an arbitrary sequence of price paths, not just historical data. That keeps the door open for Monte Carlo without rewriting the engine.
- Persistent rule version history (Phase 3): rule files should be content-addressable (hash-based IDs) so Phase 3 can build git-like versioning on top without re-engineering.
- Continuous tuning agent (Phase 3): the MCP tool surface should be stable so the agent in Phase 3 can rely on it.

---

## 7. Architecture and Technical Design

This section exists because the user asked for a vibecode-ready spec. Make these choices, don't second-guess them in implementation unless something breaks.

### 7.1 Platform and Stack

- **Language:** Python 3.12
- **Package management:** `uv` (fast, modern, lockfile-based)
- **Project layout:** Single monorepo, src-layout, installable as `thetakit`
- **Data processing:** `polars` as the primary DataFrame library. Faster than pandas for time series and has a cleaner API. Pandas is allowed at adapter boundaries for compatibility.
- **Schema and validation:** `pydantic` v2 for all data models and rule DSL schemas.
- **CLI:** `typer` (built on click, clean type-hint-driven API).
- **Options pricing and Greeks:** `py_vollib_vectorized` for Black-Scholes Greeks. Custom binomial for American-exercise early assignment logic around dividends.
- **Statistics:** `scipy.stats`, `numpy`. Avoid heavy stats libraries until needed.
- **Plotting:** `plotly` (interactive HTML), `kaleido` for static PNG export.
- **MCP server:** Official `mcp` Python SDK (`mcp` package from Anthropic).
- **Configuration:** `pydantic-settings` for env-based config.
- **Testing:** `pytest`, `pytest-snapshot` for reference backtests, `hypothesis` for property tests on the rule DSL.
- **Code quality:** `ruff` for linting and formatting, `pyright` for type checking.
- **Docs:** `mkdocs-material` for the website, docstrings rendered via `mkdocstrings`.

**Deliberately NOT in the stack for Phase 1:**

- **LangGraph** — see Section 7.6 for the detailed reasoning. Short answer: LangGraph is for orchestrating stateful agent loops. In Phase 1, the agent loop lives in the MCP host (Claude), not in the server. The MCP server is a stateless tool surface. LangGraph becomes useful in Phase 2+ when we run our own agent runtime in the hosted product. Adding it now is premature.
- **LangChain** — same reason. The MCP SDK gives us all the tool machinery we need.
- **FastAPI / web framework** — Phase 1 is CLI + MCP only. No HTTP service.
- **Database** — Phase 1 uses the filesystem. Parquet files for data, JSON/YAML for rules, pickle or Parquet for cached backtest results. Phase 2 adds Postgres.
- **Task queue** — Phase 1 runs backtests inline (they complete in seconds to minutes on a laptop). Phase 2 adds Celery/Modal/Dramatiq.
- **pandas as primary** — use polars unless an adapter forces pandas at the edge.

### 7.2 Repository Structure

```
thetakit/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE (Apache 2.0)
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── src/
│   └── thetakit/
│       ├── __init__.py
│       ├── cli.py                      # typer entry point
│       ├── dsl/
│       │   ├── __init__.py
│       │   ├── schema.py               # Pydantic models for Rule, Entry, Roll, Exit, Risk
│       │   ├── loader.py               # YAML parsing, template inheritance
│       │   └── validator.py            # cross-field validation, semantic checks
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── backtest.py             # main run_backtest function
│       │   ├── portfolio.py            # Portfolio state, position tracking
│       │   ├── position.py             # Position lifecycle
│       │   ├── fills.py                # slippage and fill modeling
│       │   ├── rolls.py                # roll trigger logic
│       │   ├── greeks.py               # Greek aggregation
│       │   └── events.py               # expiration, assignment, dividends
│       ├── data/
│       │   ├── __init__.py
│       │   ├── adapter.py              # DataAdapter protocol
│       │   ├── marketdata_app.py       # MarketData.app adapter
│       │   ├── local_parquet.py        # local file adapter
│       │   └── calendar.py             # earnings, Fed, OPEX, dividends
│       ├── pricing/
│       │   ├── __init__.py
│       │   ├── bsm.py                  # Black-Scholes wrappers
│       │   └── american.py             # binomial for early exercise
│       ├── mcp_server/
│       │   ├── __init__.py
│       │   ├── server.py               # MCP server, tool definitions
│       │   └── tools.py                # thin wrappers over engine
│       ├── skill/                      # skill files for bundled conversational path
│       │   └── SKILL.md
│       ├── templates/
│       │   ├── wheel.yaml
│       │   ├── iron_condor_spy.yaml
│       │   ├── credit_spread_equities.yaml
│       │   ├── covered_call_basic.yaml
│       │   └── csp_dividend_stocks.yaml
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── plots.py                # plotly charts
│       │   ├── summary.py              # stats tables
│       │   └── report.py               # HTML report assembly
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── reference_backtests/            # snapshot-tested reference runs
├── examples/
│   ├── wheel_on_spy.ipynb
│   └── ...
└── docs/
    └── mkdocs.yml
```

### 7.3 Core Data Models (Pydantic Sketches)

```python
class EntryRule(BaseModel):
    strategy: Literal["CSP", "CC", "BullPutSpread", "BearCallSpread", "IronCondor"]
    delta_target: float = Field(..., ge=0.05, le=0.5)
    delta_tolerance: float = 0.05
    dte_target: int = Field(..., ge=7, le=90)
    dte_tolerance: int = 7
    min_iv_rank: float | None = None
    symbols: list[str] | SymbolFilter
    skip_if_earnings_within_days: int | None = None
    skip_if_fomc_within_days: int | None = None

class PositionSizing(BaseModel):
    mode: Literal["fixed_contracts", "pct_bp", "kelly_lite"]
    contracts: int | None = None
    pct_bp: float | None = None

class RollRule(BaseModel):
    trigger: Literal["short_strike_tested", "delta_breach", "dte_threshold"]
    delta_threshold: float | None = None
    dte_threshold: int | None = None
    target_dte: int = 45
    target_delta: float = 0.35

class ExitRule(BaseModel):
    profit_target_pct: float = 0.5  # close at 50% of max profit
    dte_close: int = 21
    stop_loss_multiplier: float | None = None  # e.g., 2x credit received

class RiskConstraints(BaseModel):
    max_concurrent_positions: int = 20
    max_capital_per_symbol_pct: float = 0.1
    max_portfolio_delta: float | None = None
    max_portfolio_vega: float | None = None

class Strategy(BaseModel):
    name: str
    description: str | None = None
    extends: str | None = None  # template inheritance
    entry: EntryRule
    sizing: PositionSizing
    rolls: list[RollRule]
    exits: list[ExitRule]
    risk: RiskConstraints
```

### 7.4 Backtest Engine Execution Flow

The engine is a deterministic, single-threaded, event-loop walker over daily bars. Pseudocode:

```
def run_backtest(strategy, data, start, end, options):
    portfolio = Portfolio(initial_capital=options.capital)
    trade_log = []
    daily_state = []

    for day in trading_days(start, end):
        market_snapshot = data.get_snapshot(day)                   # prices, IV, chains
        calendar_context = data.get_calendar(day, strategy.symbols) # events

        # 1. Mark-to-market existing positions
        portfolio.mark(market_snapshot)

        # 2. Process expirations and assignments from previous day
        for event in portfolio.process_expirations(day):
            trade_log.append(event)

        # 3. Check exits (profit target, DTE close, stop loss)
        for position in portfolio.open_positions:
            if exit_triggered(position, strategy.exits):
                event = portfolio.close(position, fill_price=modeled_fill(position, market_snapshot))
                trade_log.append(event)

        # 4. Check rolls (tested, delta breach, DTE threshold)
        for position in portfolio.open_positions:
            if roll_triggered(position, strategy.rolls, market_snapshot):
                event = portfolio.roll(position, strategy.rolls, market_snapshot, calendar_context)
                trade_log.append(event)

        # 5. Check risk constraints before opening new positions
        if portfolio.within_risk_limits(strategy.risk):
            candidates = find_entries(strategy.entry, market_snapshot, calendar_context)
            for candidate in candidates:
                if portfolio.can_open(candidate, strategy.risk):
                    event = portfolio.open(candidate)
                    trade_log.append(event)

        # 6. Snapshot daily state
        daily_state.append(portfolio.snapshot(day))

    return BacktestResults(
        trade_log=trade_log,
        daily_state=daily_state,
        strategy=strategy,
        options=options,
    )
```

**Critical implementation notes for vibecoding:**

- The `run_backtest` function must be pure: inputs in, outputs out, no filesystem, no network. All I/O happens in the data adapter passed in. This is what lets Phase 2 wrap it in a job queue without refactoring.
- `Portfolio` is the state container. All mutations go through `Portfolio` methods so state transitions are auditable.
- `modeled_fill()` is where slippage logic lives. Default: fill at `mid ± (spread_pct * bid_ask_spread / 2)` where spread_pct defaults to 0.4 (i.e., you cross 40% of the spread). Configurable per backtest.
- Roll trigger "short strike tested" looks at the daily bar high/low, not close. When a roll triggers from an intraday test, apply an additional penalty to the fill (configurable, default +10% to the slippage).
- Greek calculation: batch-compute per-position Greeks with py_vollib_vectorized at each daily snapshot, then aggregate. Caching IV surfaces per day is important for performance.

### 7.5 MCP Server Design

The MCP server is a **stateless tool surface** over the engine. It holds no long-lived state beyond an in-memory cache of recent backtest results keyed by handle. If the server restarts, handles are lost (Phase 1 acceptable; Phase 2 adds persistence).

```python
# mcp_server/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("thetakit")

_backtest_cache: dict[str, BacktestResults] = {}

@server.tool()
async def validate_rule(rule_yaml: str) -> dict:
    try:
        strategy = load_strategy(rule_yaml)
        return {"valid": True, "summary": strategy.name}
    except ValidationError as e:
        return {"valid": False, "errors": format_errors(e)}

@server.tool()
async def run_backtest(
    rule_yaml: str,
    universe: list[str],
    start: str,  # ISO date
    end: str,
    options: dict | None = None,
) -> dict:
    strategy = load_strategy(rule_yaml)
    data = get_default_adapter()  # or from options
    results = run_backtest_impl(strategy, data, parse_date(start), parse_date(end), options or {})
    handle = make_handle(results)
    _backtest_cache[handle] = results
    return {"handle": handle, "status": "complete"}

@server.tool()
async def summarize_backtest(handle: str) -> dict:
    results = _backtest_cache[handle]
    return {
        "summary_text": results.summarize_for_llm(),  # plain English
        "stats": results.stats.model_dump(),
    }
```

**Why backtests return synchronously in Phase 1:** Laptop backtests on 5 symbols over 5 years complete in under 60 seconds. That fits inside an MCP tool timeout. Phase 2 introduces async handles because hosted Monte Carlo eval takes minutes. The Phase 1 API shape already uses handles precisely so Phase 2 can introduce status polling without breaking anything.

The bundled skill (shipped in `src/thetakit/skill/SKILL.md`) tells Claude how to sequence these tools conversationally, how to handle validation errors, and how to present summaries. It's intentionally thin in Phase 1 — the polished conversational product is Phase 3.

### 7.6 On LangGraph: Is It Useful Here?

Short answer: **no in Phase 1, yes in Phase 2+, and being clear about why matters.**

LangGraph is a framework for building stateful, multi-step agent workflows with explicit graph structure, persistent checkpointing, and human-in-the-loop support. It shines when you are running your own agent loop — orchestrating a sequence of LLM calls and tool invocations with state that persists across turns and survives restarts.

In Phase 1, **the agent loop does not live in our code at all**. It lives in the MCP host (Claude Code, Cowork, Claude Desktop). Our MCP server exposes tools; the host decides when to call them, passes context between calls, and handles the conversation. We provide a skill to guide the host's behavior, but we are not running an agent runtime ourselves. Adding LangGraph to the MCP server in Phase 1 would mean building a second, parallel agent loop that fights the host for control. That is strictly worse than the MCP-native pattern: more code, more failure modes, duplicated state, and it does not buy us anything the host cannot already do.

In Phase 2 (the hosted evaluation service with its own web UI), **we will run our own agent runtime**, because the conversation happens in our app and we need full control over state, memory, billing events, and async backtest status. This is where LangGraph earns its keep:

- **State machine for rule authoring:** gather → propose → validate → backtest → review → iterate. Each node can have its own prompt, tools, and exit conditions. LangGraph's checkpointing lets us resume a multi-turn rule authoring session days later.
- **Async backtest orchestration:** a long-running full HMM eval takes minutes. LangGraph handles the "fire job, persist state, wake up when done, resume the conversation" pattern cleanly.
- **Human-in-the-loop approval gates:** "commit this rule version to your live strategy set? y/n" — this is LangGraph's wheelhouse.
- **Multi-agent composition:** if we later split rule authoring, risk narration, and calibration tracking into specialized sub-agents, LangGraph is the right orchestration layer.

The Phase 1 decision that matters here: **design the MCP tool surface so the Phase 2 LangGraph agent can consume it unchanged.** That means tool names, argument shapes, and handle-based async semantics should be stable. Concretely:

- Tools accept primitive arguments (strings, numbers, dicts), not Python-specific types.
- Handles are opaque strings the server can later remap to persisted job IDs.
- Every tool that can be slow accepts a `wait: bool` argument (defaulted true in Phase 1 since everything is fast, defaulted false in Phase 2 for async jobs).
- Summarization tools return both structured data and an LLM-friendly text summary so the agent can choose.

This is the discipline that lets Phase 2 add LangGraph without re-architecting the server. Do not skip it.

### 7.7 Data Handling

- **Historical options data:** bring-your-own vendor credentials (MarketData.app or ORATS). Cache fetched data to local Parquet files under `~/.thetakit/cache/` keyed by symbol + date range. Never re-fetch what is already cached.
- **Calendar data:** bundled static datasets for historical FOMC, OPEX, CPI, NFP dates. Earnings and ex-dividend dates are fetched on-demand from a free source (Yahoo, Nasdaq) with caching. Document the data sources and their update cadence in ARCHITECTURE.md.
- **Local Parquet adapter:** must be able to run the full reference backtest suite from a bundled test dataset without any network access, so CI and offline users both work.

### 7.8 Performance Targets

- Reference backtest suite (5 templates, 5-year window, ~5 symbols each) completes in under 3 minutes on a laptop.
- A single backtest for 1 template on 5 symbols over 5 years completes in under 60 seconds.
- MCP server cold start under 2 seconds.
- These are hard targets. If the engine exceeds them on reasonable hardware, profile and fix before shipping.

### 7.9 Testing Strategy

- **Unit tests:** DSL parsing, validation, schema edge cases. Hypothesis property tests for DSL round-trip.
- **Engine unit tests:** position lifecycle, roll logic, exit logic, Greek aggregation. Use synthetic fixed data, not market data.
- **Integration tests:** the 5 reference backtests, snapshot-tested with `pytest-snapshot`. Any change that alters results fails CI and requires explicit snapshot update.
- **Determinism:** the engine must be fully deterministic given fixed inputs. Seed any RNG. Fill modeling that uses spread sampling should seed from a strategy + date hash.

---

## 8. Success Metrics

**Leading indicators (check weekly for first 90 days post-launch):**

- **Installations:** `pip install thetakit` downloads per week. Target: 200/week by week 4, 500/week by week 12.
- **GitHub stars:** proxy for awareness. Target: 500 by day 90.
- **First-backtest completion rate:** of users who install, what fraction successfully run a backtest within 24 hours? Measured via opt-in anonymous telemetry (off by default; users can enable it). Target: 60%.
- **Time-to-first-backtest:** from install to first successful run. Target: under 10 minutes for users who read the quickstart.
- **External PRs:** number of pull requests from contributors outside the core team. Target: 10 by day 90.
- **Issue quality:** fraction of opened issues that include a reproducible example. Target: above 50%.

**Lagging indicators (check monthly for first 6 months):**

- **Community traction:** number of forum posts, blog posts, or videos from independent users mentioning thetakit. Target: 20 by month 6.
- **Reference strategy adoptions:** number of distinct forks or citations of the shipped templates. Target: 50 by month 6.
- **Issue close rate:** median time from issue open to first substantive response. Target: under 48 hours.
- **Contributor retention:** fraction of first-time contributors who submit a second PR. Target: above 25%.

**Anti-metrics (watch these to know when to worry):**

- **Silent downloads with no usage:** if installs are high but first-backtest completion is under 40%, the quickstart is broken.
- **Backtest-result complaints:** if users report the engine produces unrealistic results (too good, usually), the fill modeling is wrong. This is a product-credibility emergency.
- **Stars without stickiness:** if the repo gets a HN spike and then goes quiet, the product is a demo, not a tool.

---

## 9. Open Questions

1. **Data vendor:** MarketData.app vs ORATS as the default reference adapter. ORATS has better historical IV surfaces but higher cost. MarketData.app is cheaper and has good DX. **Owner:** Founder. **Blocking:** yes, before engine implementation.
2. **Fill modeling calibration:** what should the default slippage be? Options: flat 40% of spread, empirically calibrated by liquidity tier, or configurable with a "conservative/realistic/aggressive" preset. **Owner:** Founder with input from beta users. **Blocking:** no, can default to 40% and iterate.
3. **Early assignment model:** binomial pricing for Bjerksund-Stensland is the textbook answer, but implementation cost is nontrivial. For Phase 1, is a simpler heuristic (flag and assign ITM calls within 1 day of ex-div if the time value is below the dividend) acceptable? **Owner:** Founder + quantitatively-minded contributor. **Blocking:** no, ship with the heuristic and document its limits.
4. **Telemetry:** how much (if any) anonymous usage telemetry should we collect to measure success metrics? Any telemetry in an open source tool is politically charged. **Owner:** Founder. **Blocking:** yes, before first release.
5. **Bundled skill scope:** how detailed should the skill in Phase 1 be? Minimal enough to prove the MCP integration, or polished enough to be the default rule-authoring UX? Risk of over-investing here before Phase 3. **Owner:** Founder. **Blocking:** no, default to minimal.
6. **Name:** `thetakit` is a placeholder. Final name affects the package name, GitHub repo, and domain. **Owner:** Founder. **Blocking:** yes, before public release.
7. **Documentation site hosting:** GitHub Pages, Read the Docs, or custom domain? **Owner:** Founder. **Blocking:** no.

---

## 10. Timeline and Phasing

Phase 1 is targeted at 12–14 weeks of focused work for a solo-founder + 1 engineer team, assuming Phase 0 has already passed.

Suggested sub-phases:

- **Weeks 1–3:** DSL, schema, template system, validator. Unit tests. Get rule authoring working end-to-end with no engine.
- **Weeks 4–7:** Backtest engine. Portfolio, positions, rolls, exits, fills, Greeks. Integration tests with synthetic data.
- **Weeks 8–9:** Data adapters. MarketData.app + local Parquet. Calendar data. First real backtest on real data.
- **Weeks 10–11:** MCP server. Skill file. CLI polish. Reporting and plots.
- **Week 12:** Reference backtest suite. Docs. Worked examples.
- **Weeks 13–14:** Private beta with 10–20 premium sellers from network. Fix the top-3 issues they find. Prepare public launch.

**Hard constraints:**

- Must not ship before Phase 0 validation passes.
- License decision (Apache 2.0 recommended) must be final before first commit to public repo.
- Data vendor open question (#1) must be resolved before Week 4.
- Telemetry open question (#4) must be resolved before first public release.

**Dependencies:**

- MarketData.app or ORATS account with API access
- GitHub organization and repository
- Domain name (once product name is chosen)

---

## 11. Appendix: Vibecoding Kickoff Prompt

If you are about to open Claude Code and start building, a good opening prompt is something like:

> Read `spec-phase-1.md` in this repo. We're building `thetakit`, an open source Python toolkit for backtesting options premium-selling strategies. Start with the DSL module per section 7.3: Pydantic models for Strategy, EntryRule, PositionSizing, RollRule, ExitRule, and RiskConstraints. Use Python 3.12, pydantic v2, and uv for package management. Set up the src-layout project structure shown in section 7.2. Write unit tests as you go. When the DSL is complete and validating against the 5 bundled template shapes (wheel, iron condor, credit spread, covered call, CSP), stop and show me the test results before moving on to the engine.

Scope your subsequent prompts similarly: one module, clear acceptance criteria, stop to review. The spec is detailed enough to let Claude do 80% of the work on each module without coming back to ask architectural questions.
