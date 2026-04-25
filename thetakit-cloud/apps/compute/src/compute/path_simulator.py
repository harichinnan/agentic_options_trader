"""Monte Carlo path simulator — wraps an HMM to produce price + IV paths.

Phase 1 of Phase 2: generate daily underlying paths; IV surface dynamics
are reserved for a future iteration (constant-IV assumption here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from compute.hmm.model import StudentTHMM


@dataclass(frozen=True, slots=True)
class SimulatedPath:
    """One sampled market path."""

    dates: list[str]
    prices: dict[str, list[float]]
    regimes: list[int]
    path_id: int


@dataclass
class PathSimulator:
    hmm: StudentTHMM
    initial_prices: dict[str, float]
    start: date
    n_days: int
    iv_floor: float = 0.12
    iv_ceiling: float = 0.60
    seed: int = 42

    def sample(self, n_paths: int) -> list[SimulatedPath]:
        """Generate `n_paths` market paths via the fitted HMM."""
        rng = np.random.default_rng(self.seed)

        regimes, returns = self.hmm.sample_paths(n_paths, self.n_days, rng=rng)

        # Turn returns into prices per symbol (each symbol a beta-scaled version)
        per_symbol_beta = {
            sym: 1.0 if i == 0 else 0.95 + 0.1 * (i % 3)
            for i, sym in enumerate(self.initial_prices)
        }

        paths: list[SimulatedPath] = []
        dates = _trading_days(self.start, self.n_days)
        for p in range(n_paths):
            prices: dict[str, list[float]] = {}
            for sym, s0 in self.initial_prices.items():
                beta = per_symbol_beta[sym]
                rets = returns[p] * beta
                prices_sym = [s0]
                for r in rets:
                    prices_sym.append(prices_sym[-1] * float(np.exp(r)))
                prices[sym] = prices_sym
            paths.append(
                SimulatedPath(
                    dates=dates,
                    prices=prices,
                    regimes=[int(r) for r in regimes[p]],
                    path_id=p,
                )
            )
        return paths


def _trading_days(start: date, n_days: int) -> list[str]:
    """Approximate: Monday-Friday only. Matches the synthetic adapter."""
    out: list[str] = []
    d = start
    while len(out) < n_days + 1:  # +1 so we include the initial price day
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out
