"""Stress scenario library — historical crisis periods injected into full evals.

Each scenario is a fixed, interpretable path of daily log returns covering
a well-known market stress. Full evals always include these regardless of
the current regime mix, so tail estimates cannot quietly collapse into
recent calm.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class StressScenario:
    """A named historical stress path."""

    name: str
    description: str
    start: str  # ISO date
    # Daily SPY log returns (approximations of the realized series)
    returns: list[float]


# Approximate SPY daily returns through known crisis periods.
# These are illustrative values in the right magnitude/shape — production use
# should replace with actual historical bars from a data vendor.
def _shock_series(initial_shock: float, mean_reversion_days: int, vol_spike: float) -> list[float]:
    out = [initial_shock]
    for _ in range(mean_reversion_days):
        out.append(float(np.random.default_rng(7).normal(-0.002, vol_spike)))
    return out


STRESS_SCENARIOS: list[StressScenario] = [
    StressScenario(
        name="feb_2018_vol_spike",
        description="Feb 5, 2018 XIV collapse / vol spike. -4.1% single day, choppy follow-through.",
        start="2018-02-05",
        returns=[-0.041, 0.019, -0.026, 0.015, -0.001, -0.051, 0.014, -0.018, 0.011],
    ),
    StressScenario(
        name="q4_2018_rate_scare",
        description="Q4 2018 rate/trade-war drawdown. Slow bleed with bounces.",
        start="2018-10-03",
        returns=[
            -0.009, -0.032, -0.015, 0.006, -0.012, -0.030, 0.005, 0.002, -0.019,
            -0.025, -0.008, 0.006, 0.009, -0.021, -0.014, -0.018, 0.012,
            -0.016, 0.018, -0.026, -0.031, 0.023, -0.028, 0.015, -0.025,
        ],
    ),
    StressScenario(
        name="covid_crash_mar_2020",
        description="COVID crash Feb-Mar 2020. -30% in 22 sessions with extreme realized vol.",
        start="2020-02-24",
        returns=[
            -0.032, -0.035, -0.004, -0.044, 0.046, -0.078, 0.049, 0.046, -0.076,
            -0.030, 0.060, -0.095, -0.051, 0.092, -0.033, -0.029, -0.041, 0.012,
            0.041, 0.085, 0.024, -0.020,
        ],
    ),
    StressScenario(
        name="2022_bear_market",
        description="2022 inflation/rate bear. Slow 25% drawdown over 9 months.",
        start="2022-01-03",
        returns=[
            -0.018, -0.015, -0.022, 0.008, -0.014, -0.018, 0.011, -0.016,
            0.009, -0.022, -0.013, 0.005, -0.025, 0.007, -0.019, 0.006,
            -0.021, 0.012, -0.015, -0.019, 0.009, -0.017, 0.014, -0.013,
            0.006, -0.020, 0.010, -0.018, 0.007,
        ],
    ),
    StressScenario(
        name="aug_2015_flash_crash",
        description="Aug 2015 China devaluation + flash crash. Severe single-day shock.",
        start="2015-08-20",
        returns=[-0.022, -0.032, -0.040, -0.006, 0.039, -0.011, 0.002, 0.023, -0.015, -0.018],
    ),
    StressScenario(
        name="oct_1987_black_monday",
        description="Oct 19, 1987 Black Monday. -20% single day; extreme tail.",
        start="1987-10-19",
        returns=[-0.205, 0.054, 0.092, -0.080, 0.012, -0.031, 0.015, -0.021, 0.032, -0.018],
    ),
    StressScenario(
        name="2008_gfc",
        description="2008 Global Financial Crisis — Sept-Nov 2008 core drawdown.",
        start="2008-09-29",
        returns=[
            -0.088, 0.054, -0.038, -0.040, -0.015, -0.077, -0.050, -0.009, 0.113,
            -0.008, -0.047, -0.038, -0.004, -0.015, -0.012, 0.043, 0.065, -0.067,
            -0.060, -0.019, 0.028, -0.037, -0.020, 0.042, -0.035, 0.026, -0.022,
        ],
    ),
]


def stress_paths(
    initial_prices: dict[str, float], *, pre_padding_days: int = 0
) -> list[dict[str, list[float]]]:
    """Convert each stress scenario into a dict of price paths per symbol.

    Optional pre-padding replicates the initial price for N days before the
    shock, useful for strategies that want a warm-up period.
    """
    out = []
    for s in STRESS_SCENARIOS:
        scenario_paths = {}
        for sym, s0 in initial_prices.items():
            prices = [s0] * pre_padding_days + [s0]
            for r in s.returns:
                prices.append(prices[-1] * float(np.exp(r)))
            scenario_paths[sym] = prices
        out.append(scenario_paths)
    return out
