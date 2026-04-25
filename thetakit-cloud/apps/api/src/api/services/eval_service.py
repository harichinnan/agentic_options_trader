"""Eval lifecycle service.

State machine per spec 7.4:
  queued → running → complete
                   → failed (auto-refund)
                   → canceled (auto-refund)

In prod this enqueues a Modal function; here we run in-process.
The transition methods are the same either way.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.models import Eval, User
from api.services import credit_service


VALID_STATES = {"queued", "running", "complete", "failed", "canceled"}


class IllegalEvalStateTransition(Exception):
    pass


async def submit_eval(
    session: AsyncSession,
    user: User,
    *,
    rule_yaml: str,
    universe: list[str],
    start: date,
    end: date,
    eval_type: str,
) -> Eval:
    """Charge credits + create the Eval row in 'queued' state."""
    settings = get_settings()
    if eval_type not in ("smoke", "full"):
        raise ValueError(f"invalid eval_type: {eval_type}")
    cost = settings.smoke_eval_cost if eval_type == "smoke" else settings.full_eval_cost

    content_hash = hashlib.sha256(rule_yaml.encode()).hexdigest()[:32]

    row = Eval(
        user_id=user.id,
        rule_content_hash=content_hash,
        rule_snapshot=rule_yaml,
        universe=list(universe),
        start_date=start,
        end_date=end,
        eval_type=eval_type,
        model_version=settings.model_version,
        status="queued",
        credits_charged=cost,
    )
    session.add(row)
    await session.flush()

    # Reserve credits atomically with the eval creation
    await credit_service.reserve(session, user, cost, eval_id=row.id)
    return row


async def mark_running(session: AsyncSession, eval_row: Eval) -> None:
    if eval_row.status != "queued":
        raise IllegalEvalStateTransition(f"{eval_row.status} → running")
    eval_row.status = "running"
    eval_row.started_at = datetime.utcnow()


async def mark_complete(
    session: AsyncSession,
    eval_row: Eval,
    *,
    result_blob_key: str,
    summary_stats: dict[str, Any],
) -> None:
    if eval_row.status not in ("queued", "running"):
        raise IllegalEvalStateTransition(f"{eval_row.status} → complete")
    eval_row.status = "complete"
    eval_row.completed_at = datetime.utcnow()
    eval_row.result_blob_key = result_blob_key
    eval_row.summary_stats = summary_stats


async def mark_failed(
    session: AsyncSession,
    eval_row: Eval,
    *,
    error_message: str,
) -> None:
    if eval_row.status in ("complete", "failed", "canceled"):
        raise IllegalEvalStateTransition(f"{eval_row.status} → failed")
    eval_row.status = "failed"
    eval_row.completed_at = datetime.utcnow()
    eval_row.error_message = error_message

    user = await session.get(User, eval_row.user_id)
    if user is not None:
        await credit_service.refund(
            session, user, eval_row.id, note=f"eval failed: {error_message[:80]}"
        )


async def cancel(session: AsyncSession, eval_row: Eval) -> None:
    if eval_row.status not in ("queued", "running"):
        raise IllegalEvalStateTransition(f"{eval_row.status} → canceled")
    eval_row.status = "canceled"
    eval_row.completed_at = datetime.utcnow()
    user = await session.get(User, eval_row.user_id)
    if user is not None:
        await credit_service.refund(
            session, user, eval_row.id, note="eval canceled by user"
        )


# ---- Runner integration ------------------------------------------------------


async def run_eval_in_process(session: AsyncSession, eval_row: Eval) -> None:
    """Execute the eval via the compute engine in-process.

    In production this enqueues a Modal function instead. Both paths mutate
    the DB through the same `mark_*` functions so state-machine invariants
    are identical.
    """
    from compute.eval_runner import EvalInput, run_full_eval, run_smoke_eval

    await mark_running(session, eval_row)
    await session.commit()

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    try:
        universe = list(eval_row.universe)
        initial_prices = {sym: 100.0 + 20 * i for i, sym in enumerate(universe)}
        inp = EvalInput(
            rule_yaml=eval_row.rule_snapshot,
            universe=universe,
            initial_prices=initial_prices,
            start=eval_row.start_date.isoformat(),
            end=eval_row.end_date.isoformat(),
            seed=42,
        )
        # Offload synchronous CPU work so the event loop isn't blocked in tests
        loop = asyncio.get_event_loop()
        if eval_row.eval_type == "smoke":
            result = await loop.run_in_executor(None, run_smoke_eval, inp)
        else:
            # Full eval is capped smaller for local dev to keep wall time reasonable
            result = await loop.run_in_executor(
                None, lambda: run_full_eval(inp, n_paths=500)
            )

        blob_key = f"eval_blobs/{eval_row.id}.json"
        blob_path = settings.data_dir.parent / blob_key
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_text(
            json.dumps(
                {
                    "eval_id": eval_row.id,
                    "eval_type": result.eval_type,
                    "n_paths": result.n_paths,
                    "stats": asdict(result.stats),
                    "sample_paths": result.sample_paths,
                    "model_version": result.model_version,
                },
                default=str,
            )
        )
        await mark_complete(
            session, eval_row,
            result_blob_key=blob_key,
            summary_stats=asdict(result.stats),
        )
    except Exception as e:  # pragma: no cover - defensive
        await mark_failed(session, eval_row, error_message=str(e))
        raise
