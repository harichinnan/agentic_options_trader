# Phase 0 — HMM Feasibility & Validation Protocol

**Phase:** 0 of 5 (per roadmap)
**Duration:** 4–6 weeks
**Status:** Research spike, closed source
**Audience:** Founder (non-delegable)
**Deliverable:** A one-page honest memo with a binary pass/fail verdict

> This is the gate document for the entire product. If the protocol below does not produce a passing verdict, the roadmap does not recover by pivoting the product — it recovers by going back to modeling until a different approach works. Do not start Phase 1 until this phase produces a pass. Do not let excitement, sunk cost, or "almost passing" override the verdict.

---

## 1. Purpose

Prove — or disprove — that a Hidden Markov Model over liquid market features can produce distributional backtest results **honest enough to change real user behavior**, specifically in the tail where premium-selling strategies actually blow up. This is not an engineering question about whether the code runs. It is a scientific question about whether the model is trustworthy enough to base a business on.

**The non-obvious framing you must hold in your head throughout:** the model failing loudly in this phase is a *good* outcome. It saves you months of wasted product work. The bad outcome is a model that *looks* like it passes because you were rooting for it, and then fails in production after users have trusted it with real money.

---

## 2. Core Question

Can a fitted HMM, at any plausible moment from 2012 through 2023, have produced **advance warning** of the major regime shifts that would have mattered to a premium seller — Feb 2018, Q4 2018, Mar 2020, 2022 bear, Aug 2015, Jan 2016, and the Q1 2023 banking scare — with (a) enough probability mass to justify action and (b) few enough false positives to avoid being dismissed as noise?

Everything below is a formalization of that single question.

---

## 3. Scope and Non-Scope

**In scope for Phase 0:**

- Fitting one or more HMM variants on US equity and vol index data, 2005–2024
- A specific battery of validation tests, all listed in Section 7
- Running one reference premium-selling strategy (SPY cash-secured puts, 0.35 delta, 45 DTE, 21 DTE close) through Monte Carlo over the fitted model
- Comparison against a naive historical backtest baseline
- A written verdict memo

**Explicitly out of scope for Phase 0:**

- Product UI, branding, naming
- The rule DSL, the backtest engine productization, the MCP server — that is Phase 1
- Fitting models to multiple underlyings (SPY + VIX + macro is sufficient for the go/no-go)
- Per-user calibration, online learning, or adaptive retraining
- Pretty visualizations (rough matplotlib is fine)
- Software engineering polish — this is a research spike, not a library
- Productionization of the code — expect to rewrite it in Phase 2

---

## 4. Data Requirements

### 4.1 Features to source

At minimum:

- **SPY daily returns** (log returns), 2005-01-01 through 2024-12-31. Adjusted for dividends/splits. Yahoo Finance is adequate for this phase; do not pay for a premium vendor yet.
- **VIX daily close**, same window. Cboe or Yahoo.
- **VIX term structure slope**: VIX3M / VIX or VX1 / VX2. Computable from Cboe's daily files.
- **MOVE index** (bond vol), same window. Licensed but free for research on some sources.
- **Realized volatility**: rolling 21-day std of SPY log returns. Computed, not sourced.

Optional stretch features if time permits and the baseline model is borderline:

- IG credit spread index (HYG - LQD yield differential works as a cheap proxy; Fred has cleaner series)
- Dollar index (DXY) for macro regime context
- Yield curve slope (10Y - 2Y)

### 4.2 Train / test splits

Use **two splits, not one**, and run the validation on both to catch overfitting:

- **Split A — expanding window:** train on 2005-01-01 through 2019-12-31, test on 2020-01-01 through 2024-12-31. This is the hard test because 2020 is a stress event the model has not seen.
- **Split B — rolling leave-one-event-out:** for each major stress event in the full history (Aug 2015, Jan 2016, Feb 2018, Q4 2018, Mar 2020, Jan 2022, Mar 2023), fit the model on all data *except* a 60-day window around that event, then ask: does the fitted model assign meaningful probability to a crisis transition in the held-out window?

If the model only passes on Split A, it may be overfitting to the specific shape of 2020. If it only passes on Split B, it may be memorizing the general shape of crises without being able to forecast in the wild. You need both.

### 4.3 Data hygiene

- No look-ahead. Any feature computed with a rolling window must use only past data as of each date.
- Normalize features with training-window statistics only, applied to test data without re-fitting.
- Handle the 2008 crisis in the training data deliberately. It is the cleanest example of a true regime shift in the record; treat it as reference truth, not as an outlier to be clipped.
- Do not winsorize returns. Fat tails are the signal, not the noise.

---

## 5. Model Specifications to Try

Fit these **in order**. Stop at the first that passes all validation tests. Escalate to the next only if the previous fails.

### 5.1 Baseline — Gaussian HMM

- 3-regime and 4-regime variants
- `hmmlearn.GaussianHMM` with full covariance matrices
- EM fitting with 20 random restarts, keep the best log-likelihood
- Feature set: SPY returns, VIX log level, VIX term slope (3 features)

**Purpose:** establish the floor. I expect this to fail the tail test — Gaussian innovations systematically underweight fat tails — but it gives you a reference baseline and lets you debug the validation harness before moving to harder models.

**If this passes somehow:** be deeply suspicious. Re-check the validation. Gaussian HMMs should not pass this bar on this asset class. If it does, there is probably a bug.

### 5.2 Student-t HMM

- Same 3- and 4-regime variants
- Custom implementation: EM with Student-t emissions per regime, degrees-of-freedom as a per-regime parameter
- Or: use `stan` / `numpyro` for a Bayesian version if EM convergence is shaky
- Feature set same as baseline, plus realized vol as a fourth feature

**Purpose:** this is the most likely candidate to pass. Student-t innovations are the cheapest principled fix for fat tails, and the literature on regime-switching models for equities has been using them for 20+ years for a reason. Your goal is to get a passing verdict on this model if possible.

**Implementation notes:**

- `hmmlearn` does not ship with a Student-t emission out of the box. You can either subclass `BaseHMM` and implement your own emission, or use `pomegranate` which has more flexible distributions, or write it from scratch. Writing from scratch in ~300 lines is not unreasonable for a research prototype.
- Degrees of freedom per regime is the crucial hyperparameter. Lower df = fatter tails. Crisis regime df should probably end up in the 3–6 range; calm regime df should be 10+.
- EM with Student-t can be fragile. Use fixed initialization from k-means on the feature space, not random.

### 5.3 HMM with exogenous features (Markov-switching regression)

- If 5.2 is borderline: extend the emission to a regression on macro features (credit spreads, yield curve) rather than a pure mixture
- This is the `statsmodels.tsa.regime_switching.MarkovRegression` territory
- More parameters, more overfitting risk, but also more power to distinguish "normal quiet" from "quiet before a storm"

**Purpose:** improve on 5.2 if the tail test is failing not because of distributional shape but because calm periods immediately preceding crises look identical to ordinary calm periods.

### 5.4 Markov-switching GARCH (stretch)

- If 5.2 and 5.3 both fail: the issue is probably that return volatility is itself regime-dependent *within* a regime, and a static-vol HMM cannot capture vol clustering inside a regime
- `arch` library supports regime-switching GARCH variants
- This is substantially harder to fit and interpret

**Purpose:** final escalation. If this fails too, the verdict is **FAIL** and you need to reconsider the modeling approach entirely — possibly abandoning HMM for something like a deep state-space model, which is a very different project.

---

## 6. Reference Strategy for Tail Tests

A single strategy, held constant across all model variants and tests, so the test is about the model, not about strategy choices:

- **Underlying:** SPY
- **Strategy:** cash-secured puts
- **Delta target:** 0.35
- **DTE target at open:** 45
- **Sizing:** fixed, one contract per $20k of simulated capital (deliberately under-sized to keep the test about tail behavior, not concentration risk)
- **Rolls:** none — if the short strike is tested, close at mid and move on (keeps the test simple)
- **Exits:** close at 50% max profit or at 21 DTE, whichever first
- **Capital:** $100k simulated
- **No earnings/event filters** — deliberately crude so the tail exposure is clean

You will need a simplified Black-Scholes-based options pricer for the simulation. `py_vollib_vectorized` is fine. No American exercise logic needed for this phase — it is SPY, European approximation is close enough for a go/no-go test.

This reference strategy is **not** intended to represent a good strategy. It is intended to have a clean, predictable tail profile so we can check whether the model's distributional output matches what historical stress periods actually did to a naked premium seller.

---

## 7. Validation Tests (The Heart of Phase 0)

Each test below has a pass criterion. **All must pass** for the phase to pass. No partial credit.

### 7.1 Interpretability Test

Can you describe each regime in plain English, based only on the fitted parameters and the historical periods where each regime has highest posterior probability? "Regime 1 is low-vol bull market. Regime 2 is choppy sideways with elevated uncertainty. Regime 3 is sustained high vol with directional downside. Regime 4 is crisis with vol spike and cross-asset contagion." If you cannot do this exercise with a straight face, the model has learned noise, not regimes.

**Pass:** each regime has a coherent, distinct verbal description supported by the historical periods that score highest on it.

**Fail modes to watch for:**

- Two regimes that look identical ("low vol" and "slightly lower vol") — collapse them, use fewer regimes
- A regime that only fires for 3 days ever — overfitting, discard the model
- A regime that fires randomly with no temporal coherence — the model has not found structure

### 7.2 Crisis Flagging Test (The Main Event)

For each of these known stress events:

| Event | Start date of major move |
|---|---|
| Aug 2015 flash crash | 2015-08-24 |
| Jan 2016 sell-off | 2016-01-15 |
| Feb 2018 Volmageddon | 2018-02-05 |
| Q4 2018 sell-off | 2018-10-10 |
| Mar 2020 COVID crash | 2020-03-09 |
| Jan 2022 bear start | 2022-01-18 |
| Mar 2023 SVB / banking scare | 2023-03-10 |

In the 30 trading days *before* the start date, what probability did the model assign to being in (or imminently transitioning to) a crisis regime? "Imminent" means: probability of the next 10-day period containing a crisis regime, computed via simulation from the current posterior.

**Pass criterion:** for at least **5 of 7** events, the model's crisis probability exceeds 3% at some point in the 30-day lookback, and exceeds 8% at some point in the 10-day lookback.

**Hard fail:** if the model's crisis probability never exceeds 1% before *any* of these events, it is hopeless. No amount of parameter tuning will fix it.

**Honest note:** 3% is not a lot. 3% is "something you should probably pay attention to." You are not trying to predict the exact date of crisis — that is impossible. You are trying to produce a *meaningful probability shift* that would justify a user tightening their risk parameters or taking down exposure.

### 7.3 False Positive Control

Across the full history (excluding the 60-day windows around known events), how often does the model emit a crisis probability above 8% in any 10-day window that is *not* followed by a crisis within the next 30 days?

**Pass criterion:** false positive rate below **25%**. That is: when the model says "crisis imminent," it is wrong at most a quarter of the time on the lookback.

**Calibration matters here.** A model that flags a crisis every other week is useless even if it catches every real one. Users will stop listening.

### 7.4 Tail Magnitude Test

Run the reference strategy from Section 6 over the full history using two methods:

1. **Historical backtest:** one realized path, 2005–2024.
2. **Model-based distributional backtest:** fit the model on data up to date T, simulate 5,000 forward paths conditional on the fitted posterior at T, run the strategy on each, record the 5th percentile drawdown. Roll T forward monthly.

Compare the model-based 5th percentile drawdown predictions to the actual realized worst-month drawdowns in the subsequent period.

**Pass criterion:** model 5th percentile drawdowns are within a factor of **2** of realized worst-month outcomes across the historical rolling window. Specifically: for at least 80% of rolling windows, `0.5 ≤ realized_worst / model_5th_pct ≤ 2.0`.

**Fail mode to watch for:** model 5th percentile is suspiciously *worse* than historical. This is actually acceptable for the safety case — overpredicting tail risk is safer than underpredicting it — but only by a factor of 2 at most. A model that cries wolf at 10x historical tails is useless.

### 7.5 Stability Test

Refit the model 10 times with different random seeds on the same training window. For each pair of fits, compute the regime assignment agreement on the test window (fraction of days where both fits agree on the most-likely regime, after matching regime labels via Hungarian algorithm).

**Pass criterion:** median agreement above **85%**, minimum above **75%** across all pairs.

**Fail mode:** low stability means the model is finding structure but the structure is random-seed-dependent. This is a disaster for product trust because users will see different recommendations on different fits.

### 7.6 Out-of-Sample Calibration

Take the Split A model (trained on 2005–2019). For every 10-day window in 2020–2024, compute the model's probability that the forward 10 days contains a crisis regime. Bin these probabilities into deciles. Within each decile, compute the realized fraction of windows that actually contained a crisis regime.

**Pass criterion:** the realized frequencies track the predicted probabilities within **±10 percentage points** across all deciles. If the model says "30% probability," the realized frequency should be between 20% and 40%.

This is the most important test if you ever want to show users a public calibration track record in Phase 3. Get it right now or you will not be able to make calibration claims later.

### 7.7 Honesty Sanity Check (Do This Last, It Matters)

Take a deliberately dangerous version of the reference strategy: 0.50 delta naked short puts on QQQ, 7 DTE, no exits, no stops, no size limits. Run it through the model.

**Pass criterion:** the model's 5th percentile P&L outcome is **catastrophically negative**. The median outcome is worse than buy-hold. The tail scatter plot should look obviously bad.

If the model makes this strategy look reasonable, the model is broken, and nothing downstream matters. Any validation harness that passes a known-dangerous strategy is a harness that does not actually catch danger.

---

## 8. Comparison Baseline

Alongside each HMM variant, run the same validation tests on a **naive baseline**: a historical bootstrap that samples 10-day windows uniformly from the training data. This is what a "just run a historical backtest" user gets today.

The HMM must **beat the naive baseline** on all of 7.2, 7.3, 7.4, and 7.6. If it does not, the HMM is not adding value over what a user could already do with a spreadsheet. Shipping Phase 2 in that state would be indefensible.

---

## 9. Workplan

A 6-week plan with weekly check-ins. Do not go past 6 weeks without an explicit reset conversation with yourself. Phase 0 is time-boxed for a reason.

### Week 1 — Data and harness

- Source all required data into a single Parquet file
- Build the validation harness for Sections 7.1–7.7, using a mock model that returns canned outputs. The harness must run end-to-end on the mock before you fit any real model.
- Build the reference strategy simulator. Verify it produces sensible numbers on known historical periods.

### Week 2 — Baseline Gaussian HMM

- Fit 3-regime and 4-regime Gaussian HMMs on Split A
- Run all validation tests
- Document results even if (especially if) it fails — this is the reference point for the Student-t work

### Week 3 — Student-t HMM

- Implement or adapt Student-t emissions
- Fit and validate, same protocol
- If close to passing, spend half the week on hyperparameter tuning (degrees of freedom, regime count, feature set)

### Week 4 — Decision point and iteration

- If Student-t HMM passed in Week 3: skip to Week 5
- If it is borderline: tune further, try Section 5.3 (exogenous features)
- If it is far from passing: consider Section 5.4 (MS-GARCH) or reconsider the approach
- **Hard decision point at end of Week 4:** if no model is within 2 of the pass bar on the main tests, write the failing memo and stop

### Week 5 — Robustness

- Re-run the winning model on Split B (leave-one-event-out)
- Run Section 7.5 stability test
- Run Section 7.6 calibration test
- Re-run Section 7.7 honesty sanity check

### Week 6 — Memo and verdict

- Write the one-page memo (template in Section 11)
- Include all pass/fail results in an appendix
- Include known limitations and what you did not have time to test
- Deliver verdict

---

## 10. Outcomes and What Each Means

### 10.1 PASS

All tests in Section 7 passed, HMM beat the baseline, honesty sanity check caught the dangerous strategy. Phase 1 is unlocked. Archive the Phase 0 code as `research/phase-0-hmm-spike` and start Phase 1 immediately.

### 10.2 PARTIAL PASS

Some tests passed, some failed, but the failures are in tests that could plausibly be fixed with 1–2 more weeks of modeling work. Extend Phase 0 by up to 2 weeks. If it is still not passing, downgrade to FAIL. Do not extend twice.

Common partial-pass patterns:

- **Interpretability and calibration passed, but tail magnitudes are off.** Usually a distributional-shape issue. Try harder innovation distributions, fit per-regime skew.
- **Crisis flagging passed for some events, not others.** Often the missing events have different character — for example, the SVB scare was fast and narrow. Consider adding credit or bank-specific features.
- **Stability failed but everything else passed.** Try more EM restarts, use k-means init, or reduce regime count.

### 10.3 FAIL

Fundamental problems: the model cannot flag crises ahead of time, tail estimates are off by more than 2x, or the model fails the honesty sanity check. **Do not proceed to Phase 1.** Write the memo. Consider one of:

- **Shelve the product idea.** Painful but honest. Better to know now.
- **Pivot the product.** Without trustworthy distributional eval, the defensibility argument collapses. A non-HMM version of the product would be "just a better historical backtester," which is a less interesting business but could still work if you are okay with smaller scope. If you go this route, rewrite the roadmap — the competitive story is very different.
- **Restart modeling with a fundamentally different approach.** Deep state-space models, change-point detection, or regime-free tail modeling (extreme value theory). These are bigger projects with their own failure modes.

Do not restart Phase 0 without a clear hypothesis for what will be different. "I'll try harder" is not a hypothesis.

---

## 11. Verdict Memo Template

Write this at end of Week 6 regardless of outcome.

```
# Phase 0 HMM Validation Memo

Date: [date]
Verdict: PASS / PARTIAL PASS / FAIL

## Summary
One paragraph. What was tested, what the verdict is, what it means for the roadmap.

## Model
Final model: [Gaussian HMM 3-regime / Student-t HMM 4-regime / ...]
Features: [list]
Training window: [dates]
Fitting method: [EM with restarts / Bayesian / ...]

## Test Results

| Test | Pass Criterion | Result | Status |
|---|---|---|---|
| 7.1 Interpretability | Coherent regime descriptions | [notes] | PASS/FAIL |
| 7.2 Crisis flagging | 5/7 events flagged above 3% | [x/7] | PASS/FAIL |
| 7.3 False positive | <25% FPR | [x%] | PASS/FAIL |
| 7.4 Tail magnitude | Within 2x on 80% of windows | [x%] | PASS/FAIL |
| 7.5 Stability | Median agreement >85% | [x%] | PASS/FAIL |
| 7.6 Calibration | Within 10pp across deciles | [notes] | PASS/FAIL |
| 7.7 Honesty | Dangerous strategy looks bad | [notes] | PASS/FAIL |

## Baseline Comparison
Did the HMM beat a naive historical bootstrap on tests 7.2, 7.3, 7.4, 7.6? [yes/no, with details]

## Regime Descriptions
Plain-English description of each regime the model found, with 2-3 historical periods exemplifying each.

## Known Limitations
- What you did not test
- Where you are suspicious of your own results
- What would change your verdict

## Recommendation
- If PASS: proceed to Phase 1, archive code at [path], preserve model artifact at [path]
- If PARTIAL PASS: what to try next, how long, clear criterion for FAIL
- If FAIL: which of the options in Section 10.3 to take, and why

## Appendix
- Code pointers
- Plots: regime probability over time, tail scatter, calibration curves
- Raw numbers for each test
```

---

## 12. Things to Resist

This phase is where the founder is most tempted to cut corners or see pattern in noise. A short list of things to notice in yourself and resist:

- **Rooting for the model.** You will want it to pass. Every validation test you design after seeing results is suspect. Commit to the tests in Section 7 before fitting any model.
- **Moving the bar.** "5 of 7 events" is the bar. If the model hits 4 of 7, that is a fail. Do not decide after the fact that Aug 2015 was unusual and should not count.
- **Explaining away false positives.** "The model flagged crisis in June 2019 which is wrong, but honestly if you look at it..." No. A false positive is a false positive. Count it.
- **Claiming victory on partial results.** The memo says PASS or FAIL. Partial pass is an extension, not a pass.
- **Skipping the honesty sanity check.** It is the last test and the most tempting to skip. If you only run one test in the final week, run this one.
- **Not writing the memo if it fails.** Especially write the memo if it fails. A failed spike with a clear memo is a scientific result. A failed spike with no memo is wasted time.

---

## 13. What This Phase Is Really About

You are not building a product in Phase 0. You are answering one question, honestly, in six weeks: does the core technical premise of the roadmap survive contact with reality?

If it does, the rest of the roadmap is executable. If it does not, you have saved yourself a year of work and a lot of money, and you are going to be angry and disappointed and glad you did this phase instead of shipping on hope. Both outcomes are wins compared to skipping the phase.

Go fit some models.
