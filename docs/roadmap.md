# Options Copilot — Product Roadmap

**Working name:** TBD
**One-liner:** Git + CI for trading rules, with regime-aware distributional evaluation. A risk-managed premium-selling copilot for serious retail options traders.
**Strategy:** Open core. Code is open source. Trained models, calibrated parameters, and the hosted evaluation service are proprietary.
**Date:** April 2026

---

## Open Source vs. Proprietary Split

This is the single most important architectural decision on the roadmap and it shapes every phase below. Be explicit about it from day one or you will leak your moat by accident.

**Open source (permissively licensed, on GitHub from Phase 1):**

- MCP server skeleton and tool surface
- Rule DSL, parser, validator
- Backtest engine framework (historical-data mode)
- Strategy simulator (position lifecycle, rolling logic, Greeks computation)
- Conversational skill files and prompt templates
- Plugin packaging and distribution tooling
- Data adapters (MarketData.app, ORATS, BYO-vendor shims)
- Calendar augmentation data pipeline (earnings/Fed/OPEX overlays)
- CLI, dev tooling, test harnesses

**Proprietary (hosted service, never released):**

- Trained HMM weights and regime classifiers
- Calibration datasets and stress-scenario library
- Hosted evaluation service (fast smoke + full Monte Carlo)
- Credit/billing system
- The curated universe of "known-good" rule templates
- Calibration tracking and Brier-score history across users
- Any user data or aggregated behavioral signals

**License recommendation:** Apache 2.0 or MIT for the open source components. Avoid AGPL — it will scare off integrators and you do not need the copyleft protection because your moat is the trained model, not the code. Consider BSL (Business Source License) only if you see a specific risk of a cloud provider repackaging your backtest engine as a competing SaaS — but do not default to it.

**The moat question:** "What stops someone from forking the open source, training their own HMM, and competing?" The honest answer: data quality, calibration rigor, the stress-scenario library, the ongoing tuning process, and the trust signal of a public calibration track record. The math is not the moat. The curated model and the evaluation pipeline are.

---

## Status Overview

This is a net-new roadmap. Everything is Not Started. Phase 0 is a kill-switch milestone — if it fails, the rest of the roadmap is invalid.

| Phase | Timeframe | Status | Risk |
|---|---|---|---|
| Phase 0 — HMM feasibility spike | Now (Apr–May 2026) | Not Started | Critical |
| Phase 1 — Open source MVP | Next (Jun–Sep 2026) | Not Started | Medium |
| Phase 2 — Proprietary eval service | Next (Oct–Dec 2026) | Not Started | Medium |
| Phase 3 — Conversational product | Later (Q1 2027) | Not Started | Low |
| Phase 4 — Distribution + directory | Later (Q2 2027) | Not Started | Low |
| Phase 5+ — Community + expansion | Later (H2 2027) | Not Started | Low |

---

## Now — Phase 0: HMM Feasibility Spike (4–6 weeks, Apr–May 2026)

**Goal:** Prove the distributional evaluation is trustworthy enough to change user behavior, especially in the tail. Nothing else matters until this works.

**Why this is Phase 0 and not Phase 1:** Every decision downstream — product positioning, open source structure, go-to-market, monetization — depends on whether the HMM-based eval produces honest tail estimates. If it does not, you are better off knowing in six weeks than in six months.

**This phase is closed source.** You are building a research prototype, not a product. Do not polish. Do not open-source yet.

**Work items:**

- Fit a 3–4 regime HMM on SPY + VIX (+ optionally MOVE, credit spreads) over 10–15 years
- Implement Monte Carlo path generation conditioned on inferred regime
- Implement one reference strategy end-to-end: cash-secured puts on SPY, 0.35 delta, 45 DTE, roll on test at 21 DTE
- Generate distributional outcomes (CAGR, max drawdown, CVaR, prob-of-ruin)
- Back-check against Feb 2018, Mar 2020, and 2022: did the model's tail estimates *warn* a user at plausible probabilities *before* those events?
- Compare distributional results to naive historical backtest of the same strategy
- Write a one-page honest assessment: does this work, partially work, or not work?

**Pass/fail criteria:**

- Pass: HMM assigns meaningful (>3%) probability to crisis transitions in the 30-day window preceding Feb 2018 and Mar 2020. Tail estimates are within 2x of realized tail outcomes. Model is interpretable enough to narrate in plain English.
- Fail: Crisis transitions are assigned <1% probability in lookback. Tail estimates collapse or explode. Regime assignments look like noise. → Stop, reconsider, do not proceed to Phase 1 until you have a modeling approach that passes.

**Deliverable:** Internal technical memo with pass/fail verdict. No code release. No user-facing anything.

**Owner:** Founder (this cannot be delegated — the founder needs to internalize the limits of the model firsthand).

---

## Next — Phase 1: Open Source MVP (Jun–Sep 2026)

**Goal:** Ship a credible open source premium-selling backtest toolkit that builds community and serves as the onramp to the proprietary eval service.

**Only launch this phase if Phase 0 passes.**

**What ships open source:**

- MCP server with rule authoring, validation, and historical backtest endpoints
- Rule DSL that supports the core premium-selling playbook (covered calls, CSPs, credit spreads, rolls, delta/DTE/theta filters)
- Historical backtest engine (daily-close granularity for v1, intraday later)
- Calendar augmentation pipeline (earnings, Fed, OPEX, dividends)
- Basic position-lifecycle simulator with Greeks
- CLI for running backtests locally
- 5–10 worked example strategies in the repo

**What is deliberately absent (reserved for Phase 2):**

- HMM-based distributional evaluation
- Monte Carlo path simulation
- Stress scenario library
- Regime-aware anything

**Community work items:**

- Launch on GitHub with thorough README, contribution guide, and examples
- Post to r/thetagang, r/options, r/quant, Hacker News
- Cross-post worked examples to Twitter/X options community
- Respond to every issue and PR for the first 90 days (set expectations early)
- Weekly build-in-public updates

**Success metrics:**

- 500+ GitHub stars in 90 days (signal, not a goal in itself)
- 20+ external contributors in 90 days
- 5+ cited use cases from real premium sellers
- At least 3 pieces of substantive community feedback that reshape the roadmap

**Risks:**

- Open source without a community is just a public folder. Budget serious founder time for community engagement, not just code.
- The Option Alpha / Tastytrade crowd is skeptical of new tools. Credibility comes from worked examples and honest tradeoff discussion, not marketing copy.

**Dependencies:**

- Data vendor commitments (MarketData.app, ORATS) for reference pipelines
- License decision locked (recommend Apache 2.0, decide by start of phase)

---

## Next — Phase 2: Proprietary Evaluation Service (Oct–Dec 2026)

**Goal:** Launch the hosted distributional eval as a paid service consumed by the open source MCP. Credit-based billing. This is where the business starts.

**What ships:**

- Hosted evaluation service with two tiers:
  - **Smoke eval** (fast, ~500 paths, daily granularity, single regime) — used during conversational iteration
  - **Full eval** (10k paths, intraday, full stress scenarios, calibrated HMM) — used for commit-grade evaluation
- Website with auth, billing, credit purchase, and visualization dashboard
- Payoff diagrams, regime probability distributions, portfolio Greek heatmaps, calibration curves
- API keys that plug into the open source MCP (users install the OSS plugin, paste an API key, and now the `full_eval` tool actually works)
- Free tier: enough credits for one real full eval per month, no card required
- Paid tiers: credit bundles, with power-user subscription for heavy users

**Open source stays ahead on:** historical backtests, rule authoring, strategy simulation, CLI. Proprietary wins on: regime-aware eval, tail narration, visualizations.

**Success metrics:**

- 100 paying users by end of Q4 2026
- 40% of free-tier users convert to at least one paid credit purchase
- Median time-from-signup-to-first-full-eval under 15 minutes

**Risks:**

- Pricing is hard to get right. Budget for 2–3 pricing iterations in the first 90 days.
- Visualization quality is a make-or-break feature in this domain. Under-investing here kills the product no matter how good the math is.
- Free tier economics: full evals are genuinely expensive compute. Model this carefully before setting the free tier boundary.

**Dependencies:**

- Phase 0 model must still be validating correctly at this point; re-run the validation on updated data before launch
- Legal review of disclaimers and positioning (research tool, not investment advice)

---

## Later — Phase 3: Conversational Product (Q1 2027)

**Goal:** Turn the rule-authoring experience from CLI + form-fills into a first-class conversational workflow, and make the agent the primary interface.

**What ships:**

- Polished conversational rule authoring via the skill layer
- Rule version control: branches, diffs, history, revert
- Continuous rule tuning agent (check-ins on strategy drift, roll pattern analysis, tighten/loosen recommendations)
- Calibration tracking across a user's own recommendations (personal Brier score)
- Portfolio-level risk narration in plain English

**Why this is Phase 3 and not earlier:** The conversational layer is the charming onramp but it is not where the defensibility lives. Ship the hard-to-copy parts first. The conversation is great marketing for a great backend, but great marketing for a mediocre backend is a short-lived product.

**Success metrics:**

- 60% of active users engage with conversational rule authoring at least weekly
- Measurable improvement in user retention (target: +20% vs. Phase 2 baseline)
- First public calibration track record with ≥200 resolved recommendations

---

## Later — Phase 4: Distribution and Directory (Q2 2027)

**Goal:** Expand distribution through the Claude plugin directory and broader community channels. Make the plugin a secondary surface on top of the standalone product, not a replacement for it.

**What ships:**

- Polished plugin submission to Anthropic's directory (MCP + skill + slash commands bundled)
- Financial-tools disclaimer and content policy compliance work
- "Research and analysis" positioning (not "trade recommendations") reflected everywhere
- Referral / affiliate hooks
- Content marketing push: worked examples, blog posts on HMM calibration, YouTube walkthroughs

**Explicit non-goal:** Do not make the plugin directory the primary distribution channel. Treat it as a growth channel that brings users into the standalone product.

**Risks:**

- Anthropic rejection or delayed approval. Mitigation: the web product works fine without directory listing.
- Power-law directory dynamics — being listed is not the same as being found. Mitigation: do not plan on directory traffic as a growth number.

---

## Later — Phase 5 and Beyond (H2 2027)

Directional bets, not commitments. Revisit when Phase 3 is solid.

- **Community rule library:** Curated, open-source collection of battle-tested rule sets contributed by the community. Each rule ships with its full-eval results and calibration history. Potential flywheel.
- **Intraday rolling logic:** Upgrade the backtest engine from daily-close to minute-bar granularity for rolling rules where timing matters.
- **Multi-asset expansion:** Extend beyond equity options to futures options (/ES, /CL). Bigger market, different user, real work.
- **Team / advisor features:** Multiple accounts under one org, shared rule libraries, approval workflows. Entry into the RIA market, which is regulated territory — do not pursue without legal counsel.
- **Mobile:** Read-only first (view portfolio Greeks, get risk alerts), write later if at all.
- **Live brokerage integration:** The big scary one. Enables one-click execution from recommendations. Regulatory path gets much heavier. Do not touch until everything else is stable.

---

## Capacity and Dependency Notes

**Capacity assumption:** Solo founder + 1 engineer through Phase 2. Add a second engineer and a designer for Phase 3. This roadmap is paced for that team size and is already ambitious for it.

**Critical dependencies:**

- Phase 0 passing is a hard gate on everything else. If it fails, restart with a different modeling approach or shelve the idea.
- Data vendor reliability (MarketData.app, ORATS) — any vendor change is multi-week rework.
- Legal review before Phase 2 launch for disclaimers and positioning.
- Community traction in Phase 1 is the softest dependency but the one most likely to be underinvested.

**What is deliberately not on the roadmap:**

- Autopilot / auto-execution of trades (regulatory minefield, different product)
- Stock picking / alpha generation (not what LLMs are good at, not the value proposition)
- Options education content library (Tastytrade owns this, do not compete)
- Social / copy-trading features (scope creep, different product)

---

## Riskiest Assumption

That the HMM-based distributional eval produces tail estimates trustworthy enough to justify the entire product positioning. If Phase 0 fails, this roadmap does not recover by pivoting — it recovers by going back to modeling until a different approach works. Everything else is derivative.

---

## Suggested Next Step

Begin Phase 0 immediately. Block four to six weeks of uninterrupted founder time for the HMM feasibility spike. Do not build product, do not design logos, do not talk to investors, do not pick a name. Fit the model, run the validation, and write the honest memo. Everything downstream depends on it.
