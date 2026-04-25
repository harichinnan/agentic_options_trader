"""Eval service state machine tests."""

from __future__ import annotations

from datetime import date

import pytest

from api.services import auth_service, credit_service, eval_service
from thetakit.dsl import get_template

pytestmark = pytest.mark.asyncio


async def _new_user(db_session):
    import uuid
    user = await auth_service.create_or_get_user(
        db_session, email=f"{uuid.uuid4().hex[:8]}@test.example"
    )
    # Top up so the user can afford a full eval
    await credit_service.grant(db_session, user, 100)
    return user


class TestSubmit:
    async def test_submit_smoke_reserves_one_credit(self, db_session) -> None:
        user = await _new_user(db_session)
        before = await credit_service.get_balance(db_session, user.id)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="smoke",
        )
        assert row.status == "queued"
        assert row.credits_charged == 1
        after = await credit_service.get_balance(db_session, user.id)
        assert after == before - 1

    async def test_submit_full_reserves_twenty_credits(self, db_session) -> None:
        user = await _new_user(db_session)
        before = await credit_service.get_balance(db_session, user.id)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="full",
        )
        assert row.credits_charged == 20
        assert (await credit_service.get_balance(db_session, user.id)) == before - 20

    async def test_submit_invalid_type_rejected(self, db_session) -> None:
        user = await _new_user(db_session)
        with pytest.raises(ValueError):
            await eval_service.submit_eval(
                db_session, user,
                rule_yaml=get_template("wheel"), universe=["SPY"],
                start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="extreme",
            )


class TestStateTransitions:
    async def test_full_happy_path(self, db_session) -> None:
        user = await _new_user(db_session)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="smoke",
        )
        await eval_service.mark_running(db_session, row)
        assert row.status == "running"
        await eval_service.mark_complete(
            db_session, row, result_blob_key="k", summary_stats={"return_median": 1.5}
        )
        assert row.status == "complete"

    async def test_failure_auto_refunds(self, db_session) -> None:
        user = await _new_user(db_session)
        initial = await credit_service.get_balance(db_session, user.id)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="full",
        )
        await eval_service.mark_running(db_session, row)
        await eval_service.mark_failed(db_session, row, error_message="boom")
        assert row.status == "failed"
        # Credits refunded
        final = await credit_service.get_balance(db_session, user.id)
        assert final == initial

    async def test_cancel_from_queued_refunds(self, db_session) -> None:
        user = await _new_user(db_session)
        initial = await credit_service.get_balance(db_session, user.id)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="smoke",
        )
        await eval_service.cancel(db_session, row)
        assert row.status == "canceled"
        final = await credit_service.get_balance(db_session, user.id)
        assert final == initial

    async def test_illegal_transition_raises(self, db_session) -> None:
        user = await _new_user(db_session)
        row = await eval_service.submit_eval(
            db_session, user,
            rule_yaml=get_template("wheel"), universe=["SPY"],
            start=date(2024, 1, 1), end=date(2024, 2, 1), eval_type="smoke",
        )
        await eval_service.mark_running(db_session, row)
        await eval_service.mark_complete(
            db_session, row, result_blob_key="k", summary_stats={}
        )
        with pytest.raises(eval_service.IllegalEvalStateTransition):
            await eval_service.mark_running(db_session, row)
