"""Heuristic American-exercise handling.

Per spec Q3, Phase 1 ships with a simple heuristic (assign ITM calls within
1 day of ex-div if their time value is below the dividend) rather than a
full Bjerksund-Stensland binomial. This module exposes that heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass

from thetakit.pricing.bsm import bsm_price


@dataclass(frozen=True, slots=True)
class EarlyExerciseDecision:
    """Result of an early-exercise check."""

    should_exercise: bool
    reason: str


def should_early_exercise_call(
    *,
    spot: float,
    strike: float,
    option_market_price: float,
    dividend: float,
    days_to_ex_div: int,
    days_to_expiry: int,
    r: float,
    sigma: float,
) -> EarlyExerciseDecision:
    """Heuristic for American call early-exercise around a discrete dividend.

    Rule of thumb: if the option is ITM, ex-div is imminent (≤1 day), and
    the remaining time value is less than the dividend being forfeited,
    a rational holder exercises before ex-div to capture the dividend.

    This is a conservative approximation — it will miss some deep-ITM cases
    and over-trigger when r is high — but it's transparent and documented.
    """
    if spot <= strike:
        return EarlyExerciseDecision(False, "OTM")
    if dividend <= 0:
        return EarlyExerciseDecision(False, "no dividend")
    if days_to_ex_div > 1:
        return EarlyExerciseDecision(False, "not adjacent to ex-div")
    if days_to_expiry <= 0:
        return EarlyExerciseDecision(True, "at expiry")

    intrinsic = spot - strike
    time_value = max(option_market_price - intrinsic, 0.0)

    if time_value < dividend:
        return EarlyExerciseDecision(
            True, f"time_value={time_value:.3f} < dividend={dividend:.3f}"
        )
    return EarlyExerciseDecision(
        False, f"time_value={time_value:.3f} >= dividend={dividend:.3f}"
    )


def put_early_exercise_unlikely(
    *,
    spot: float,
    strike: float,
    option_market_price: float,
    r: float,
    days_to_expiry: int,
) -> bool:
    """Puts are only rationally exercised early when very deep ITM and r is high.

    For Phase 1 we return True (meaning "assume not exercised") unless the
    put is so deep ITM that time value is negative or zero — in which case
    the short-put holder may be assigned.
    """
    intrinsic = max(strike - spot, 0.0)
    if days_to_expiry <= 0:
        return False  # at expiry, it just settles
    time_value = max(option_market_price - intrinsic, 0.0)
    # Extremely deep ITM with near-zero time value
    return time_value > 0.01
