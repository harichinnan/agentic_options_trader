# SLV Covered Call Agent — LangGraph Architecture

## Strategy
1. **Entry**: Select SLV calls with delta < 0.35, high theta. Sell covered calls.
2. **Exit**: GTC buy-back at 50% of premium received.
3. **Risk Management**: Weekly portfolio review — portfolio greeks vs thresholds, close/roll candidates.
4. **Backtest**: Run over last year of historical data.

## Tech Stack
- Python + LangGraph + FastAPI
- DuckDB for data storage and querying
- Google Sheets for portfolio tracking
- Massive.com (Polygon.io) API for market data
- Black-Scholes for greek computation
- LLM (TBD) for risk assessment and roll recommendations

---

## Three Separate Graphs

```
+==========================================+
|            FastAPI Application            |
|  POST /entry/run    POST /risk/review     |
|  POST /exit/check   GET /portfolio        |
+==========================================+
       |              |              |
       v              v              v
  +---------+   +-----------+   +----------+
  | ENTRY   |   | EXIT      |   | RISK     |
  | GRAPH   |   | MONITOR   |   | REVIEW   |
  |         |   | GRAPH     |   | GRAPH    |
  +---------+   +-----------+   +----------+
       \              |              /
        \             |             /
         v            v            v
  +------------------------------------+
  |        Shared Service Layer         |
  |  DuckDB | greeks | sheets | LLM   |
  +------------------------------------+
       |              |              |
       v              v              v
  DuckDB          Google Sheets    LLM API
  (market data)   (portfolio)      (risk)
```

---

## DuckDB Data Model

All market data loaded into DuckDB for fast analytical queries.

```sql
-- SLV underlying daily prices
CREATE TABLE underlying_prices (
    date DATE,
    ticker VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
);

-- Options contract reference data
CREATE TABLE option_contracts (
    ticker VARCHAR PRIMARY KEY,    -- e.g., O:SLV251201C00030000
    contract_type VARCHAR,         -- call / put
    strike_price DOUBLE,
    expiration_date DATE,
    underlying_ticker VARCHAR,
    exercise_style VARCHAR,
    shares_per_contract INTEGER
);

-- Options daily OHLCV bars
CREATE TABLE option_bars (
    option_ticker VARCHAR,
    date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    vwap DOUBLE,
    num_trades INTEGER
);

-- Computed greeks (populated by Black-Scholes)
CREATE TABLE option_greeks (
    option_ticker VARCHAR,
    date DATE,
    delta DOUBLE,
    gamma DOUBLE,
    theta DOUBLE,
    vega DOUBLE,
    iv DOUBLE,
    underlying_price DOUBLE
);

-- Trade/position tracking
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    option_ticker VARCHAR,
    entry_date DATE,
    entry_premium DOUBLE,
    quantity INTEGER,
    gtc_target DOUBLE,
    close_date DATE,
    close_premium DOUBLE,
    status VARCHAR,              -- open / closed / rolled
    pnl DOUBLE
);
```

### Key Queries

```sql
-- Find candidates: delta < 0.35, high theta, calls expiring 2-6 weeks out
SELECT oc.ticker, oc.strike_price, oc.expiration_date,
       og.delta, og.theta, og.iv,
       ob.close AS last_price,
       og.theta / ABS(og.delta) AS theta_delta_ratio
FROM option_contracts oc
JOIN option_greeks og ON oc.ticker = og.option_ticker
JOIN option_bars ob ON oc.ticker = ob.option_ticker AND og.date = ob.date
WHERE oc.contract_type = 'call'
  AND og.date = ?  -- as-of date
  AND og.delta < 0.35
  AND og.delta > 0.05  -- avoid near-zero delta (too far OTM)
  AND oc.expiration_date BETWEEN ? AND ?  -- 2-6 weeks out
ORDER BY theta_delta_ratio DESC
LIMIT 10;

-- Portfolio greeks snapshot
SELECT SUM(og.delta * p.quantity) AS total_delta,
       SUM(og.gamma * p.quantity) AS total_gamma,
       SUM(og.theta * p.quantity) AS total_theta,
       SUM(og.vega * p.quantity) AS total_vega,
       COUNT(*) AS position_count
FROM positions p
JOIN option_greeks og ON p.option_ticker = og.option_ticker
WHERE p.status = 'open'
  AND og.date = ?;

-- Check GTC targets (positions where option price <= 50% of entry premium)
SELECT p.*, ob.close AS current_price
FROM positions p
JOIN option_bars ob ON p.option_ticker = ob.option_ticker
WHERE p.status = 'open'
  AND ob.date = ?
  AND ob.close <= p.gtc_target;
```

---

## State Schemas

```python
# src/state.py
from typing import TypedDict, Optional

class OptionCandidate(TypedDict):
    ticker: str
    strike_price: float
    expiration_date: str
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    last_price: float
    underlying_price: float
    days_to_expiry: int
    theta_delta_ratio: float

class Position(TypedDict):
    id: int
    option_ticker: str
    entry_date: str
    entry_premium: float
    quantity: int
    gtc_target: float
    status: str
    greeks_current: Optional[dict]

class PortfolioGreeks(TypedDict):
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    position_count: int

class EntryGraphState(TypedDict):
    run_date: str
    mode: str                    # "live" | "backtest"
    underlying_price: float
    candidates: list             # list[OptionCandidate]
    selected_trade: Optional[OptionCandidate]
    execution_result: Optional[dict]
    error: Optional[str]

class ExitGraphState(TypedDict):
    run_date: str
    mode: str
    positions_to_close: list
    close_results: list
    error: Optional[str]

class RiskReviewState(TypedDict):
    run_date: str
    mode: str
    open_positions: list
    portfolio_greeks: PortfolioGreeks
    risk_flags: list             # rule-based flags
    llm_analysis: str            # LLM risk assessment
    roll_candidates: list
    llm_roll_recommendations: list
    actions_taken: list
    report: str
    error: Optional[str]
```

---

## Graph 1: Trade Entry

```
  fetch_underlying
        |
        v
  query_candidates  (DuckDB: delta < 0.35, high theta, 2-6 wk expiry)
        |
        v
  [has candidates?]
      /       \
    yes        no --> END
    /
   v
  rank_and_select  (best theta/delta ratio)
        |
        v
  execute_trade  (record in DuckDB positions table)
        |
        v
       END
```

## Graph 2: Exit Monitor

```
  query_open_positions  (DuckDB: open positions)
        |
        v
  check_gtc_targets  (DuckDB: current price <= 50% of entry premium)
        |
        v
  [any to close?]
      /       \
    yes        no --> END
    /
   v
  execute_closes  (update positions in DuckDB)
        |
        v
       END
```

## Graph 3: Risk Review (Weekly, LLM-Enhanced)

```
  query_open_positions
        |
        v
  compute_portfolio_greeks  (DuckDB aggregate query)
        |
        v
  rule_based_risk_check  (delta/gamma/vega thresholds, near-expiry)
        |
        v
  llm_risk_assessment  (LLM interprets greeks + market context)
        |
        v
  identify_roll_candidates  (high delta, near expiry, etc.)
        |
        v
  llm_roll_recommendations  (LLM suggests roll strategies)
        |
        v
  [actions needed?]
      /       \
    yes        no
    /            \
   v              v
  execute_actions  generate_report
        |              |
        v              v
  generate_report    END
        |
        v
       END
```

### Where the LLM adds value:
1. **Pattern interpretation** — explains *why* greeks are concerning, not just that thresholds are breached
2. **Roll strategy selection** — weighs theta curves, premium credit/debit, whether to go further OTM
3. **Risk narrative** — weekly summary a human can read
4. **Anomaly detection** — spots non-obvious risks like expiry concentration or unusual vega ahead of events

---

## Backtesting vs Live Mode

Swappable via a data provider interface:

| Aspect | Live | Backtest |
|--------|------|----------|
| Data source | Polygon API | DuckDB (historical) |
| Position store | DuckDB + Google Sheets | DuckDB only |
| Order execution | Broker API (future) | Instant fill at close price |
| LLM calls | Real API | Optional / cached |
| Timing | Scheduled (cron) | Simulated day loop |

```python
class BacktestRunner:
    def run(self, start_date, end_date):
        for day in trading_days(start_date, end_date):
            self.exit_graph.invoke({"run_date": day, "mode": "backtest"})
            if is_monday(day):
                self.entry_graph.invoke({"run_date": day, "mode": "backtest"})
            if is_friday(day):
                self.risk_graph.invoke({"run_date": day, "mode": "backtest"})
        return self.compute_metrics()  # P&L, Sharpe, win rate, drawdown
```

---

## Project Structure

```
src/
  state.py                     # TypedDict state schemas
  db.py                        # DuckDB connection + table setup
  services/
    data_provider.py           # ABC + Live + Backtest providers
    black_scholes.py           # Greeks computation, IV solver
    google_sheets.py           # Sheets API wrapper
    polygon_client.py          # Polygon/Massive API client
  graphs/
    entry_graph.py             # Trade entry LangGraph
    exit_graph.py              # Exit monitor LangGraph
    risk_review_graph.py       # Weekly risk review LangGraph
  nodes/
    entry_nodes.py             # Node functions for entry
    exit_nodes.py              # Node functions for exit
    risk_nodes.py              # Node functions for risk review
    llm_nodes.py               # LLM-calling nodes
  backtesting/
    runner.py                  # Day-loop simulation
    metrics.py                 # P&L, Sharpe, drawdown
  api/
    main.py                    # FastAPI app
    routes.py                  # API endpoints
data/
  slv.duckdb                   # DuckDB database file
  slv_contracts.json           # Raw contract metadata
tests/
```

## Implementation Phases

1. **Foundation**: DuckDB schema + data loader, Black-Scholes greeks, data provider interface
2. **Entry + Exit graphs**: LangGraph wiring, DuckDB queries, backtest provider
3. **Backtesting harness**: Day-loop runner, performance metrics
4. **Risk Review + LLM**: Risk graph, LLM nodes, prompt templates
5. **Live infra**: FastAPI, Google Sheets, scheduling
