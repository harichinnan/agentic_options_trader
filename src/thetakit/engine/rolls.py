"""Roll trigger logic.

A position is rolled when any configured RollRule fires. Triggers:
- short_strike_tested: intraday high/low crossed the short strike
- delta_breach: abs(short leg delta) exceeded delta_threshold
- dte_threshold: DTE dropped at or below dte_threshold
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from thetakit.data.adapter import UnderlyingBar
from thetakit.dsl.schema import RollRule
from thetakit.engine.position import OptionLeg, Position
from thetakit.pricing.bsm import bsm_greeks, time_to_expiry_years


@dataclass(frozen=True, slots=True)
class RollSignal:
    fired: bool
    trigger: str | None = None
    reason: str | None = None
    tested_intraday: bool = False


def _short_legs(pos: Position) -> list[OptionLeg]:
    return [leg for leg in pos.legs if leg.side == "short"]


def evaluate_rolls(
    position: Position,
    rules: Iterable[RollRule],
    underlying: UnderlyingBar,
    on: date,
    *,
    r: float = 0.04,
    sigma: float = 0.20,
) -> RollSignal:
    """Return the first roll signal that fires, or a non-firing signal."""
    for rule in rules:
        signal = _evaluate_one(position, rule, underlying, on, r=r, sigma=sigma)
        if signal.fired:
            return signal
    return RollSignal(fired=False)


def _evaluate_one(
    position: Position,
    rule: RollRule,
    underlying: UnderlyingBar,
    on: date,
    *,
    r: float,
    sigma: float,
) -> RollSignal:
    shorts = _short_legs(position)
    if not shorts:
        return RollSignal(False)

    primary = shorts[0]

    if rule.trigger == "short_strike_tested":
        tested = False
        # Short call → test when high >= strike; short put → test when low <= strike
        if primary.option_type == "call" and underlying.high >= primary.strike:
            tested = True
        elif primary.option_type == "put" and underlying.low <= primary.strike:
            tested = True
        if tested:
            return RollSignal(
                fired=True,
                trigger="short_strike_tested",
                reason=(
                    f"short {primary.option_type} strike {primary.strike} tested by "
                    f"bar high={underlying.high} low={underlying.low}"
                ),
                tested_intraday=True,
            )
        return RollSignal(False)

    if rule.trigger == "delta_breach":
        t = time_to_expiry_years(primary.expiration, on.isoformat())
        if t <= 0:
            return RollSignal(False)
        g = bsm_greeks(
            s=underlying.close,
            k=primary.strike,
            t=t,
            r=r,
            sigma=sigma,
            option_type=primary.option_type,  # type: ignore[arg-type]
        )
        threshold = rule.delta_threshold or 0.5
        if abs(g.delta) >= threshold:
            return RollSignal(
                fired=True,
                trigger="delta_breach",
                reason=f"short leg delta={g.delta:.3f} breached threshold {threshold}",
            )
        return RollSignal(False)

    if rule.trigger == "dte_threshold":
        dte = (date.fromisoformat(primary.expiration) - on).days
        if rule.dte_threshold is not None and dte <= rule.dte_threshold:
            return RollSignal(
                fired=True,
                trigger="dte_threshold",
                reason=f"DTE={dte} <= threshold {rule.dte_threshold}",
            )
        return RollSignal(False)

    return RollSignal(False)
