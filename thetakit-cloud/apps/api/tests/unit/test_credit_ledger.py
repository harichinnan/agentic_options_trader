"""Credit ledger invariant tests.

Per spec: this is where silent money bugs live. The contract:

1. balance_from_ledger(user) == sum(delta) for every user, always.
2. reserve(cost) is atomic: either debits AND creates a ledger row, or does neither.
3. refund(eval_id) is idempotent: double-refund is a no-op, never over-refunds.
4. stripe_event_id uniqueness prevents duplicate webhook processing.
"""

from __future__ import annotations

import pytest

from api.models import User
from api.services import auth_service, credit_service


pytestmark = pytest.mark.asyncio


async def _new_user(session) -> User:
    import uuid
    email = f"{uuid.uuid4().hex[:8]}@test.example"
    return await auth_service.create_or_get_user(session, email=email)


class TestBalanceInvariant:
    async def test_sum_of_deltas_equals_reported_balance(self, db_session) -> None:
        user = await _new_user(db_session)  # 50-credit signup grant
        await credit_service.grant(db_session, user, 100)
        await credit_service.grant(db_session, user, 50)

        ledger = await credit_service.ledger_for_user(db_session, user.id)
        sum_deltas = sum(e.delta for e in ledger)
        reported = await credit_service.get_balance(db_session, user.id)
        assert sum_deltas == reported

    async def test_signup_grant_matches_free_tier(self, db_session) -> None:
        user = await _new_user(db_session)
        balance = await credit_service.get_balance(db_session, user.id)
        # Default free tier is 50
        assert balance == 50


class TestReserve:
    async def test_reserve_decrements_balance(self, db_session) -> None:
        user = await _new_user(db_session)
        before = await credit_service.get_balance(db_session, user.id)
        await credit_service.reserve(db_session, user, 20, eval_id="eval-1")
        after = await credit_service.get_balance(db_session, user.id)
        assert after == before - 20

    async def test_reserve_fails_cleanly_on_insufficient(self, db_session) -> None:
        user = await _new_user(db_session)
        before = await credit_service.get_balance(db_session, user.id)
        with pytest.raises(credit_service.InsufficientCreditsError) as exc:
            await credit_service.reserve(db_session, user, 10_000, eval_id="eval-x")
        assert exc.value.required == 10_000
        assert exc.value.available == before
        # Balance unchanged
        after = await credit_service.get_balance(db_session, user.id)
        assert after == before

    async def test_reserve_with_zero_cost_rejected(self, db_session) -> None:
        user = await _new_user(db_session)
        with pytest.raises(ValueError):
            await credit_service.reserve(db_session, user, 0, eval_id="eval-x")


class TestRefund:
    async def test_refund_restores_balance(self, db_session) -> None:
        user = await _new_user(db_session)
        initial = await credit_service.get_balance(db_session, user.id)
        await credit_service.reserve(db_session, user, 20, eval_id="eval-ref-1")
        after_reserve = await credit_service.get_balance(db_session, user.id)
        assert after_reserve == initial - 20

        await credit_service.refund(db_session, user, "eval-ref-1")
        after_refund = await credit_service.get_balance(db_session, user.id)
        assert after_refund == initial

    async def test_refund_is_idempotent(self, db_session) -> None:
        user = await _new_user(db_session)
        await credit_service.reserve(db_session, user, 20, eval_id="eval-ref-2")
        row1 = await credit_service.refund(db_session, user, "eval-ref-2")
        row2 = await credit_service.refund(db_session, user, "eval-ref-2")
        assert row1 is not None
        assert row2 is None  # second refund is a no-op
        # Balance is unchanged between the two calls
        bal = await credit_service.get_balance(db_session, user.id)
        assert bal == 50  # initial grant, reserve, refund = 50

    async def test_refund_without_consumption_is_noop(self, db_session) -> None:
        user = await _new_user(db_session)
        row = await credit_service.refund(db_session, user, "never-consumed-id")
        assert row is None
        bal = await credit_service.get_balance(db_session, user.id)
        assert bal == 50  # unchanged


class TestStripeIdempotency:
    async def test_duplicate_stripe_event_rejected(self, db_session) -> None:
        user = await _new_user(db_session)
        await credit_service.purchase(db_session, user, 200, stripe_event_id="evt_test_1")
        with pytest.raises(credit_service.DuplicateStripeEventError):
            await credit_service.purchase(db_session, user, 200, stripe_event_id="evt_test_1")


class TestGrantValidation:
    async def test_grant_negative_rejected(self, db_session) -> None:
        user = await _new_user(db_session)
        with pytest.raises(ValueError):
            await credit_service.grant(db_session, user, -10)

    async def test_purchase_zero_rejected(self, db_session) -> None:
        user = await _new_user(db_session)
        with pytest.raises(ValueError):
            await credit_service.purchase(db_session, user, 0, stripe_event_id="evt_x")
