"""Aggregate per-path outcomes into distributional statistics."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True, slots=True)
class PathOutcome:
    """One path's strategy result."""

    path_id: int
    total_return_pct: float
    max_drawdown_pct: float
    cagr_pct: float
    trades: int
    win_rate: float
    dominant_regime: int
    stress_scenario: str | None = None


@dataclass(frozen=True, slots=True)
class DistributionalStats:
    n_paths: int
    # Return distribution
    return_median: float
    return_p05: float
    return_p25: float
    return_p75: float
    return_p95: float
    return_mean: float
    return_std: float
    # Drawdown distribution
    drawdown_median: float
    drawdown_p95: float  # worst 5%
    drawdown_p99: float  # worst 1%
    # Tail risk
    cvar_05: float  # mean of worst 5%
    cvar_01: float  # mean of worst 1%
    prob_ruin_25pct: float  # fraction of paths with drawdown worse than -25%
    prob_ruin_50pct: float  # fraction with drawdown worse than -50%
    # Central tendency
    win_rate_mean: float
    trades_median: float
    # Regime breakdown: regime_id -> mean return on paths dominated by that regime
    return_by_regime: dict[int, float]
    # Stress scenarios
    stress_results: dict[str, float]  # scenario name -> return


def aggregate(outcomes: list[PathOutcome]) -> DistributionalStats:
    if not outcomes:
        return DistributionalStats(
            n_paths=0,
            return_median=0, return_p05=0, return_p25=0, return_p75=0, return_p95=0,
            return_mean=0, return_std=0,
            drawdown_median=0, drawdown_p95=0, drawdown_p99=0,
            cvar_05=0, cvar_01=0, prob_ruin_25pct=0, prob_ruin_50pct=0,
            win_rate_mean=0, trades_median=0,
            return_by_regime={}, stress_results={},
        )

    # Exclude stress paths from the Monte Carlo distribution — they're
    # categorically different and reported separately.
    mc_outcomes = [o for o in outcomes if o.stress_scenario is None]
    if not mc_outcomes:
        mc_outcomes = outcomes  # fallback

    returns = np.array([o.total_return_pct for o in mc_outcomes])
    drawdowns = np.array([o.max_drawdown_pct for o in mc_outcomes])

    sorted_returns = np.sort(returns)
    worst_5pct_cutoff = max(1, int(np.ceil(0.05 * len(sorted_returns))))
    worst_1pct_cutoff = max(1, int(np.ceil(0.01 * len(sorted_returns))))

    # Regime breakdown
    regimes = np.array([o.dominant_regime for o in mc_outcomes])
    return_by_regime: dict[int, float] = {}
    for r in np.unique(regimes):
        rmask = regimes == r
        return_by_regime[int(r)] = float(returns[rmask].mean())

    # Stress
    stress_results: dict[str, float] = {}
    for o in outcomes:
        if o.stress_scenario is not None:
            stress_results[o.stress_scenario] = o.total_return_pct

    return DistributionalStats(
        n_paths=len(outcomes),
        return_median=float(np.median(returns)),
        return_p05=float(np.percentile(returns, 5)),
        return_p25=float(np.percentile(returns, 25)),
        return_p75=float(np.percentile(returns, 75)),
        return_p95=float(np.percentile(returns, 95)),
        return_mean=float(returns.mean()),
        return_std=float(returns.std(ddof=1)) if len(returns) > 1 else 0.0,
        drawdown_median=float(np.median(drawdowns)),
        drawdown_p95=float(np.percentile(drawdowns, 5)),  # 5th pctile = worst 5%
        drawdown_p99=float(np.percentile(drawdowns, 1)),
        cvar_05=float(sorted_returns[:worst_5pct_cutoff].mean()),
        cvar_01=float(sorted_returns[:worst_1pct_cutoff].mean()),
        prob_ruin_25pct=float((drawdowns <= -25.0).mean()),
        prob_ruin_50pct=float((drawdowns <= -50.0).mean()),
        win_rate_mean=float(np.array([o.win_rate for o in mc_outcomes]).mean()),
        trades_median=float(np.median([o.trades for o in mc_outcomes])),
        return_by_regime=return_by_regime,
        stress_results=stress_results,
    )
