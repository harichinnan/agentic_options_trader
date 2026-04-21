# Spec — Phase 2: Hosted Distributional Evaluation Service

**Working name:** TBD (placeholder: `thetakit.cloud`)
**Phase:** 2 of 5 (per roadmap)
**Target ship:** Oct–Dec 2026
**Status:** Draft, intended to be buildable directly
**Audience:** Founder + 1–2 engineers, vibecoding from this doc
**Prerequisites:** Phase 0 validation passed. Phase 1 (thetakit OSS) shipped and in use.

> This spec covers the proprietary hosted service that sits on top of the open source thetakit toolkit. The core asset is the HMM-based distributional evaluation engine, wrapped in a web product with auth, billing, and first-class visualizations. **This is the phase where the business starts.** Phase 3 (polished conversational experience, continuous tuning agent) and Phase 4 (plugin directory distribution) are explicitly out of scope here, though the architecture must not preclude them.

---

## 1. Problem Statement

Historical backtests of premium-selling strategies give users a single realized path through time. They cannot tell you whether your strategy's 14% CAGR was a robust central tendency or a lucky rollout, and they systematically underestimate tail risk because the sample of crisis periods in any finite window is too small to reason from. Phase 1 ships honest historical backtests, which is better than nothing, but every sophisticated premium seller who has been burned knows that "looked great in backtest" is exactly the moment before a blowup. What they need — and what does not exist for retail — is **distributional evaluation**: the same strategy run against thousands of plausible market paths generated from a regime-aware model, with explicit posterior distributions over outcomes, conditional tail expectations, and the ability to see what happens during regime transitions.

The cost of not solving it: users either stop trusting backtests entirely and fly blind, or trust them too much and get run over by the first real vol event. Both failure modes are avoidable with the right modeling layer and the right UX for communicating uncertainty.

---

## 2. Goals

1. **Ship a trustworthy HMM-based distributional evaluator.** Given a Phase 1 strategy rule set, produce a posterior distribution over outcomes (CAGR, max drawdown, CVaR, probability of ruin, conditional returns by regime) across thousands of simulated paths generated from a fitted regime-switching model. The results must be calibrated against known historical stress periods and communicated with honest uncertainty.
2. **Provide two eval tiers with clear latency characteristics.** A fast smoke eval (~500 paths, single regime mix, under 30 seconds) for conversational iteration, and a full eval (~10,000 paths, full regime transitions, stress scenario augmentation, 2–10 minutes) for commit-grade evaluation. Both cost credits; the full eval costs substantially more.
3. **Make the distributional results legible.** First-class interactive visualizations: payoff envelopes, regime probability paths, drawdown distributions, tail density plots, conditional return by regime, and before-after comparison views for rule tweaks. This is where the product either sings or dies.
4. **Ship a credit-based billing system with a real free tier.** Free tier large enough that a new user can run one full eval without a credit card on file. Paid tiers priced to cover compute with margin. Stripe-backed, metered on eval consumption.
5. **Integrate cleanly with the Phase 1 OSS toolkit.** Users install `thetakit` locally, paste an API key, and the same CLI and MCP tools they already use gain access to hosted smoke and full evals. No re-learning. No migration. The OSS tool is the onramp to the hosted service.
6. **Lay the groundwork for calibration tracking.** Every recommendation the system produces gets logged with its predicted probabilities and its resolution criteria so that a public calibration track record can be built over time (surfaced starting in Phase 3).

---

## 3. Non-Goals

1. **No polished conversational product with memory and continuous tuning.** That is Phase 3. Phase 2 exposes the eval service and a basic web dashboard; the conversational rule authoring experience in Phase 2 is "good enough to be the onramp," not a hero feature.
2. **No live trading, no broker integration, no order routing.** Still strictly research and analysis. The regulatory line does not move in Phase 2.
3. **No plugin directory submission.** Phase 4. The hosted service needs to work standalone before distribution becomes interesting.
4. **No mobile app.** Read-only mobile might come in Phase 5+. Phase 2 is desktop-web only.
5. **No team or multi-seat features.** Single-user accounts. Organizations come in Phase 5+ if the RIA segment materializes.
6. **No custom model training per user.** Everyone shares the same fitted HMM. Per-user calibration is Phase 3+.
7. **No intraday granularity for path simulation.** Daily-close only, consistent with Phase 1. Intraday is Phase 5+.
8. **No alternative asset classes.** US equity options only.

---

## 4. Target Users

**Primary persona — "The Phase 1 graduate"**
Already using thetakit OSS for historical backtests. Has hit the wall where a rule looks good on history but they do not trust it for real money. Wants distributional confidence. Willing to pay for compute. This is the warm audience and the majority of Phase 2 revenue.

**Secondary persona — "The risk-conscious premium seller who hasn't touched the OSS yet"**
Heard about the product through community or word-of-mouth, lands on the website, sees the visualizations, signs up. They will not install the OSS before trying the hosted product. This persona matters because it tests whether the web experience stands on its own.

**Explicit non-persona for Phase 2:**
The casual retail gambler who wants AI to pick winning trades. We are aggressively not their product and we should not try to acquire them because they churn, complain, and distort the product signal.

---

## 5. User Stories

**Onboarding and first value**

- As a new user, I want to sign up with Google/GitHub in one click so that I can reach the dashboard without friction.
- As a new user, I want to receive enough free credits to run one full eval without a credit card so that I can experience the core value before committing.
- As a new user, I want a guided "first eval in under 15 minutes" flow so that I know exactly what to do next after signup.
- As a new user, I want to see someone else's eval results as a demo before running my own so that I understand what the output looks like.

**Running evals from the web app**

- As a user, I want to paste or upload a Phase 1 rule file and run a smoke eval from the dashboard so that I can iterate on rules without leaving the browser.
- As a user, I want to run a full eval asynchronously and be notified when it completes so that I can walk away during the run.
- As a user, I want to see my eval history with stats, dates, and cost so that I can compare past runs and re-run old rules.
- As a user, I want to compare two eval results side-by-side so that I can see how a rule tweak changed my distributional outcomes.

**Running evals from the OSS toolkit**

- As a Phase 1 user, I want to paste an API key into my local thetakit config so that my existing CLI gains `thetakit smoke-eval` and `thetakit full-eval` commands.
- As a Phase 1 user, I want the MCP tools I'm already using in Claude Code / Cowork to gain hosted eval capabilities once my API key is set so that my existing workflows get upgraded automatically.
- As a Phase 1 user, I want hosted eval results to be retrievable via handle from the CLI so that I can download them locally for offline inspection.

**Understanding the results**

- As a user, I want to see the distribution of my strategy's outcomes (CAGR, drawdown, probability of ruin) with honest uncertainty bands so that I know what the range of futures looks like, not just the median.
- As a user, I want the regime mix to be shown explicitly ("62% normal, 28% elevated, 10% transitioning") so that I understand the context the eval was run under.
- As a user, I want a plain-English narration of the tail ("in the 5% worst paths, max drawdown averages 24%, concentrated in regime transitions from normal to crisis") so that I do not have to interpret statistics on my own.
- As a user, I want to see the conditional performance of my strategy by regime so that I understand where it is robust and where it is fragile.
- As a user, I want to see which stress scenarios were included in the eval so that I can verify the tail estimates are not flattering by omission.

**Billing and credits**

- As a user, I want to buy credits in bundles of varying sizes so that I can pay only for what I use.
- As a user, I want a subscription option that gives me a monthly credit pool and priority queueing so that heavy usage is predictable.
- As a user, I want to see my credit balance, recent consumption, and projected burn rate so that I can manage my usage.
- As a user, I want to receive a warning when my credit balance is low so that I am not surprised by a rejected eval.

**Trust and integrity**

- As a skeptical user, I want to see what model is being used, when it was last retrained, and what its out-of-sample validation results look like so that I can trust the tool before I pay.
- As a skeptical user, I want to see warnings when model uncertainty is high (e.g., crisis regime transition probabilities) so that I know when to distrust the point estimates.
- As a skeptical user, I want a public calibration track record so that I can evaluate whether the tool's probabilities match reality over time.

---

## 6. Requirements

### 6.1 Must-Have (P0) — Ship Blockers

**Distributional evaluation engine**

- Fitted Hidden Markov Model over SPY + VIX (+ MOVE, credit spreads as feature extensions) with 3–4 latent regimes. Fitted on 10–15 years of daily data.
- Regime-conditional generative model for returns and IV surface dynamics. Fat-tailed innovations (Student's t or similar). Term structure preserved at the sampling level.
- Monte Carlo path generator that samples regime sequences from the HMM transition matrix and generates price + IV paths conditioned on each regime sample.
- Stress scenario library: a curated set of historical stress periods (Feb 2018, Mar 2020, 2022 bear, Q4 2018, Aug 2015, 1987, 2008) that are injected into full evals regardless of the current regime mix, so the tail is always anchored to real crisis physics.
- Path replayer that runs a Phase 1 strategy against each generated path and produces per-path outcomes (P&L, drawdown, max delta, max vega, etc.).
- Aggregator that turns per-path outcomes into distributional statistics: median/5th/25th/75th/95th percentile CAGR, drawdown distribution, CVaR at 5% and 1%, probability of ruin at configurable thresholds, win rate distribution, conditional return by regime.
- **Acceptance:** Given a known-dangerous strategy (e.g., naked short puts on QQQ at 0.5 delta, 7 DTE, no exits), when a full eval is run, then the distributional results show median returns below a buy-hold baseline and 5th-percentile tail losses in excess of 40%. The tail must not look flattering for known-dangerous playbooks.

**Two eval tiers**

- **Smoke eval**: ~500 paths, fixed at the current regime mix (no regime transitions simulated), daily granularity, under 30 seconds end-to-end. Cost: 1 credit. Used for conversational iteration on rule tweaks.
- **Full eval**: ~10,000 paths, full regime transitions sampled from the HMM, stress scenarios injected, daily granularity, target 2–10 minutes. Cost: 20 credits. Used for commit-grade evaluation.
- **Acceptance:** Both eval tiers produce outputs with the same schema; the full eval is strictly a superset of the smoke eval in terms of statistical richness and available visualizations.

**Web dashboard**

- Auth with email magic link + Google + GitHub OAuth.
- Dashboard home: balance, recent evals, queued evals, "run a new eval" CTA.
- Rule editor view: paste YAML, validate inline, save to user's rule library, run eval.
- Eval result view: summary stats, distributional plots, regime breakdown, tail narration, link to downloadable JSON report, shareable read-only link.
- Compare view: side-by-side diff of two eval results with highlighted changes.
- Billing view: current plan, credit balance, purchase history, Stripe-hosted upgrade flow.
- Account settings: API key management, rotation, revocation.
- **Acceptance:** A new user can sign up, run a smoke eval on a bundled example rule, and see results in under 5 minutes. They can run a full eval in under 15 minutes (including wait time) without reading documentation.

**Visualizations (the make-or-break category)**

- **Payoff envelope plot:** equity curve distribution with median, IQR band, 90% band, and individual-path overlays. Interactive hover, zoom, regime shading.
- **Drawdown distribution plot:** histogram + KDE of max drawdown across paths, with stress-scenario paths highlighted.
- **Regime probability path:** stacked area chart of regime probabilities over time for the current market state.
- **Portfolio Greek heatmap:** net delta, gamma, theta, vega as a function of time, averaged across paths with IQR bands.
- **Tail scatter:** each path plotted as (CAGR, max drawdown), color-coded by dominant regime, with the 5% worst paths labeled.
- **Conditional return by regime:** bar chart of expected P&L conditional on each regime, with confidence intervals.
- **Stress scenario panel:** per-stress-scenario P&L outcome, ranked.
- **Acceptance:** A user can look at these six plots and, without reading any text, form a reasonable opinion about whether the strategy is robust or fragile. If they need supplementary text to understand the plots, the plots are not doing their job.

**Integration with Phase 1 OSS**

- `thetakit auth` command to set API key from the CLI, stored in `~/.thetakit/credentials`.
- New CLI commands: `thetakit smoke-eval <rule>`, `thetakit full-eval <rule>`, `thetakit eval-status <handle>`, `thetakit eval-pull <handle>`.
- New MCP tools added to the OSS server (gated on presence of API key): `run_smoke_eval`, `run_full_eval`, `get_eval_status`, `get_eval_results`, `summarize_eval`.
- The OSS MCP server proxies these calls to the hosted API with the user's API key. Results can be cached locally once pulled.
- **Acceptance:** A user who already has thetakit OSS installed can run `thetakit auth --key <key>` followed by `thetakit full-eval strategies/wheel-spy.yaml` and get results back through the same workflow they already know.

**Credits and billing**

- Stripe-backed billing. Credit packs: 200 ($20), 600 ($50 — 17% discount), 2000 ($150 — 25% discount).
- Monthly subscription: $99/mo for 2000 credits + priority queue + unused credits carry over for one month.
- Free tier: 50 credits/month, resets monthly, no card required. Enough for 2 full evals or 50 smoke evals.
- Credit ledger: append-only transaction log of all credit grants, purchases, and consumptions. Every eval decrements the balance at the moment the job is enqueued; failed evals refund credits.
- Billing events (purchase, refund, subscription changes) webhooked from Stripe and reconciled to the ledger.
- **Acceptance:** A user can purchase credits, see them reflected in their balance immediately, run evals against them, and see accurate billing history. Failed evals never silently consume credits.

**Trust surface**

- Model card page: current model version, training window, regime count, out-of-sample validation metrics (how well does the HMM flag known crisis periods), last retrain date.
- Honest uncertainty communication: every distributional statistic shown in the UI has an associated uncertainty estimate. Crisis tail statistics are visually flagged with a "high model uncertainty" indicator.
- Disclaimer surface: clear, prominent, not buried. "Research and analysis tool. Not investment advice. Past performance, including simulated performance, does not predict future results." Review by counsel before launch.
- Methodology documentation: a public methodology page explaining the HMM approach at a level a sophisticated retail trader can understand, with links to academic references.
- **Acceptance:** A skeptical user can find the model card, the methodology, and the limitations within two clicks from the dashboard home. No feature of the product implies confidence the model does not support.

### 6.2 Nice-to-Have (P1) — Ship If Time Permits

- Shareable read-only eval links (generate a public URL for an eval that others can view without an account).
- Email notifications when full evals complete or when credit balance falls below a threshold.
- Export eval results to PDF report.
- Basic rule library: save named rules, organize in folders, tag.
- Diff view between rule versions as the user edits.
- "Run the same eval against a previous market snapshot" — i.e., re-run with the regime mix from 6 months ago to see how my strategy would have looked then.
- Referral program: refer a user, both get bonus credits on their first purchase.

### 6.3 Future Considerations (P2) — Explicitly Out of Scope, Design For

- **Calibration track record (Phase 3):** every recommendation logged with (predicted_probability, resolution_criteria, timestamp, model_version) so the Phase 3 calibration dashboard can compute Brier scores without retroactive data collection. This table exists and is populated from day 1 of Phase 2.
- **Continuous rule tuning agent (Phase 3):** the eval service API must support "compare eval A to eval B" as a primitive so the Phase 3 agent can reason about rule changes. Expose it even if the Phase 2 UI only uses it for the compare view.
- **Team / org mode (Phase 5+):** every user record has a nullable `org_id` from day 1, even though orgs are not a feature yet, so adding them later does not require a migration.
- **Custom per-user HMM calibration (Phase 3+):** the eval endpoint accepts an optional `model_override` parameter that is ignored in Phase 2 but reserved for per-user fitted models later.
- **Plugin directory submission (Phase 4):** the MCP integration should be a bundle that is already plugin-directory-compatible even though we are not submitting it yet.

---

## 7. Architecture and Technical Design

### 7.1 Platform and Stack

**Backend (Python)**

- **Language:** Python 3.12
- **Package management:** `uv`
- **Web framework:** `FastAPI` with `pydantic` v2 models shared between API and storage layers.
- **ORM / DB:** `SQLAlchemy` 2.x async + `asyncpg`. Alembic for migrations.
- **Database:** Postgres 16, managed on Neon or Supabase.
- **Auth:** Clerk (cheapest path to OAuth + magic link with minimal code) OR Supabase Auth if we are already on Supabase for DB. Recommend: **Clerk**, lower friction.
- **Billing:** Stripe with metered billing via the credit ledger pattern (we do not use Stripe's metered billing primitive; we use credit packs and one-time charges + subscription objects, reconciled to our own ledger).
- **Task queue and compute runtime:** **Modal** (modal.com). This is the most important platform choice in Phase 2. Modal is Python-native, scales to zero, pay-per-second, and is purpose-built for bursty Monte Carlo compute. A full HMM eval becomes a Modal function invocation that runs on an autoscaling pool. Alternative: Celery + Redis + a persistent worker pool, which is cheaper at high utilization but has worse scale-to-zero economics. Recommend Modal for the first 12 months; reconsider if utilization exceeds 40% steady-state.
- **Agent orchestration:** **LangGraph** (see Section 7.6 for detailed reasoning). Used for the conversational rule authoring + eval review flow with Postgres-backed checkpointing.
- **LLM access:** Anthropic API (Claude Sonnet 4.6 for the agent, Haiku for cheap summarization tasks).
- **Data processing:** `polars` for DataFrames, `numpy` for arrays, `numba` for hot loops in the path simulator, `scipy.stats` for distributions.
- **HMM libraries:** `hmmlearn` as a baseline for Gaussian HMM, custom Student-t HMM implementation on top of numpy for production (the fat tails matter and hmmlearn's Gaussian assumption is insufficient).
- **Options pricing:** `py_vollib_vectorized` for Black-Scholes Greeks, custom binomial for American-exercise paths.
- **Data storage:** Postgres for metadata, rules, evals, users, billing. **S3 / R2** for Parquet historical data, fitted model artifacts, and full-eval result blobs (distributional outputs are too big for the DB).
- **Caching:** Redis for session state, rate limiting, short-lived eval handles.
- **Deployment:** Backend API on **Fly.io** (cheap, fast deploys, good DX) or **Render**. Compute-heavy Modal functions run on Modal's infrastructure and are called from the API.

**Frontend (TypeScript, breaking from Python-only preference intentionally)**

- **Framework:** **Next.js 15** with the App Router. TypeScript throughout.
- **Styling:** `tailwindcss` + `shadcn/ui` components.
- **Charts:** `plotly.js` (interactive, rich, handles all the visualizations we need) with a `tremor` component layer on top for simpler dashboard cards. Plotly is the right call because the chart density and interactivity requirements exceed what lightweight libraries like Recharts can handle.
- **State / data fetching:** `@tanstack/react-query` for server state, React Context for UI state. No global state library.
- **Auth:** Clerk SDK for Next.js (seamless if we picked Clerk on the backend).
- **Billing UI:** Stripe Elements + Stripe Checkout for upgrade flows. Custom React for the credit balance display.
- **Deployment:** Vercel.

**Why Next.js and not Python-native frontend frameworks.** I want to be explicit about breaking from Python-only because the user's preference was real. The three Python-native options I considered: **Reflex** (new, Python-native, nice DX, but small community and no battle-tested patterns for rich dashboards with many interactive charts), **Streamlit** (mature but visually and interactively limited, not a fit for a product with paying users), and **FastHTML / HTMX + Jinja** (great for content-heavy sites, weaker for complex client-side interactivity). None of these are the right call when visualization density and polish are make-or-break. **Next.js + TypeScript is the industry default for a reason** and in Phase 2 we need to be in the industry default. If the team is uncomfortable with TypeScript, the mitigation is hiring a part-time frontend contractor for 6 weeks to get the scaffolding right, not picking a weaker framework.

**Deliberately NOT in the stack**

- **Next.js API routes for backend logic.** Keep the backend Python, Next.js is the view layer only.
- **Kubernetes.** Modal + Fly + Vercel means we never touch k8s in Phase 2. Avoid this trap.
- **GraphQL.** REST + OpenAPI from FastAPI. Keep it simple.
- **A search service.** No full-text search needed yet.
- **A dedicated analytics warehouse.** Postgres views are fine through Phase 3.

### 7.2 Monorepo Layout

```
thetakit-cloud/
├── apps/
│   ├── api/                          # FastAPI backend
│   │   ├── pyproject.toml
│   │   ├── src/api/
│   │   │   ├── main.py               # FastAPI app
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── evals.py
│   │   │   │   ├── billing.py
│   │   │   │   ├── rules.py
│   │   │   │   └── mcp_proxy.py      # MCP-compatible endpoints for OSS integration
│   │   │   ├── models/               # SQLAlchemy models
│   │   │   ├── schemas/              # Pydantic models
│   │   │   ├── services/
│   │   │   │   ├── eval_service.py   # enqueues Modal jobs
│   │   │   │   ├── credit_service.py
│   │   │   │   ├── auth_service.py
│   │   │   │   └── agent_service.py  # LangGraph entry point
│   │   │   └── deps.py
│   │   └── alembic/
│   ├── compute/                      # Modal functions
│   │   ├── pyproject.toml
│   │   ├── src/compute/
│   │   │   ├── modal_app.py          # modal.App definition
│   │   │   ├── smoke_eval.py         # @app.function for smoke
│   │   │   ├── full_eval.py          # @app.function for full
│   │   │   ├── path_simulator.py     # numba-compiled path generation
│   │   │   ├── hmm/
│   │   │   │   ├── fit.py            # training (run offline, not from API)
│   │   │   │   ├── model.py          # Student-t HMM
│   │   │   │   └── regime_classifier.py
│   │   │   ├── strategy_runner.py    # imports thetakit OSS engine
│   │   │   └── aggregator.py         # per-path → distribution
│   │   └── training/                 # offline scripts for model training
│   ├── web/                          # Next.js frontend
│   │   ├── package.json
│   │   ├── src/app/
│   │   │   ├── (marketing)/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── evals/
│   │   │   │   ├── rules/
│   │   │   │   ├── billing/
│   │   │   │   └── settings/
│   │   │   └── api/                  # Next.js BFF routes (auth helpers only)
│   │   ├── components/
│   │   │   ├── charts/               # plotly wrappers per chart type
│   │   │   ├── ui/                   # shadcn components
│   │   │   └── eval/
│   │   └── lib/
│   └── docs/                         # mkdocs site for methodology
├── packages/
│   ├── shared-types/                 # TypeScript types generated from OpenAPI
│   └── mcp-client/                   # MCP tools shipped to the OSS toolkit
├── infra/
│   ├── modal/                        # Modal secrets, images
│   ├── fly/                          # Fly deploy config
│   └── terraform/                    # optional, if we go that route
└── README.md
```

### 7.3 Core Data Models (Postgres, SQLAlchemy)

Sketches of the critical tables. Use Alembic migrations; do not hand-edit.

```python
class User(Base):
    id: UUID
    email: str
    clerk_id: str (unique)
    org_id: UUID | None           # reserved for Phase 5+
    created_at: datetime
    credit_balance: int            # denormalized, source of truth is CreditLedger
    plan: Literal["free", "starter", "pro"]
    subscription_status: Literal["none", "active", "canceled", "past_due"]

class ApiKey(Base):
    id: UUID
    user_id: UUID (fk)
    key_hash: str (indexed)
    name: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

class Rule(Base):
    id: UUID
    user_id: UUID (fk)
    name: str
    yaml_source: str
    content_hash: str              # for deduplication & version tracking
    created_at: datetime

class Eval(Base):
    id: UUID
    user_id: UUID (fk)
    rule_content_hash: str
    rule_snapshot: str             # yaml at time of eval
    universe: list[str]
    start_date: date
    end_date: date
    eval_type: Literal["smoke", "full"]
    model_version: str
    status: Literal["queued", "running", "complete", "failed", "canceled"]
    created_at: datetime
    completed_at: datetime | None
    credits_charged: int
    modal_call_id: str | None
    result_blob_key: str | None    # S3 key for distributional output
    summary_stats: JSONB           # denormalized for list views

class CreditLedger(Base):
    id: UUID
    user_id: UUID (fk)
    delta: int                     # positive grant/refund, negative consumption
    reason: Literal["grant", "purchase", "consumption", "refund", "subscription_grant"]
    eval_id: UUID | None (fk)
    stripe_event_id: str | None
    created_at: datetime

class Prediction(Base):              # forward-compat for Phase 3 calibration
    id: UUID
    eval_id: UUID (fk)
    predicted_at: datetime
    statement: str                  # human-readable
    probability: float
    resolution_criterion: str       # machine-readable
    resolution_date: date | None
    resolved: bool
    resolved_outcome: bool | None   # true = prediction correct
    model_version: str

class StripeEvent(Base):            # idempotency for webhooks
    id: str                         # stripe event id
    type: str
    payload: JSONB
    processed_at: datetime | None
```

### 7.4 Eval Execution Flow

This is the backbone of Phase 2. Get this right and the rest is scaffolding.

```
User submits eval via web UI or OSS MCP → POST /evals
    │
    ▼
api/routes/evals.py::submit_eval
    │
    ├── Validate rule (calls thetakit OSS validator in-process)
    ├── Check credit balance (credit_service.reserve)
    ├── Create Eval row with status="queued"
    ├── Insert CreditLedger row (delta=-cost, reason="consumption")
    ├── Enqueue Modal function (smoke_eval or full_eval)
    │    └── modal_call_id stored on Eval row
    └── Return 202 with eval_id
    │
    ▼
Modal function runs (smoke: ~30s, full: 2-10min)
    │
    ├── Fetch rule from DB
    ├── Fetch/cache underlying data from S3 (historical Parquet)
    ├── Load current HMM model artifact from S3
    ├── Sample regime sequences + generate paths (numba-compiled hot loop)
    ├── Run Phase 1 strategy engine against each path in parallel
    ├── Aggregate per-path outcomes into distributional stats
    ├── Write full result blob to S3
    ├── POST back to /internal/eval-complete with summary stats
    │    (authed with a shared secret between Modal and API)
    └── Done
    │
    ▼
api/routes/evals.py::eval_complete
    │
    ├── Update Eval row (status="complete", summary_stats, result_blob_key)
    ├── (if failed) Refund credits via CreditLedger
    ├── (if notifications enabled) Email user
    └── Done
    │
    ▼
User polls GET /evals/{id} or web UI auto-refreshes via WebSocket/SSE
```

**Critical notes for vibecoding:**

- **Credit reservation is synchronous before enqueue.** Never enqueue a job you have not charged for. Never charge for a job that failed to enqueue.
- **Eval failures refund credits automatically.** No manual intervention should be required for the common case.
- **The Modal function is stateless.** All state flows through DB + S3. If a Modal call is lost, we can re-enqueue without corruption.
- **Rule snapshots are immutable on the Eval row.** Even if the user deletes the rule later, the eval history remains reproducible.
- **S3 result blobs are the source of truth for distributional details.** The DB only stores summary stats denormalized for list views. Detail views fetch from S3.

### 7.5 HMM Modeling Approach

A full research document belongs elsewhere (this is the product spec), but the architectural commitments the spec imposes on the modeling work are:

- **3–4 regimes, interpretable.** Not 12. Not learned-unsupervised without interpretation. A user must be able to look at the regime output and understand which one they are in.
- **Features:** SPY log returns + VIX level + VIX term structure slope + MOVE index + IG credit spreads. All daily. Normalized per a fixed training-window z-score.
- **Innovation distribution:** Student's t per regime, not Gaussian. Fat tails matter.
- **Fitting:** EM with random restarts. Validate by regime log-likelihood on held-out data and by the crisis-flagging test (does the model assign meaningful probability to crisis transitions before known events).
- **Stability:** Regime labels must be stable across refits (solve via Hungarian matching on centroids). Users should not see their "normal regime" magically flip to a "crisis regime" because we retrained.
- **Retraining cadence:** Quarterly on a rolling window. Freeze crisis regimes more aggressively than calm regimes.
- **Artifact format:** Fitted model serialized to pickle + metadata JSON, stored in S3 under versioned keys. The API knows the current version via an env var.

The Phase 0 memo is the spec for the modeling work itself. This section just says: whatever model you fit, it must conform to these architectural commitments so the Phase 2 code can consume it cleanly.

### 7.6 On LangGraph: Now It Matters

In Phase 1 I argued LangGraph was premature. In Phase 2 it becomes the right tool, and here is the reasoning — because nothing is worse than adopting a framework without being clear on what it is earning you.

**What changes in Phase 2:** we are running our own agent loop, not relying on an external MCP host. A user in our web app has a conversation that may span minutes (waiting for a full eval) or days (resuming tomorrow to tweak a rule). We need:

- **State persistence across turns.** The conversation carries context — the rule being authored, the most recent eval results, the user's feedback. Losing this state on a backend restart would make the product feel broken.
- **Async/long-running steps as first-class citizens.** A full eval is a multi-minute task. The agent needs to say "I've started the eval, I'll ping you when it's done," persist its state, and resume when the job completes. LangGraph's checkpointing + interrupt pattern is exactly this.
- **Explicit graph structure.** The rule authoring flow has real branches: validation succeeds vs. fails, smoke eval suggests tweaks vs. commit, full eval commits vs. revises. Encoding this as a graph is clearer than nested if-statements in a loop.
- **Human-in-the-loop gates.** Before a rule is committed to the user's saved library (and potentially linked to the OSS MCP), the agent must get explicit user approval. LangGraph's `interrupt` primitive is built for this.
- **Replay and debugging.** Bugs in agent flows are hard to reproduce without state snapshots. LangGraph's checkpoint store gives you a free replay tool.

**The LangGraph architecture for Phase 2:**

```
Graph: rule_authoring_session

States (nodes):
  [start]
  gather_requirements       - Initial intent, strategy type, universe, risk profile
  draft_rule                - Produce draft YAML
  validate_rule             - Call thetakit OSS validator
      ↓ fail → draft_rule (loop with error context)
      ↓ pass → smoke_eval
  smoke_eval                - Enqueue smoke eval, wait for result
  review_smoke              - Narrate results, propose tweaks
      ↓ user wants tweaks → draft_rule
      ↓ user commits → full_eval_prompt
  full_eval_prompt          - Confirm full eval cost, get approval [INTERRUPT]
      ↓ approved → full_eval
      ↓ declined → review_smoke
  full_eval                 - Enqueue full eval [INTERRUPT until job completes]
  review_full               - Narrate distributional results, tail, regime breakdown
      ↓ user wants tweaks → draft_rule
      ↓ user commits → save_rule
  save_rule                 - Persist to rule library, link API key [INTERRUPT for approval]
  [end]

Checkpointer: PostgresSaver (Postgres-backed, keyed by session_id)
```

**Implementation notes:**

- Use LangGraph's `PostgresSaver` checkpointer so sessions survive backend restarts and can be resumed across devices.
- Each node is a plain Python function. No magic. LangGraph is a graph runner, not a DSL.
- The LLM calls from each node use the Anthropic API directly (not LangChain abstractions). LangGraph does not require LangChain for model calls; avoid the heavier dependency.
- Tools exposed to the LLM from within the graph are the same thetakit MCP tools plus a handful of Phase 2 extensions (the hosted eval endpoints). Reuse, do not rewrite.

**What LangGraph is not for in Phase 2:**

- Not for the request/response API paths. Those are boring FastAPI endpoints.
- Not for the compute itself. Modal runs the backtests; LangGraph does not.
- Not as an excuse to add LangChain everywhere. We use the graph runner and the checkpointer; that is it.

### 7.7 API Surface (FastAPI, REST + OpenAPI)

Abbreviated list; full spec generated from FastAPI. Versioned under `/v1`.

```
POST   /v1/auth/sessions            - Clerk session exchange
GET    /v1/me                       - Current user, balance, plan
POST   /v1/api-keys                 - Create API key
DELETE /v1/api-keys/{id}            - Revoke API key

GET    /v1/rules                    - List user's saved rules
POST   /v1/rules                    - Create or update a rule
GET    /v1/rules/{id}
DELETE /v1/rules/{id}
POST   /v1/rules/validate           - Validate without saving

POST   /v1/evals                    - Submit a smoke or full eval
GET    /v1/evals                    - List user's evals (paginated)
GET    /v1/evals/{id}               - Get eval status + summary
GET    /v1/evals/{id}/result        - Get full distributional result (S3-redirect)
POST   /v1/evals/{id}/cancel
POST   /v1/evals/compare            - Compare two evals

GET    /v1/billing/portal           - Stripe customer portal redirect
POST   /v1/billing/checkout         - Start Stripe checkout
POST   /v1/billing/webhook          - Stripe webhook receiver
GET    /v1/billing/history          - Credit ledger for the user

POST   /v1/agent/sessions           - Start a LangGraph rule authoring session
POST   /v1/agent/sessions/{id}/message
GET    /v1/agent/sessions/{id}/state

POST   /v1/internal/eval-complete   - Modal → API callback (shared-secret auth)

POST   /v1/mcp/run_smoke_eval       - MCP-compatible endpoints for OSS toolkit
POST   /v1/mcp/run_full_eval
GET    /v1/mcp/eval/{id}
```

All endpoints return problem+json on errors. OpenAPI spec auto-generated. Rate limits on the API-key surface (per-user, per-minute, per-day).

### 7.8 Performance and Cost Targets

- **Smoke eval:** p50 under 30s, p95 under 60s, measured end-to-end from submit to result. Modal cold start is the main risk; keep a warm pool.
- **Full eval:** p50 under 5 minutes, p95 under 10 minutes.
- **API response times:** p50 under 100ms for non-eval endpoints, p95 under 300ms.
- **Dashboard first-paint:** under 2 seconds on a median broadband connection.
- **Compute cost per full eval:** target under $0.40 on Modal. Budget $8 for a 20-credit full eval (at $50/200-credit pack, 20 credits is $5 of user spend, so margin target is ~85% at list price). This is a hard target — if compute cost exceeds it consistently, the pricing model breaks.
- **Database:** Postgres on Neon starter tier should be sufficient until ~500 active users.

### 7.9 Security and Compliance

- API keys are random 32+ byte tokens, hashed with bcrypt or argon2 at rest. Never stored in plaintext.
- All user data encrypted at rest (handled by Neon/S3).
- TLS everywhere. HSTS enabled.
- CSRF protection on browser requests. CORS locked to known frontend origins.
- Webhook signature verification for Stripe.
- Audit log for credit ledger events, rule saves, and API key creation/revocation.
- **Compliance posture:** research tool, not investment advice. Disclaimers reviewed by counsel before launch. No PII beyond email + OAuth provider ID. No financial account linking in Phase 2 (that would change the compliance story dramatically).
- Privacy policy and terms of service reviewed by counsel before launch.

### 7.10 Testing Strategy

- **Unit tests:** credit ledger logic (exhaustive — this is where silent money bugs live), rule validation, eval state transitions, LangGraph node functions.
- **Integration tests:** eval submission → Modal stub → callback → DB update happy path and failure paths. Use Modal's local runner mode.
- **Property tests:** credit ledger invariants (balance equals sum of deltas for every user, at every point in time).
- **End-to-end tests:** Playwright against a staging deployment running the full stack. Cover signup, first eval, paid eval, billing upgrade.
- **Model validation tests:** reference HMM must assign >3% transition probability to crisis regimes in the 30-day window before Feb 2018, Mar 2020, and Q4 2018. Gate on this in CI for model artifact updates.
- **Load testing:** simulate 50 concurrent full evals to verify Modal scaling and DB connection pool behavior before launch.

---

## 8. Success Metrics

**Leading indicators (check weekly for first 90 days post-launch)**

- **Signup → first smoke eval:** target 60% of new signups complete a smoke eval within their first session.
- **Signup → first full eval:** target 40% within first week.
- **Free → paid conversion:** target 15% of signups purchase credits or upgrade within 30 days.
- **Activation: time to first full eval:** median under 15 minutes from signup.
- **Eval success rate:** target above 98% of enqueued evals complete successfully.
- **OSS integration adoption:** target 30% of paying users configure their OSS CLI with an API key.

**Lagging indicators (check monthly for first 6 months)**

- **Paying users:** target 100 by end of Q4 2026.
- **MRR:** target $5–10k MRR by end of Q4 2026.
- **Retention:** target 70% month-over-month retention of paying users.
- **NPS:** target >40 from paying users.
- **Compute margin:** target >80% gross margin on eval compute.

**Trust metrics (check continuously)**

- **Model calibration:** each prediction logged; reviewed quarterly once N >200. No public calibration track record yet (Phase 3) but internal signal matters.
- **Eval result complaint rate:** if more than 5% of evals trigger a "this looks wrong" user report, the model has a bug. Treat as a P0 incident.
- **Disclaimer acknowledgment rate:** 100% at signup. No exceptions.

**Anti-metrics**

- **Silent credit consumption:** zero tolerance. Any user-reported case of credits consumed without a visible eval is a P0.
- **Full eval duration outliers:** if p95 > 15 minutes, investigate immediately; slow evals erode trust.
- **Dashboard errors in Sentry:** more than 5 per day sustained means something is broken.

---

## 9. Open Questions

1. **Auth provider:** Clerk vs. Supabase Auth. Clerk is cleaner DX, Supabase is one fewer vendor if we are already using Supabase Postgres. **Owner:** Founder. **Blocking:** yes, before backend scaffolding.
2. **Compute provider:** Modal vs. Celery+Redis+persistent workers. Modal wins at low-to-medium utilization; Celery wins at high steady-state. **Owner:** Founder + infra engineer. **Blocking:** yes, before compute implementation.
3. **Model artifact rollout strategy:** how do we roll out new HMM model versions? Shadow mode + compare? Hard cutover? Gradual by user cohort? **Owner:** Founder. **Blocking:** no, can ship with hard cutover and add gradual rollout later.
4. **Free tier calibration:** is 50 credits/month the right amount? Too generous and we lose money; too stingy and the onramp breaks. **Owner:** Founder. **Blocking:** no, will iterate post-launch.
5. **Pricing at launch:** the suggested tiers ($20/200, $50/600, $150/2000, $99/mo subscription) are my best guess. Real answer comes from beta user feedback. **Owner:** Founder. **Blocking:** no, commit to something and iterate.
6. **Legal disclaimers and methodology documentation:** counsel review needed before launch. Who and when? **Owner:** Founder. **Blocking:** yes, before public launch.
7. **Frontend contractor vs. solo:** if the founder/engineer are not TypeScript-native, do we hire a frontend contractor for 6 weeks? **Owner:** Founder. **Blocking:** no, but affects timeline.
8. **Data source for real-time regime inference:** for live rule recommendations, we need current feature values. Does this come from the same vendor as Phase 1 historical data, or a separate real-time feed? **Owner:** Founder. **Blocking:** yes, before eval service is usable for current-state evaluation.

---

## 10. Timeline and Phasing

Phase 2 is targeted at 12–14 weeks of focused work assuming Phase 1 has shipped and the founder + 1–2 engineers are available.

Suggested sub-phases:

- **Weeks 1–2:** Infrastructure scaffolding. Monorepo. Postgres. Auth. Basic FastAPI + Next.js apps deployed to staging. Clerk integrated. Stripe test mode configured.
- **Weeks 3–5:** Compute layer. Modal integration. Path simulator. HMM model loader (consuming the Phase 0 artifact). Smoke eval end-to-end working from API to Modal to DB. CLI integration from OSS.
- **Weeks 6–8:** Full eval. Stress scenario library. Aggregator. Result blob storage. Credit ledger. Billing webhooks.
- **Weeks 9–11:** Frontend dashboard. All six core visualizations. Eval submit and result views. Compare view. Billing UI. Account settings.
- **Week 12:** LangGraph rule authoring flow. Basic conversational path; polish is Phase 3.
- **Weeks 13–14:** Private beta with 20–30 users from Phase 1 community. Fix top-5 issues. Counsel review. Public launch.

**Hard constraints:**

- Phase 0 HMM validation must still be passing against refreshed data at the time of Phase 2 launch. Re-run the validation before public launch.
- Stripe live mode and counsel review both complete before public launch.
- First 100 paying users onboarded with founder-assisted activation, not pure self-serve.

**Dependencies:**

- Phase 1 OSS shipped and in use
- Phase 0 HMM model artifact
- Modal, Clerk, Stripe, Neon, Vercel, Fly accounts
- Counsel for disclaimer and privacy review

---

## 11. Appendix: Vibecoding Kickoff Prompt

If you are about to open Claude Code and start building Phase 2, a good opening prompt is:

> Read `spec-phase-2.md` in this repo. We are building `thetakit.cloud`, the hosted distributional evaluation service on top of the open source thetakit toolkit. Start with the infrastructure scaffolding from Section 10 Week 1–2: set up the monorepo structure from Section 7.2, initialize the FastAPI app in `apps/api`, set up Alembic migrations for the data models in Section 7.3, wire up Clerk auth for Phase 1 of the backend, and deploy a health-check endpoint to Fly.io. Next.js app in `apps/web` scaffolded with Clerk integration and a placeholder dashboard page. Do not start on Modal or the eval engine yet. Come back and show me the deploy URLs before moving on.

Scope subsequent prompts to single architectural areas: the credit ledger with exhaustive tests, the Modal compute integration with one synthetic eval, the path simulator, the visualization components one at a time. Stop to review at each boundary. The spec is dense enough that Claude can do 70–80% of the work per module without coming back for architectural decisions — but the credit ledger and the eval state machine are both places where a careful human review matters, so do not blindly accept agent output there.
