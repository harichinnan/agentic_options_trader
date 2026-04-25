# thetakit.cloud architecture

This is the contributor-facing companion to [docs/spec-phase-2.md](../docs/spec-phase-2.md).
It covers the Phase 2 monorepo as actually scaffolded in this session — what's
shipped, what's stubbed, and where the integration seams live.

## Component map

```
                        ┌────────────────────────────┐
                        │   Next.js dashboard        │   ← STUBBED in this session
                        │   (apps/web/)              │     (TS frontend, 2-3 wks)
                        └──────────────┬─────────────┘
                                       │ REST /v1
                                       ▼
                        ┌────────────────────────────┐
       OSS CLI ─────────►  FastAPI app                │
       (thetakit auth /  │  apps/api/src/api/         │
        smoke-eval, etc) │  • /v1/auth, /me           │
                        │  • /v1/rules                │
                        │  • /v1/evals                │
                        │  • /v1/billing (stub)       │
                        │  • /v1/mcp (OSS surface)    │
                        └──────────────┬─────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
      ┌──────────────────┐    ┌──────────────────┐   ┌──────────────────┐
      │ Credit ledger    │    │ Eval state       │   │ Agent service    │
      │ (append-only)    │    │ machine          │   │ (LangGraph)      │
      │ services/        │    │ services/        │   │ services/        │
      │  credit_service  │    │  eval_service    │   │  agent_service   │
      └────────┬─────────┘    └────────┬─────────┘   └──────────────────┘
               │                       │
               ▼                       ▼
      ┌──────────────────┐    ┌──────────────────┐
      │ Postgres / SQLite│    │ Compute engine   │
      │ (apps/api/db.py) │    │ apps/compute/    │
      └──────────────────┘    │  • HMM           │
                              │  • Path sim      │
                              │  • Aggregator    │
                              │  • Stress lib    │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  thetakit OSS    │
                              │  engine (Phase 1)│
                              │  run_backtest()  │
                              └──────────────────┘
```

## Why the engine is reused

The compute engine **does not reimplement the strategy lifecycle**. It calls
`thetakit.engine.run_backtest()` from Phase 1 against a `PathDataAdapter` that
wraps a single `SimulatedPath`. This means rule semantics (entry, exit, roll,
fill modeling, greeks) are guaranteed identical between historical backtests
and distributional evaluations. The only thing the cloud adds is *what data
goes in* — a generated path instead of a real one.

## State machine (eval lifecycle)

```
   submit_eval
      │
      │ reserve N credits in CreditLedger (atomic)
      │ create Eval row in 'queued'
      │ schedule background task
      │
      ▼
  [queued] ──mark_running──► [running]
                                 │
                                 ├─mark_complete──► [complete]
                                 │
                                 ├─mark_failed────► [failed]   (auto-refund)
                                 │
                                 └─cancel─────────► [canceled] (auto-refund)
```

State transitions are guarded by `IllegalEvalStateTransition`. The
auto-refund semantics live in `mark_failed` and `cancel` — never in route
handlers.

## Modal stub

`eval_service.run_eval_in_process` is what runs locally. In production, this
function is replaced by a Modal-function dispatcher: same signature, same
state mutations, but the work happens on Modal's autoscaling infra and a
`POST /v1/internal/eval-complete` callback finishes the state transitions.
Both code paths use the same `mark_*` mutators so invariants are identical.

## Credit ledger contract

The single piece of code I'd review hardest:
- Source of truth is the `credit_ledger` table. `users.credit_balance` is a
  cache. Tests verify they agree.
- Every transition gets a `reason` enum value.
- `reserve` is atomic — either decrements + writes a row, or fails cleanly.
- `refund` is idempotent — double-refund returns `None`, never over-pays.
- `stripe_event_id` has a `unique` constraint enforced at the DB level. Two
  webhooks with the same event id raise `DuplicateStripeEventError`.

See `apps/api/tests/unit/test_credit_ledger.py` for the invariant tests.

## LangGraph rule-authoring graph

Implements the spec 7.6 state machine with an in-memory checkpointer
(`MemorySaver`). For production use, swap to `PostgresSaver` so sessions
survive restarts.

The LLM is not directly imported — node functions take pluggable
`AgentHooks` that supply draft / narration callables. The default hooks
are deterministic stubs so the graph is testable without an LLM key. To
wire a real LLM, pass an `AgentHooks` whose `draft` and `narrate_*`
callables hit the Anthropic SDK.
