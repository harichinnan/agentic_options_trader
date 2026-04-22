"""Expiration and assignment handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from thetakit.engine.position import Position, PositionStatus


@dataclass(frozen=True, slots=True)
class ExpirationResult:
    """Outcome of processing a position at its expiration."""

    status: PositionStatus
    settlement_value: float  # per-contract debit required to close at settlement
    reason: str


def settle_at_expiration(position: Position, underlying_close: float) -> ExpirationResult:
    """Compute cash-settled value for each leg at expiration and classify.

    We treat every leg as cash-settled for Phase 1 (even for CC on shares,
    we settle the call in cash and assume the user handles share mechanics).
    Extension point: return an ASSIGNED status when ITM for a short and
    delegate share movement to a separate layer.
    """
    total_intrinsic = 0.0
    any_itm_short = False

    for leg in position.legs:
        if leg.option_type == "call":
            intrinsic = max(underlying_close - leg.strike, 0.0)
        else:
            intrinsic = max(leg.strike - underlying_close, 0.0)

        # The signed_quantity convention: positive qty for long legs receives
        # intrinsic; negative (short) legs owe intrinsic.
        total_intrinsic += intrinsic * leg.signed_quantity * leg.multiplier
        if leg.side == "short" and intrinsic > 0:
            any_itm_short = True

    # settlement_value is what we "pay to close" — positive if we owe.
    # For a short premium position, credit_received is already booked; we
    # add total_intrinsic as a cost (it's negative-signed because shorts are
    # negative, so the aggregation above naturally produces a negative value
    # when we owe money).
    settlement_value = -total_intrinsic / (
        position.legs[0].multiplier if position.legs else 100
    )

    if any_itm_short:
        return ExpirationResult(
            status=PositionStatus.ASSIGNED,
            settlement_value=settlement_value,
            reason="ITM short leg at expiration (cash-settled)",
        )
    return ExpirationResult(
        status=PositionStatus.EXPIRED,
        settlement_value=0.0,
        reason="all legs expired worthless or OTM",
    )


def is_expiring_today(position: Position, today: date) -> bool:
    return any(leg.expiration == today.isoformat() for leg in position.legs)
