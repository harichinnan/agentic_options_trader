"""Credit ledger service.

Contract (spec section 6.1 "Credits and billing", 7.4 "critical notes"):
1. Every eval decrements balance at enqueue time. Never enqueue what you
   haven't charged.
2. Failed evals automatically refund credits — no manual intervention.
3. The ledger is append-only. The denormalized `users.credit_balance`
   is a cache; the ledger is the source of truth.
4. Every write is tagged with a reason. The audit log is the ledger.
5. Stripe events use `stripe_event_id` for idempotency — processing the
   same event twice is a no-op.

Invariants enforced by this service and tested:
- balance_from_ledger(user) == sum(delta) for every user, always.
- reserve(user, cost) atomically: either decrements balance and creates
  a ledger row, or fails cleanly (insufficient funds) and does neither.
- refund(eval) never over-refunds: the refund amount is read from the
  consumption ledger entry, not guessed.
- stripe_event_id is unique across the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import CreditLedger, User


class InsufficientCreditsError(Exception):
    def __init__(self, user_id: str, required: int, available: int):
        super().__init__(
            f"user {user_id} needs {required} credits, has {available}"
        )
        self.required = required
        self.available = available


class DuplicateStripeEventError(Exception):
    """Raised when the same Stripe event id is applied twice."""


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    id: str
    delta: int
    reason: str
    eval_id: str | None
    note: str | None


async def get_balance(session: AsyncSession, user_id: str) -> int:
    """Recompute balance from the ledger — authoritative."""
    stmt = select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(
        CreditLedger.user_id == user_id
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def _append(
    session: AsyncSession,
    *,
    user: User,
    delta: int,
    reason: str,
    eval_id: str | None = None,
    stripe_event_id: str | None = None,
    note: str | None = None,
) -> CreditLedger:
    row = CreditLedger(
        user_id=user.id,
        delta=delta,
        reason=reason,
        eval_id=eval_id,
        stripe_event_id=stripe_event_id,
        note=note,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as e:
        # Typically stripe_event_id uniqueness
        raise DuplicateStripeEventError(str(e)) from e
    # Refresh denormalized balance
    user.credit_balance = await get_balance(session, user.id)
    return row


async def grant(
    session: AsyncSession,
    user: User,
    amount: int,
    *,
    reason: str = "grant",
    note: str | None = None,
    stripe_event_id: str | None = None,
) -> CreditLedger:
    if amount <= 0:
        raise ValueError("grant amount must be positive")
    return await _append(
        session, user=user, delta=amount,
        reason=reason, note=note, stripe_event_id=stripe_event_id,
    )


async def purchase(
    session: AsyncSession,
    user: User,
    amount: int,
    *,
    stripe_event_id: str,
    note: str | None = None,
) -> CreditLedger:
    if amount <= 0:
        raise ValueError("purchase amount must be positive")
    return await _append(
        session, user=user, delta=amount,
        reason="purchase", note=note, stripe_event_id=stripe_event_id,
    )


async def reserve(
    session: AsyncSession,
    user: User,
    cost: int,
    *,
    eval_id: str,
) -> CreditLedger:
    """Atomically charge the user for an eval about to run.

    Raises InsufficientCreditsError without writing if balance < cost.
    """
    if cost <= 0:
        raise ValueError("cost must be positive")
    balance = await get_balance(session, user.id)
    if balance < cost:
        raise InsufficientCreditsError(user.id, cost, balance)
    return await _append(
        session, user=user, delta=-cost,
        reason="consumption", eval_id=eval_id,
    )


async def refund(
    session: AsyncSession,
    user: User,
    eval_id: str,
    *,
    note: str | None = None,
) -> CreditLedger | None:
    """Refund a previously-consumed eval. Idempotent: if the eval was never
    consumed or was already refunded, returns None without writing."""
    # Find the consumption row (negative delta) for this eval
    stmt = (
        select(CreditLedger)
        .where(CreditLedger.eval_id == eval_id)
        .where(CreditLedger.reason == "consumption")
    )
    consumption = (await session.execute(stmt)).scalar_one_or_none()
    if consumption is None:
        return None

    # Check if already refunded
    stmt_refund = (
        select(CreditLedger)
        .where(CreditLedger.eval_id == eval_id)
        .where(CreditLedger.reason == "refund")
    )
    existing = (await session.execute(stmt_refund)).scalar_one_or_none()
    if existing is not None:
        return None

    return await _append(
        session, user=user, delta=-consumption.delta,  # flip the sign of the charge
        reason="refund", eval_id=eval_id, note=note,
    )


async def ledger_for_user(
    session: AsyncSession, user_id: str, *, limit: int = 100
) -> list[LedgerEntry]:
    stmt = (
        select(CreditLedger)
        .where(CreditLedger.user_id == user_id)
        .order_by(CreditLedger.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        LedgerEntry(id=r.id, delta=r.delta, reason=r.reason, eval_id=r.eval_id, note=r.note)
        for r in rows
    ]
