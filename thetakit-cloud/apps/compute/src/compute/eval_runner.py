"""Top-level eval runners — smoke and full.

Both runners take the same EvalInput shape and produce the same EvalResult
shape so the full eval is strictly a superset in terms of data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from math import log
from typing import Any

import numpy as np

from compute.aggregator import DistributionalStats, PathOutcome, aggregate
from compute.hmm.model import StudentTHMM
from compute.path_simulator import PathSimulator, SimulatedPath
from compute.strategy_runner import run_strategy_on_path
from compute.stress import STRESS_SCENARIOS, stress_paths
from thetakit.dsl import load_strategy


@dataclass(frozen=True, slots=True)
class EvalInput:
    rule_yaml: str
    universe: list[str]
    initial_prices: dict[str, float]
    start: str  # ISO
    end: str  # ISO
    seed: int = 42


@dataclass(frozen=True, slots=True)
class EvalResult:
    eval_type: str  # "smoke" | "full"
    n_paths: int
    stats: DistributionalStats
    sample_paths: list[dict[str, Any]] = field(default_factory=list)
    model_version: str = "minimal-student-t-v0"
    seed: int = 42


def _fit_hmm_on_synthetic(seed: int) -> StudentTHMM:
    """Fit the HMM on synthetic market returns. In production this would load
    a pre-fitted artifact from S3; here we fit on-demand so the service is
    self-contained."""
    rng = np.random.default_rng(seed)
    # Two-regime GBM-ish returns: long calm stretches interrupted by short vol bursts
    returns = []
    in_crisis = False
    days_in_regime = 0
    for _ in range(2500):
        if not in_crisis:
            r = rng.normal(0.0004, 0.01)
            if rng.random() < 0.002:
                in_crisis = True
                days_in_regime = 0
        else:
            r = rng.normal(-0.001, 0.03)
            days_in_regime += 1
            if days_in_regime > 15 and rng.random() < 0.1:
                in_crisis = False
        returns.append(r)
    hmm = StudentTHMM(n_regimes=3, max_iter=20, random_state=seed)
    hmm.fit(np.asarray(returns))
    return hmm


def run_smoke_eval(inp: EvalInput) -> EvalResult:
    """Smoke eval: ~500 paths, fixed regime mix (no transitions), daily bars.

    Fixed regime mix here means: we sample the initial regime from the
    fitted prior and hold the transition matrix flat-ish (forced-sticky)
    so paths don't flip regimes mid-simulation. This keeps latency low.
    """
    strategy = load_strategy(inp.rule_yaml)
    start = date.fromisoformat(inp.start)
    end = date.fromisoformat(inp.end)
    n_days = max((end - start).days, 20)

    hmm = _fit_hmm_on_synthetic(inp.seed)
    # Flatten transitions for smoke (force sticky regimes)
    if hmm.params is not None:
        k = hmm.params.n_regimes
        sticky = np.eye(k) * 0.99 + (1 - np.eye(k)) * (0.01 / max(k - 1, 1))
        hmm.params = hmm.params.__class__(
            n_regimes=k,
            initial_probs=hmm.params.initial_probs,
            transition_matrix=sticky,
            means=hmm.params.means,
            scales=hmm.params.scales,
            dofs=hmm.params.dofs,
        )

    sim = PathSimulator(
        hmm=hmm,
        initial_prices=inp.initial_prices,
        start=start,
        n_days=n_days,
        seed=inp.seed,
    )
    paths = sim.sample(n_paths=500)
    outcomes = [run_strategy_on_path(strategy, p) for p in paths]
    stats = aggregate(outcomes)
    return EvalResult(
        eval_type="smoke",
        n_paths=len(outcomes),
        stats=stats,
        sample_paths=[_serialize_path(p) for p in paths[:5]],
        seed=inp.seed,
    )


def run_full_eval(inp: EvalInput, *, n_paths: int = 10_000) -> EvalResult:
    """Full eval: 10k paths with full regime transitions + stress scenarios injected."""
    strategy = load_strategy(inp.rule_yaml)
    start = date.fromisoformat(inp.start)
    end = date.fromisoformat(inp.end)
    n_days = max((end - start).days, 20)

    hmm = _fit_hmm_on_synthetic(inp.seed)
    sim = PathSimulator(
        hmm=hmm,
        initial_prices=inp.initial_prices,
        start=start,
        n_days=n_days,
        seed=inp.seed,
    )
    paths = sim.sample(n_paths=n_paths)
    outcomes: list[PathOutcome] = [run_strategy_on_path(strategy, p) for p in paths]

    # Inject stress scenarios
    stress_path_list = stress_paths(inp.initial_prices)
    for scenario, prices_by_sym in zip(STRESS_SCENARIOS, stress_path_list):
        # Build a SimulatedPath from the stress data
        length = max(len(v) for v in prices_by_sym.values())
        dates = _weekday_dates(start, length)
        path = SimulatedPath(
            dates=dates,
            prices=prices_by_sym,
            regimes=[2] * length,  # all crisis regime
            path_id=10_000 + hash(scenario.name) % 10_000,
        )
        outcome = run_strategy_on_path(strategy, path)
        outcomes.append(
            PathOutcome(
                path_id=outcome.path_id,
                total_return_pct=outcome.total_return_pct,
                max_drawdown_pct=outcome.max_drawdown_pct,
                cagr_pct=outcome.cagr_pct,
                trades=outcome.trades,
                win_rate=outcome.win_rate,
                dominant_regime=2,
                stress_scenario=scenario.name,
            )
        )

    stats = aggregate(outcomes)
    return EvalResult(
        eval_type="full",
        n_paths=len(outcomes),
        stats=stats,
        sample_paths=[_serialize_path(p) for p in paths[:10]],
        seed=inp.seed,
    )


def _serialize_path(p: SimulatedPath) -> dict[str, Any]:
    return {
        "path_id": p.path_id,
        "dates": p.dates[: len(p.regimes)],
        "regimes": p.regimes,
        "prices": {sym: [round(v, 4) for v in vals] for sym, vals in p.prices.items()},
    }


def _weekday_dates(start: date, n: int) -> list[str]:
    from datetime import timedelta

    out: list[str] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out
