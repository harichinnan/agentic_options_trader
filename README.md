# Agentic Options Trader

A risk-managed premium-selling copilot for serious retail options traders — git + CI for trading rules, with regime-aware distributional evaluation.

> **Status:** Phase 0 — HMM feasibility & validation spike. Pre-product. See [docs/roadmap.md](docs/roadmap.md).

---

## What This Is

An AI-powered options trading agent that helps traders author, validate, and backtest systematic premium-selling strategies (covered calls, cash-secured puts, credit spreads). The first validated strategy is a **delta-35 / high-theta covered call on SLV** with GTC buy-back at 50% of premium and weekly portfolio-level risk review.

The long-term vision is a developer-friendly, rule-first toolkit with distributional (not just point-estimate) evaluation, conditioned on market regime — giving serious retail traders institutional-grade rigor without institutional tooling.

## What This Is Not

- Not a trade-execution bot. No broker integration, no auto-routing.
- Not stock-picking or alpha generation.
- Not investment advice. Research and analysis only.

See the [roadmap](docs/roadmap.md) for the open-source / proprietary split and why certain capabilities are deliberately excluded.

---

## Architecture at a Glance

Three LangGraph graphs coordinated by FastAPI, backed by DuckDB for analytical queries:

- **Entry Graph** — query candidates (delta < 0.35, high theta, 2–6 week expiry), rank by theta/delta ratio, execute the covered call sell.
- **Exit Monitor Graph** — check open positions against the 50%-of-premium GTC target; close winners.
- **Risk Review Graph (weekly, LLM-enhanced)** — aggregate portfolio greeks, run rule-based flags, then use an LLM to interpret patterns, recommend rolls, and produce a narrative risk report.

Full design in [docs/architecture.md](docs/architecture.md).

## Tech Stack

- **Language:** Python
- **Agent framework:** LangGraph
- **API:** FastAPI
- **Database:** DuckDB (market data + positions)
- **Portfolio storage:** Google Sheets (live mode)
- **Market data:** Massive.com (formerly Polygon.io) REST API — OHLCV bars, contract reference, technical indicators
- **Greeks:** Computed locally via Black-Scholes (no vendor provides historical greeks on accessible tiers)
- **LLM:** TBD — used only in the risk-review graph for pattern interpretation and roll recommendations

## Project Structure

```
src/
  download_slv_options.py    # Batch download of per-contract OHLCV bars (REST, rate-limited)
  download_slv_flatfiles.py  # S3 flat-file downloader (requires paid plan)
  fetch_contracts.py         # Paginated contract reference fetch with partial-save resumability
data/                        # Raw + processed market data (gitignored)
docs/
  roadmap.md                 # Product roadmap, open/proprietary split, phase gates
  architecture.md            # LangGraph + DuckDB design for the SLV covered-call agent
  phase-0-validation-protocol.md
  spec-phase-1.md            # Open-source backtest toolkit spec
  spec-phase-2.md            # Proprietary HMM evaluation service spec
  spec-phase-3.md            # Conversational product spec
tests/
```

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your MASSIVE_API_KEY
```

### Download historical data

```bash
# Fetch all SLV options contracts (paginated, ~30K contracts, resumable)
python src/fetch_contracts.py

# Download daily OHLCV bars per contract (rate-limited on free tier — use --batch for cron/scheduled runs)
python src/download_slv_options.py --batch 4
```

**Note on rate limits:** The Massive.com free tier is 5 requests/minute. The download scripts are designed to be resumable and to run incrementally via cron (`--batch N` makes N requests per invocation and exits). For serious backtesting, a paid plan or flat-file access is strongly recommended.

---

## Current Progress

- [x] Project scaffold and architecture design
- [x] Massive.com REST API integration (contracts + bars)
- [x] Contract reference data cached (~31K SLV contracts, 2-year range)
- [x] Batch-mode download with checkpointing and cron-friendly execution
- [ ] DuckDB schema + JSON-to-DuckDB loader
- [ ] SLV underlying price history
- [ ] Black-Scholes greeks computation + IV solver
- [ ] Entry graph (LangGraph)
- [ ] Exit monitor graph
- [ ] Risk review graph with LLM integration
- [ ] Backtest harness
- [ ] FastAPI endpoints
- [ ] Google Sheets portfolio integration

---

## License

TBD. See [docs/roadmap.md](docs/roadmap.md) for the open-source / proprietary split — the code in this repo is intended for Apache 2.0 or MIT release alongside Phase 1.
