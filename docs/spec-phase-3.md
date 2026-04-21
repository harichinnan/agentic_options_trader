# Spec — Phase 3: Conversational Product, Continuous Tuning, and Calibration

**Working name:** TBD (placeholder: `thetakit.cloud`, Phase 3 features)
**Phase:** 3 of 5 (per roadmap)
**Target ship:** Q1 2027
**Status:** Draft, intended to be buildable directly
**Audience:** Founder + 2 engineers + designer, vibecoding from this doc
**Prerequisites:** Phase 2 shipped and in use, with at least 100 paying users and 200 resolved predictions logged via the forward-compat hooks.

> Phase 3 is where the product transforms from "a tool you run" into "a copilot that lives with you." Three capabilities define it: (1) polished conversational rule authoring with memory and version control, (2) a continuous tuning agent that watches your rules and flags drift, and (3) a public calibration track record that builds trust through measured honesty. Phase 4 (plugin directory distribution, content marketing push) is explicitly out of scope. Phase 5+ stretch bets (team mode, broker integration, mobile) are out of scope.

---

## 1. Problem Statement

Phase 2 shipped a hosted distributional evaluation service with a competent rule editor and a basic conversational onramp. It works. Paying users run evals, make decisions, and come back. But the product still feels like a tool — something you visit when you want to do a specific thing. It does not yet feel like a copilot that knows you, remembers your last conversation, watches your strategies drift over time, or tells you when the regime mix has shifted enough that your carefully-tuned rules from three months ago deserve a second look. Most importantly, the product has no public trust surface: users have to take our word that the distributional eval is calibrated, and "trust us, we do math" is a weak foundation for a product that influences real money.

The cost of not solving it in Phase 3: the product stays a tool, retention plateaus around Phase 2 levels, and the "our 70% predictions resolve 68% of the time" trust signal — which is the hardest-to-copy moat in the entire roadmap — never gets built.

---

## 2. Goals

1. **Make conversational rule authoring the primary interface.** The experience from intent to validated rule to committed eval should feel like talking to a thoughtful analyst, not navigating a form. State persists across sessions and devices. Users who prefer the YAML editor still have it, but most should reach for the conversation first.
2. **Ship continuous tuning as a background agent.** Scheduled check-ins examine a user's active rules against the current regime mix, run smoke evals, detect meaningful drift, and propose actionable tweaks — delivered via in-app inbox and email. This turns the product from a session into a relationship.
3. **Ship rule version control.** Every rule has history, branches, diffs, and revert. Every eval is attached to a specific rule version so results are always reproducible and auditable. The "how did my thinking evolve" view matters for serious users and the compliance-adjacent audit trail matters for regulators if the product ever moves toward advisory.
4. **Ship portfolio-level risk narration.** Users can upload their current positions (CSV or manual entry) and the agent can narrate portfolio-level risk in plain English — net Greeks, calendar exposure, regime sensitivity, concentration risk, and the delta between their actual book and what their rules would say to hold.
5. **Ship the public calibration dashboard.** Aggregated, anonymized calibration curves and Brier scores for every prediction the agent has made, broken down by confidence decile and prediction type. This is the trust surface that differentiates the product from every competitor who says "we use AI" without measuring it.
6. **Ship personal calibration tracking.** Each user sees their own calibration history — their agent's predictions scored against their actual outcomes. Private by default, with an optional share link.

---

## 3. Non-Goals

1. **No broker integration, no live trading, no order routing.** Still the hard line. Positions come in via CSV or manual entry only.
2. **No team / multi-seat features.** Phase 5+.
3. **No mobile app.** Responsive web is enough. Mobile is Phase 5+ at the earliest.
4. **No custom per-user model retraining.** Everyone shares the fitted HMM from Phase 2. Per-user calibration tracking uses a single shared model.
5. **No plugin directory submission.** Phase 4.
6. **No content marketing push as a feature of the product.** The website may gain blog capabilities but the editorial program is a Phase 4 concern.
7. **No investment advisory licensing.** The product remains research and analysis. Legal boundaries from Phase 2 hold.
8. **No alternative asset classes.** US equity options only, still.
9. **No multi-model ensembling.** One HMM, one eval pipeline, one source of truth. Ensembles are a Phase 5+ research direction.

---

## 4. Target Users

**Primary persona — "The Phase 2 power user"**
Already paying, already using the hosted eval service, probably running several distinct strategy rule sets for different slices of their portfolio. Checks the product at least weekly. Has strong opinions about what the tool gets right and wrong. Wants less friction, more memory, and a reason to treat the product as the center of their workflow rather than a utility they visit.

**Secondary persona — "The cautious new user who cared about trust"**
Lands on the marketing site, sees the public calibration dashboard on the homepage, and signs up specifically because the product is willing to be measured. This persona is defined by the calibration surface existing; they would not have converted in Phase 2.

**Tertiary persona — "The returning lapser"**
Signed up in Phase 2, ran a few evals, then fell off. Phase 3's continuous tuning emails bring them back with specific, actionable context. This is a retention play, not an acquisition play.

**Explicit non-persona:**
The user who wants the agent to run their account for them. Phase 3 pushes closer to "active recommendation" territory but still stops short of autonomous action. If a user wants autopilot, they are not a Phase 3 user and should not be nurtured toward one.

---

## 5. User Stories

**Conversational rule authoring with memory**

- As a returning user, I want the agent to remember my risk tolerance, preferred underlyings, and past decisions so that I am not re-explaining my context every session.
- As a returning user, I want to resume a conversation I started yesterday so that I do not lose my train of thought when I switch devices.
- As a user, I want the agent to know which rules I currently have active so that its suggestions are grounded in my real portfolio.
- As a user, I want the agent to reference my past eval results when proposing tweaks so that the conversation builds on history, not starts from zero.
- As a user, I want the agent to push back on my ideas when it has evidence they are risky so that I get sparring, not sycophancy.

**Rule version control**

- As a user, I want every save to create a new version of a rule so that I can review how my thinking has evolved.
- As a user, I want to name branches of a rule (e.g., "main", "aggressive", "experimental") so that I can keep parallel drafts without losing my main strategy.
- As a user, I want a visual diff between two versions of a rule so that I can see exactly what changed.
- As a user, I want to revert a rule to an earlier version with one click so that I can undo a bad change.
- As a user, I want every eval to be attached to a specific rule version so that my results are reproducible and my decision history is auditable.
- As a user, I want to see the eval history for a rule over time so that I can watch the distributional outcomes shift as I refine the rule.

**Continuous tuning**

- As a user, I want the product to watch my active rules and notify me when the regime mix has shifted enough to matter so that I do not have to re-run evals on a schedule I set manually.
- As a user, I want tuning proposals to come with specific reasoning ("the regime mix has shifted from 60% normal to 40% normal / 40% elevated, and your CSP delta target of 0.35 is now showing elevated tail risk — consider tightening to 0.30") so that I can evaluate the suggestion on its merits.
- As a user, I want to accept, reject, or open a conversation on each tuning proposal so that the agent learns what I care about.
- As a user, I want tuning check-ins on a schedule I control (daily, weekly, biweekly, or only when something is urgent) so that I am not spammed.

**Portfolio upload and risk narration**

- As a user, I want to upload a CSV of my current positions (from Tastytrade, IBKR, Schwab export formats) so that the agent can reason about my actual book.
- As a user, I want to enter positions manually for small accounts or edge cases so that I am not forced into CSV workflows.
- As a user, I want the agent to narrate my portfolio-level risk — net Greeks, largest exposures, calendar risk, concentration — so that I do not have to compute this from a spreadsheet.
- As a user, I want the agent to tell me when my actual book has drifted from what my rules would say to hold so that I can see my own discipline lapses.
- As a user, I want my positions to update when I upload a new CSV, with a history so I can see how my book evolved.

**Calibration (personal and public)**

- As a user, I want to see my personal calibration curve — across all predictions the agent has made in my conversations — so that I know whether to trust the tool's probabilities as applied to me.
- As a user, I want to see the public calibration curve — aggregate performance across all users — so that I can compare my personal experience to the global baseline.
- As a skeptical prospect, I want to see a public calibration dashboard *before I sign up* so that I can evaluate the product's honesty without giving my email.
- As a user, I want individual predictions to be labeled with their resolution criteria and outcomes so that I can spot-check the calibration numbers myself.

---

## 6. Requirements

### 6.1 Must-Have (P0) — Ship Blockers

**Conversational rule authoring with memory**

- LangGraph-backed agent with Postgres checkpointing, resumable across sessions and devices.
- Long-term user memory stored as a structured profile document (risk tolerance, preferred underlyings, strategy types in use, past decisions) read at the start of each session and updated at the end.
- Agent has access to the user's rule library, eval history, portfolio (if uploaded), and conversation history via tool calls.
- Agent can reference specific past evals and rule versions in its responses ("your Wheel rule v7 had a 24% drawdown in the elevated regime; v9 tightened that to 18% — want to see why?").
- In-app chat interface with resumable threads, message history, rich rendering of eval summaries and plots inline.
- **Acceptance:** A user can start a conversation on their laptop, switch to desktop, and resume the conversation with full context intact, including any in-flight eval. The agent correctly references at least one piece of information from a previous session within the first two turns of a returning conversation.

**Rule version control**

- Content-addressed rule storage: every save computes a hash of the rule YAML and stores it as an immutable version. Duplicate saves are deduplicated by hash.
- Named refs (like git branches) per user per rule: `main`, user-created branches.
- Diff view: visual side-by-side or unified diff between any two versions of a rule, rendered in the web UI.
- Revert: one-click to move a ref to an earlier version. Old versions are never deleted.
- Full history view: timeline of all versions of a rule with linked evals and summary stats for each.
- Every eval record stores the exact rule version hash used, not just the rule ID.
- **Acceptance:** A user can make five edits to a rule, view the full history, diff version 2 against version 5, and revert to version 3. Every eval in the history view shows its distributional summary and a link to the full result.

**Continuous tuning agent**

- Scheduled background jobs per user: daily, weekly, biweekly, or "urgent only" cadence, user-configurable per rule.
- On each run, the agent: (a) fetches current regime posterior from the HMM, (b) runs a smoke eval on the user's active rules, (c) compares to the most recent full eval attached to that rule version, (d) classifies the drift as "none", "minor", "notable", or "urgent", and (e) for notable/urgent drifts, generates a proposal.
- Proposals include: plain-English narration of what changed, specific suggested parameter tweaks, the expected impact on distributional outcomes, and a link to a one-click "run full eval on the tweaked version" action.
- Delivery channels: in-app inbox (always), email (user-configurable), optional webhook for Discord/Slack (P1).
- Rate limiting: no more than one "notable" proposal per rule per week; "urgent" proposals can interrupt but are themselves rate-limited to one per rule per 72 hours.
- Proposal audit trail: every proposal is logged with the agent's reasoning, the smoke eval that triggered it, and the user's response (accepted, rejected, discussed, ignored).
- **Acceptance:** In a simulated regime shift (inject a fake regime change into a test user's data), the continuous tuning agent generates a notable-severity proposal within 24 hours, the proposal references the specific regime change, and the user can accept-and-commit or open a conversation on it from the in-app inbox.

**Portfolio upload and narration**

- CSV importers for Tastytrade, IBKR, and Schwab export formats. Schema-detect on upload; ask for confirmation if ambiguous.
- Manual position entry form for positions not in a CSV.
- Position storage: append-only history of position snapshots, each with timestamp and source.
- Live Greek computation per position using current market data and the IV surface from the Phase 1 data layer.
- Portfolio narration tool callable from the agent: returns net Greeks, top 5 largest-exposure positions, calendar exposure (days to nearest earnings/Fed/OPEX for each position), regime sensitivity of the current book, and a drift score vs. what the user's rules would have held.
- **Acceptance:** A user can upload a Tastytrade CSV with 15 positions, see them parsed correctly within 10 seconds, and ask the agent "what's the biggest risk in my book?" to get an actionable plain-English response grounded in the actual positions.

**Calibration tracking and dashboard**

- Prediction resolution engine: scheduled job that examines unresolved predictions and checks whether their resolution criteria are met based on market data.
- Each prediction has a machine-readable resolution criterion (e.g., "SPY returns 21 days >= -2%", "user's strategy X realized drawdown < 5% over next 30 days") and a predicted probability.
- Personal calibration view: per-user calibration curve (predicted probability deciles vs. realized frequency), Brier score, and a list of recent resolved predictions with outcomes. Private by default.
- Public calibration dashboard: same view but aggregated across all users, anonymized, updated daily. Linked from the marketing site homepage and from the in-app nav. No login required to view.
- Confidence-interval bands on the public calibration curve (Wilson score intervals) so users can see sample-size uncertainty.
- Filtering in the public dashboard: by prediction type (regime transition, strategy outcome, roll decision), by time window (last 30 days, last 90 days, all time), by confidence decile.
- **Acceptance:** The public calibration dashboard shows at least 200 resolved predictions within 30 days of launch (leveraging Phase 2 logging hooks). The displayed curve is within sample-error bounds of a simulated ground truth on a test dataset.

**LangGraph architecture upgrades**

- Three named graphs, each with its own state machine: `rule_authoring`, `rule_revision`, `continuous_tuning`, and `portfolio_review`.
- Shared memory layer: user profile document persisted in Postgres, loaded by all graphs at the start of their runs.
- Resumable interrupts: long-running operations (full evals, user approval gates) use LangGraph's `interrupt` primitive with Postgres checkpointing.
- Cross-graph context: the continuous tuning graph can hand off to the rule revision graph (e.g., "user accepted the proposal; open a revision conversation").

**API additions (extending Phase 2)**

```
POST   /v1/rules/{id}/versions             - Explicitly create a new version
GET    /v1/rules/{id}/versions             - List versions
GET    /v1/rules/{id}/versions/{hash}      - Get specific version
POST   /v1/rules/{id}/branches             - Create a branch
POST   /v1/rules/{id}/revert               - Revert ref to hash
GET    /v1/rules/{id}/diff                 - Diff two versions

POST   /v1/portfolio/positions/import      - CSV upload
POST   /v1/portfolio/positions             - Manual position
GET    /v1/portfolio/positions             - Current positions
GET    /v1/portfolio/history               - Snapshot history
GET    /v1/portfolio/narration             - Agent-generated narration

GET    /v1/tuning/schedules                - List user's tuning schedules
PUT    /v1/tuning/schedules/{rule_id}      - Configure cadence
GET    /v1/tuning/proposals                - List recent proposals
POST   /v1/tuning/proposals/{id}/accept
POST   /v1/tuning/proposals/{id}/reject
POST   /v1/tuning/proposals/{id}/discuss   - Opens a LangGraph revision session

GET    /v1/calibration/personal            - Per-user calibration
GET    /v1/calibration/public              - Public aggregate (unauthenticated)
GET    /v1/predictions/{id}                - Individual prediction detail

POST   /v1/chat/sessions                   - Start conversational session
POST   /v1/chat/sessions/{id}/messages
GET    /v1/chat/sessions/{id}              - Resume
```

### 6.2 Nice-to-Have (P1) — Ship If Time Permits

- Voice input for the conversational interface (iOS Safari's dictation is free; implementing it cleanly is not).
- Discord and Slack webhook delivery for tuning proposals.
- "Explain this eval" button on any eval result that opens a conversation seeded with the eval's context.
- Exportable personal calibration report (PDF).
- Named presets for portfolio upload from additional brokers (TD, E*TRADE, Fidelity).
- Visual regime timeline on the portfolio page showing when each position was opened against historical regime.
- A/B testing framework for tuning proposal phrasing (does "consider tightening" perform better than "I'd tighten" in acceptance rates?).

### 6.3 Future Considerations (P2) — Explicitly Out of Scope, Design For

- **Team / org features (Phase 5+):** the `org_id` column reserved in Phase 2 gets used. Rule libraries and portfolios become org-scoped optionally. Approval workflows for rule commits in org mode.
- **Read-only broker OAuth (Phase 4–5):** the portfolio layer must treat "source" as an abstraction (CSV, manual, future OAuth), so adding live sync is a new source, not a rewrite.
- **Autonomous execution (never, probably, but designed around the possibility):** the portfolio layer and the rule commit layer should be logically separable from any execution layer, so the regulatory story stays clean.
- **Multi-model ensembles (Phase 5+):** the prediction and eval layers should be model-version-aware so that comparing predictions from multiple models is feasible without a schema rewrite.

---

## 7. Architecture and Technical Design

### 7.1 Stack Changes from Phase 2

Minimal. Phase 3 is mostly new features on the Phase 2 stack. Explicit changes:

- **Scheduling:** add a scheduler layer for the continuous tuning jobs. Recommend **`apscheduler`** running inside the FastAPI app for simplicity, or a dedicated lightweight scheduler service if the API is getting heavy. Do not introduce Airflow or Prefect; overkill.
- **Prediction resolution engine:** a daily cron job that sweeps unresolved predictions. Runs as a Modal scheduled function or a FastAPI background task, depending on what is already deployed.
- **Chat UI components:** extend the Next.js app with a real chat interface. Use `@assistant-ui/react` or build custom on top of shadcn — prefer custom for full control.
- **Diff rendering:** `react-diff-view` or similar for the rule diff UI.
- **CSV parsing:** `papaparse` in the frontend for client-side preview, `polars.read_csv` in the backend for canonical parsing.
- **New LangGraph graphs:** no framework change, just more graph definitions.
- **Background job visibility:** add a minimal admin dashboard for monitoring scheduled jobs, failed predictions, and proposal generation. Can be a protected admin route in the existing Next.js app.

Explicitly *not* changing:

- Database (still Postgres on Neon)
- Compute runtime (still Modal for evals)
- Auth (still Clerk)
- Billing (still Stripe)
- Chart library (still Plotly)

### 7.2 New Data Models

Additions to the Phase 2 schema. Migrations via Alembic.

```python
class RuleVersion(Base):
    id: UUID
    rule_id: UUID (fk)
    content_hash: str (indexed)
    yaml_source: str
    parent_hash: str | None
    created_at: datetime
    created_by_session_id: UUID | None  # which chat session produced this
    commit_message: str | None          # agent-generated or user-provided
    # Eval rows now reference (rule_id, content_hash) as compound key

class RuleRef(Base):
    rule_id: UUID (fk)
    name: str                           # "main", "aggressive", etc.
    content_hash: str                   # current head of this ref
    updated_at: datetime
    # primary key (rule_id, name)

class Position(Base):
    id: UUID
    user_id: UUID (fk)
    snapshot_id: UUID (fk)
    symbol: str
    option_type: Literal["CALL", "PUT", "STOCK"] | None
    strike: float | None
    expiration: date | None
    quantity: int                       # signed
    cost_basis: float
    opened_at: date | None

class PositionSnapshot(Base):
    id: UUID
    user_id: UUID (fk)
    source: Literal["csv_tastytrade", "csv_ibkr", "csv_schwab", "manual"]
    created_at: datetime
    position_count: int
    raw_source_hash: str | None         # hash of original CSV for idempotency

class TuningSchedule(Base):
    id: UUID
    user_id: UUID (fk)
    rule_id: UUID (fk)
    cadence: Literal["daily", "weekly", "biweekly", "urgent_only"]
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime

class TuningProposal(Base):
    id: UUID
    user_id: UUID (fk)
    rule_id: UUID (fk)
    rule_version_hash: str
    schedule_id: UUID (fk)
    severity: Literal["minor", "notable", "urgent"]
    triggered_by_eval_id: UUID (fk)
    narration: str                      # plain English
    proposed_tweaks: JSONB
    reasoning: JSONB                    # structured agent reasoning
    created_at: datetime
    user_response: Literal["pending", "accepted", "rejected", "discussed", "ignored"] | None
    responded_at: datetime | None
    delivered_channels: list[str]        # ["inbox", "email"]

class ChatSession(Base):
    id: UUID
    user_id: UUID (fk)
    graph_name: Literal["rule_authoring", "rule_revision", "continuous_tuning", "portfolio_review"]
    title: str                          # agent-generated
    created_at: datetime
    last_activity_at: datetime
    langgraph_thread_id: str            # pointer into LangGraph checkpoint store
    context: JSONB                      # active rule_id, active eval_id, etc.

class UserProfile(Base):
    user_id: UUID (pk, fk)
    risk_tolerance: Literal["conservative", "balanced", "aggressive"] | None
    preferred_strategies: list[str]
    typical_capital: int | None
    stated_goals: str | None
    notes: str                          # free-form, agent-updated
    updated_at: datetime

# Prediction table from Phase 2 gets new indexing for dashboard queries,
# and a new column:
# Prediction.is_public_dashboard: bool  -- eligible for public aggregation
```

### 7.3 LangGraph Graph Definitions

Phase 3 introduces four named graphs. Each is a plain Python function collection wired into a LangGraph `StateGraph`. All share a common `UserState` schema loaded at entry and persisted at exit.

**Graph: `rule_authoring` (Phase 2 graph, upgraded with memory)**

```
[start]
  ↓
load_user_profile
  ↓
gather_requirements       ← now reads profile for defaults
  ↓
draft_rule
  ↓
validate_rule
  ↓ pass
smoke_eval
  ↓
review_smoke
  ↓ user wants tweaks → draft_rule
  ↓ user commits → full_eval_prompt [INTERRUPT]
  ↓ approved
full_eval                 [INTERRUPT until complete]
  ↓
review_full
  ↓ user commits → save_rule_version
  ↓
update_user_profile       ← persists what we learned
  ↓
[end]
```

**Graph: `rule_revision` (new in Phase 3)**

Invoked when the user clicks "discuss" on a tuning proposal or "revise this rule" on an existing rule. Differs from `rule_authoring` by starting with a specific existing rule version and proposal context, not blank.

```
[start]
  ↓
load_context (rule, version history, recent evals, active proposal if any)
  ↓
propose_diff             ← agent shows what it would change and why
  ↓ user accepts → validate_rule → smoke_eval → review_smoke → ...
  ↓ user iterates → propose_diff
  ↓ user rejects → end with no changes
```

**Graph: `continuous_tuning` (new in Phase 3, headless)**

Runs on schedule, no user in the loop during execution. Produces TuningProposal rows, delivers them, and ends. No interrupts — this is a batch graph.

```
[start]
  ↓
load_user_rules
  ↓
load_current_regime_posterior
  ↓
(parallel per rule)
  run_smoke_eval
  ↓
  compare_to_last_full_eval
  ↓
  classify_drift
  ↓
  generate_proposal (if drift >= notable)
  ↓
deliver_proposals
  ↓
update_schedule
  ↓
[end]
```

**Graph: `portfolio_review` (new in Phase 3)**

Invoked when the user asks the agent about their portfolio.

```
[start]
  ↓
load_positions
  ↓
compute_portfolio_greeks
  ↓
compute_calendar_exposure
  ↓
compute_regime_sensitivity
  ↓
compute_rule_drift (actual vs. what rules would have held)
  ↓
narrate (LLM call, grounded in computed facts)
  ↓
[end]
```

**Implementation notes:**

- All graphs use `PostgresSaver` with a unified thread table. Thread IDs map 1:1 to `ChatSession.langgraph_thread_id`.
- The LLM nodes use Claude Sonnet 4.6 for user-facing conversation and Claude Haiku 4.5 for classification, drift detection, and structured tool inputs where cost matters.
- Every graph's final node calls `update_user_profile` with the relevant deltas learned in the session. This is how long-term memory accretes without a full vector store.
- Prediction logging: each node that emits a probabilistic claim (agent's confidence in a proposed tweak, agent's regime forecast, agent's expected outcome) writes a `Prediction` row with a resolution criterion before the session ends. This is mandatory and enforced via a graph-level post-processor, not left to individual nodes.

### 7.4 Rule Version Control Design

Content-addressed storage is the load-bearing abstraction. Design notes:

- **Hash function:** SHA-256 of a canonicalized YAML serialization (sorted keys, normalized whitespace, no comments). This gives deduplication across functionally-identical saves.
- **Immutability:** `RuleVersion` rows are never updated. Corrections happen by creating new versions.
- **Refs, not branches:** we call them "branches" in the UI because that's what users expect, but internally they're refs — named pointers to hashes that can move freely.
- **Revert semantics:** reverting `main` to an older hash is an update to the `RuleRef` row, not a delete of intermediate versions. History is preserved.
- **Orphaned versions:** if a branch is deleted and no eval references its tip, the tip becomes orphaned but is never garbage-collected in Phase 3. Storage is cheap, and users expect history to be permanent. Revisit in Phase 5+ if it becomes expensive.
- **Eval attachment:** the `Eval` table gains a `rule_version_hash` column and an index on `(rule_id, rule_version_hash)`. Old evals from Phase 2 are migrated to attach to the version that was current at eval time (best-effort — document the migration in the release notes).
- **Diff rendering:** compute diffs in the backend (Python's `difflib` is sufficient) and render in the frontend using a visual diff component. Semantic diffs that understand the rule DSL structure (e.g., "delta target changed from 0.35 to 0.30") are a stretch for P1.

### 7.5 Continuous Tuning: Drift Classification

The most important unsolved question in continuous tuning is: **what counts as drift worth bothering the user about?** Getting this wrong is product death — too sensitive and users mute notifications, too insensitive and the feature is invisible.

The drift classifier is deterministic, not LLM-based. It takes two distributional eval results (the old full eval and the new smoke eval) and produces a severity label:

- **None:** no material change in any key statistic.
- **Minor:** small shift in median or quartiles, tail unchanged.
- **Notable:** tail statistics (5th percentile P&L, CVaR 5%) have shifted by more than a configurable threshold, or the regime mix the strategy is now being evaluated under differs from the commit-time mix by more than a threshold.
- **Urgent:** the strategy now shows catastrophic tail risk it did not show at commit time, OR the regime mix has moved decisively toward a regime where the strategy's conditional performance was historically the worst.

Initial thresholds (tune post-launch):

- Notable if: |Δ 5th-pct P&L| / |commit 5th-pct P&L| > 0.25, or regime mix JS-divergence > 0.15
- Urgent if: |Δ 5th-pct P&L| / |commit 5th-pct P&L| > 0.5, or probability of crisis regime > 15% with strategy conditionally negative-expected in crisis regime

The agent node in the `continuous_tuning` graph takes the severity label and the underlying numbers, and generates the narration. The LLM is not deciding whether to fire; the deterministic classifier decides. This keeps the fire rate predictable and tunable, and it means bugs in the LLM never cause spam.

### 7.6 Calibration Resolution Engine

The prediction resolution engine is a daily scheduled job that sweeps unresolved `Prediction` rows and marks them resolved with their outcomes. Resolution criteria are structured so a deterministic evaluator can check them.

Supported criterion types:

- **Market-outcome criterion:** "SPY return over window [start, end] >= X%" — evaluated against historical data after `end`.
- **User-strategy-outcome criterion:** "user's rule X, attached to version Y, realized drawdown over window [start, end] is within band [lo, hi]" — evaluated by running a fast backtest of the locked rule version over the window against actual market data.
- **Regime-transition criterion:** "HMM regime at date D is in set S" — evaluated against the regime posterior at D using the current model.

Each `Prediction` row carries one criterion JSON and a target resolution date. The daily sweep evaluates all predictions with `resolution_date <= yesterday`. Resolutions are append-only; once resolved, a prediction is never re-resolved.

**Fairness guarantee:** the public calibration dashboard only aggregates predictions that were logged at least 24 hours before their resolution could be observed. This prevents look-ahead concerns.

**Model-version honesty:** when a prediction is scored, the model version at prediction time is recorded. If the model is later retrained, old predictions are not re-evaluated under the new model. The calibration curve can be filtered by model version so we do not conflate eras.

### 7.7 Public Calibration Dashboard

This is the marketing homepage feature, and getting it right is worth disproportionate effort.

**Visible primitives:**

- A calibration curve: x-axis is predicted probability decile (0–10%, 10–20%, ..., 90–100%), y-axis is realized frequency in that decile. A perfectly calibrated model traces the diagonal.
- Wilson score confidence intervals on each decile, visualized as vertical bands.
- A headline number: aggregate Brier score, with a reference comparison ("0.18 — for context, a coin-flip baseline is 0.25 and a perfectly calibrated forecaster approaches 0").
- Sample size per decile, visible on hover.
- Filters: prediction type, time window, model version.
- Last updated timestamp with the date of the most recent resolved prediction included.

**Explicit honesty features:**

- If sample size in any decile is below 30, the decile is shown with a warning visual and a "insufficient sample" label.
- Predictions that were flagged as high-model-uncertainty at emission time are shown separately, not mixed into the main curve.
- The methodology page is linked from the dashboard header. It describes exactly what is and is not included, how criteria are evaluated, and the known limitations.

**What the dashboard must not do:**

- Cherry-pick. If a prediction type would make the calibration look bad, it still appears. The only predictions excluded are those that were never logged as dashboard-eligible at emission time — and that flag is set at emission time, not retroactively.
- Suppress bad results for marketing reasons. Ever. The dashboard's value is exactly that it cannot be gamed.
- Show predictions that are not yet resolved. Unresolved is not the same as "our AI got it right."

### 7.8 Portfolio Upload Parsing

CSV parsers are usually where products die from death-by-edge-case. Approach:

- Ship with three named adapters (Tastytrade, IBKR, Schwab) and a fallback manual column-mapping UI.
- On upload, run heuristic format detection. If unambiguous, parse. If ambiguous, show the column-mapping UI with the agent's best-guess pre-filled.
- Validate parsed positions against a strict schema before persisting. Any row that fails validation is shown to the user for manual fix, not silently dropped.
- Preserve the raw CSV as a blob with a hash for idempotent re-uploads.
- Greek computation uses the Phase 1 pricing engine against current market data — same code, different input.

**Column mapping UI is P0, not P1.** Without it, the third broker integration breaks and the user has no recovery path.

### 7.9 Performance and Cost Targets

- **Chat message latency:** p50 under 1.5s for Sonnet responses, p95 under 4s (dominated by LLM latency, not our code).
- **Scheduled tuning job:** daily batch completes for all users within 30 minutes of scheduled start. At 1000 active users with 3 rules each, that is 3000 smoke evals per day, which fits comfortably in Modal.
- **Prediction resolution sweep:** daily, under 2 minutes regardless of prediction volume.
- **Public calibration dashboard:** cached, refreshed hourly. Dashboard page load under 1 second.
- **Continuous tuning compute cost:** budget $0.10 per user per day (driven by smoke eval compute at 3 rules/day per user). At 1000 active users, $100/day, absorbed by subscription revenue.

### 7.10 Testing Strategy

- Existing Phase 2 test suite continues to pass.
- **New unit tests:** rule version hashing and diffing, drift classifier thresholds, prediction criterion evaluators (each type), CSV parsers (one golden file per broker).
- **New integration tests:** full `continuous_tuning` graph run on a synthetic user with synthetic drift, verifying a proposal is created and delivered; full `rule_authoring` graph run verifying profile updates persist; prediction resolution sweep against a fixture database.
- **End-to-end tests:** Playwright flows for chat resume-across-devices, rule version history navigation, tuning proposal accept/reject, calibration dashboard public view.
- **Fairness audits:** a synthetic adversarial test harness that tries to make the public calibration look artificially good by injecting high-confidence predictions — verify the dashboard does not silently suppress them.
- **Load testing:** simulate 1000 concurrent chat sessions with LLM calls stubbed, verify Postgres checkpoint store does not bottleneck.

---

## 8. Success Metrics

**Leading indicators (check weekly for first 90 days post-launch)**

- **Chat session resumption rate:** % of chat sessions resumed across devices/days. Target: above 30%.
- **Tuning proposal acceptance rate:** of proposals delivered, what fraction are accepted or discussed (not ignored)? Target: above 40%.
- **Tuning proposal quality signal:** among accepted proposals, what fraction lead to a committed rule change within 7 days? Target: above 50%.
- **Portfolio upload adoption:** % of active users who upload a portfolio within 30 days of Phase 3 launch. Target: above 35%.
- **Version control engagement:** % of active users with at least one non-`main` branch. Target: above 15% (most users will not need branches — that is OK).
- **Public calibration dashboard traffic:** unique visitors per week to the public dashboard from the marketing site. Target: above 500/week after first 90 days.
- **Calibration dashboard → signup conversion:** % of public dashboard visitors who sign up. Target: above 3%.

**Lagging indicators (check monthly for first 6 months)**

- **Retention lift from Phase 2 baseline:** target +20% 90-day retention among new signups.
- **MRR growth:** target 2x MRR by end of Q2 2027 vs. Phase 2 exit.
- **NPS:** target above 50 from paying users.
- **Returning-lapser reactivation:** % of Phase 2 churned users who return after receiving a tuning proposal email. Target: above 10%.
- **Public calibration track record:** at least 1000 resolved, dashboard-eligible predictions with a calibration curve within ±5pp of the diagonal across all deciles. This is the headline trust claim — get it right.

**Anti-metrics**

- **Tuning proposal mute rate:** % of users who disable tuning notifications within 30 days of receiving their first. If above 20%, the drift classifier is too sensitive — retune thresholds before shipping more features.
- **Calibration dashboard sample-starvation:** if any decile on the public dashboard shows fewer than 30 samples after 60 days, the prediction emission rate is wrong.
- **LLM cost per active user:** target below $2/user/month. If above $5, refactor to move more decisions into Haiku and deterministic classifiers.

---

## 9. Open Questions

1. **Default tuning cadence:** what should the out-of-box cadence be for new users? Weekly feels right but has no data behind it. **Owner:** Founder. **Blocking:** no, default to weekly and iterate.
2. **Calibration dashboard granularity:** show all prediction types together, or segmented by default? Segmented is more honest but harder to parse at a glance. **Owner:** Founder + designer. **Blocking:** no, ship segmented with an "all" tab.
3. **Long-term memory mechanism:** structured profile document (my recommendation) vs. vector store vs. full conversation replay. **Owner:** Founder. **Blocking:** yes, before LangGraph work begins.
4. **Prediction resolution corner cases:** how do we handle predictions whose criteria cannot be evaluated (data vendor outage, retired underlying, model retrained)? **Owner:** Founder. **Blocking:** yes, design the exception flow before launch.
5. **Public dashboard launch threshold:** what's the minimum sample size to go public? 500? 1000? Launching too early with wide bands looks unconfident; launching too late delays the headline trust feature. **Owner:** Founder. **Blocking:** yes, set a specific threshold.
6. **Broker CSV edge cases:** which formats must ship at launch and which can wait for P1? **Owner:** Founder + beta users. **Blocking:** no, ship with three, add more on demand.
7. **Email delivery:** transactional email provider (Postmark, Resend, SES). **Owner:** Founder. **Blocking:** yes, before tuning notification work.
8. **Designer engagement:** is a part-time designer hired for Phase 3, or do we run on founder taste + shadcn? The chat interface and calibration dashboard are UX-heavy features that benefit from real design work. **Owner:** Founder. **Blocking:** no, but quality ceiling is limited without a designer.

---

## 10. Timeline and Phasing

Phase 3 is targeted at 14–16 weeks with founder + 2 engineers + part-time designer.

Suggested sub-phases:

- **Weeks 1–2:** Foundations. Rule version control backend (content-addressed storage, refs, diffs). Schema migrations. Version-aware eval attachment. Prediction resolution engine scaffolding.
- **Weeks 3–4:** Portfolio upload. CSV parsers (Tastytrade, IBKR, Schwab). Manual entry. Position snapshot history. Live Greek computation against existing pricing engine. Portfolio API.
- **Weeks 5–7:** LangGraph upgrades. Shared memory / user profile. Four named graphs. Migration of Phase 2 rule authoring graph into the new pattern. Chat session persistence across devices.
- **Weeks 8–9:** Continuous tuning. Scheduler. Drift classifier. Headless tuning graph. Proposal delivery (inbox + email). Tuning admin dashboard for monitoring.
- **Weeks 10–11:** Chat UI in the Next.js app. Conversation history, resume, inline eval rendering, rich formatting. Rule version history UI. Diff viewer.
- **Weeks 12–13:** Calibration dashboard. Personal view. Public view. Wilson intervals. Filters. Methodology page. Marketing homepage integration.
- **Week 14:** Private beta with 30 Phase 2 power users. Collect feedback on tuning cadence, drift classifier thresholds, chat UX.
- **Weeks 15–16:** Fix top issues. Public launch. Announcement post with calibration dashboard as the hero.

**Hard constraints:**

- Public calibration dashboard must not launch until it has the minimum sample size from the Open Questions (currently TBD; set before work begins).
- Continuous tuning must ship with a muteable-by-default for the first two weeks of general availability, and the mute rate must be monitored closely.
- Any change to the prediction resolution engine or the calibration dashboard requires a second engineer's review. This is the trust surface and it cannot be corrupted.

**Dependencies:**

- Phase 2 live with stable prediction logging (confirm before starting Phase 3)
- HMM model artifact available and the regime posterior endpoint reliable
- Part-time designer identified by Week 3 at the latest
- Email provider selected by Week 8

---

## 11. Appendix: Vibecoding Kickoff Prompt

If you are about to open Claude Code and start building Phase 3, a good opening prompt is:

> Read `spec-phase-3.md` in this repo. We are extending `thetakit.cloud` with conversational rule authoring, continuous tuning, portfolio upload, and a public calibration dashboard. Start with the rule version control backend from Section 7.4 and the schema additions from Section 7.2. Write Alembic migrations for RuleVersion, RuleRef, Position, PositionSnapshot, TuningSchedule, TuningProposal, ChatSession, and UserProfile. Implement content-addressed rule storage with SHA-256 hashing of canonicalized YAML. Add the new API endpoints from Section 6.1 for rule versions, branches, diffs, and reverts. Write unit tests for hashing determinism and diff correctness. Do not touch LangGraph, portfolio upload, or the calibration dashboard yet. Show me the migration plan and the test results before moving on.

Subsequent prompts should continue the module-by-module discipline. The two modules to slow down and hand-review are **the prediction resolution engine** (trust surface, bugs here corrupt the calibration dashboard silently) and **the drift classifier thresholds** (product feel, easy to get wrong, hard to fix after users have muted notifications).
