# Phase 2 — status of this session's implementation

## Shipped (runnable locally)

- **Compute engine** (`apps/compute/src/compute/`):
  - Student-t HMM (3 regimes) with fit/infer/generate
  - Numpy-based Monte Carlo path simulator
  - Stress scenario library with 7 historical crisis periods
  - Per-path aggregator → distributional stats (median/IQR/90% band/CVaR/etc.)
  - Smoke-eval runner (~500 paths, fixed regime mix, <30s)
  - Full-eval runner (~10k paths, regime transitions, stress scenarios injected)
  - Strategy runner that imports the Phase 1 `thetakit` engine
- **FastAPI backend** (`apps/api/src/api/`):
  - SQLAlchemy 2 models: User, ApiKey, Rule, Eval, CreditLedger, Prediction, StripeEvent
  - Alembic-style schema init (bootstrap-only; full migrations deferred)
  - Routes: /auth, /rules, /evals, /billing (stub), /mcp (OSS integration)
  - API-key bearer auth middleware
  - Credit service with exhaustive ledger invariants + tests
  - Eval service (submit → run in-process → callback → aggregate)
- **LangGraph rule authoring session**:
  - 7-node graph with in-memory checkpointer (Postgres checkpointer in prod)
  - Matches the state machine in spec section 7.6
- **OSS integration**:
  - `thetakit auth --key <key>` stores credentials in `~/.thetakit/credentials`
  - `thetakit smoke-eval` / `full-eval` / `eval-status` / `eval-pull` commands
  - MCP tools: `run_smoke_eval`, `run_full_eval`, `get_eval_status`, `get_eval_results`, `summarize_eval`
  - HTTP client in `packages/mcp-client`
- **Tests**: credit ledger (invariant-based), HMM shape/stability, path simulator determinism, API round-trips, eval state transitions, OSS integration

## Deliberately stubbed (documented, not wired)

| Component | Reason | Where |
|---|---|---|
| Next.js frontend | Different stack (TypeScript); 2-3 weeks on its own per spec section 10 | `apps/web/` missing |
| Clerk auth | External SaaS; requires account + real user flow | API uses API-key bearer only |
| Stripe billing | External SaaS; requires webhook infra | `/v1/billing/*` routes return 501 |
| Modal compute | External SaaS; requires account + deploy | Runs in-process via same code paths |
| S3 / R2 storage | External SaaS | Result blobs stored in local `./data/eval_blobs/` |
| Postgres | External SaaS | Uses SQLite (`./thetakit_cloud.db`) |
| Real HMM artifact | Phase 0 research spike (not started per roadmap) | HMM fitted on synthetic data at service start |

All stubs have single-line integration points — see `apps/api/src/api/services/*_service.py` for the pattern.

## Known Phase 2 tasks not covered in this session

- Dashboards, charts, billing UI (all Next.js)
- Stripe webhook reconciliation (endpoint shell exists, wiring doesn't)
- Email notifications on eval completion
- Shareable read-only eval links
- Model artifact versioning + rollout strategy
- Load testing (50 concurrent full evals)
- Counsel review of disclaimers (pre-launch gate per spec)
