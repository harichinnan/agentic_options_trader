"""Eval submit + list + get routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select

from api.db import AsyncSessionLocal
from api.deps import CurrentUser, DbSession
from api.models import Eval
from api.schemas import EvalListItem, EvalResultResponse, SubmitEvalRequest
from api.services import credit_service, eval_service

router = APIRouter(prefix="/v1/evals", tags=["evals"])


async def _run_eval_background(eval_id: str) -> None:
    """Background task wrapper — uses a fresh DB session."""
    async with AsyncSessionLocal() as session:
        row = await session.get(Eval, eval_id)
        if row is None:
            return
        try:
            await eval_service.run_eval_in_process(session, row)
            await session.commit()
        except Exception:
            await session.rollback()
            # mark_failed already wrote state; persist it
            async with AsyncSessionLocal() as session2:
                pass


@router.post("", response_model=EvalListItem, status_code=202)
async def submit_eval(
    body: SubmitEvalRequest,
    current_user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> EvalListItem:
    try:
        row = await eval_service.submit_eval(
            db, current_user,
            rule_yaml=body.rule_yaml, universe=body.universe,
            start=body.start, end=body.end, eval_type=body.eval_type,
        )
    except credit_service.InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "insufficient_credits",
                "required": e.required,
                "available": e.available,
            },
        ) from e

    await db.commit()
    # Schedule the actual work asynchronously
    background.add_task(_run_eval_background, row.id)
    return _to_list_item(row)


@router.get("", response_model=list[EvalListItem])
async def list_evals(
    current_user: CurrentUser, db: DbSession, limit: int = 50
) -> list[EvalListItem]:
    stmt = (
        select(Eval)
        .where(Eval.user_id == current_user.id)
        .order_by(Eval.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_list_item(r) for r in rows]


@router.get("/{eval_id}", response_model=EvalResultResponse)
async def get_eval(
    eval_id: str, current_user: CurrentUser, db: DbSession
) -> EvalResultResponse:
    row = await db.get(Eval, eval_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="not found")
    summary = _format_summary(row)
    return EvalResultResponse(
        id=row.id, status=row.status, eval_type=row.eval_type,
        stats=row.summary_stats, result_blob_key=row.result_blob_key,
        error_message=row.error_message, summary_text=summary,
    )


@router.post("/{eval_id}/cancel", response_model=EvalResultResponse)
async def cancel_eval(
    eval_id: str, current_user: CurrentUser, db: DbSession
) -> EvalResultResponse:
    row = await db.get(Eval, eval_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await eval_service.cancel(db, row)
    except eval_service.IllegalEvalStateTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return EvalResultResponse(
        id=row.id, status=row.status, eval_type=row.eval_type,
        stats=row.summary_stats, result_blob_key=row.result_blob_key,
        error_message=row.error_message,
    )


def _to_list_item(row: Eval) -> EvalListItem:
    return EvalListItem(
        id=row.id, eval_type=row.eval_type, status=row.status,
        universe=list(row.universe), start_date=row.start_date,
        end_date=row.end_date, credits_charged=row.credits_charged,
        created_at=row.created_at, completed_at=row.completed_at,
        summary_stats=row.summary_stats,
    )


def _format_summary(row: Eval) -> str | None:
    if row.status != "complete" or not row.summary_stats:
        return None
    s = row.summary_stats
    return (
        f"{row.eval_type} eval of {row.rule_content_hash[:8]} on "
        f"{', '.join(row.universe)} [{row.start_date} → {row.end_date}]:\n"
        f"  median return: {s.get('return_median', 0):+.2f}%  "
        f"(p05 {s.get('return_p05', 0):+.2f}%, p95 {s.get('return_p95', 0):+.2f}%)\n"
        f"  drawdown p95: {s.get('drawdown_p95', 0):.2f}%  "
        f"CVaR 5%: {s.get('cvar_05', 0):+.2f}%\n"
        f"  prob-of-ruin (>25% dd): {s.get('prob_ruin_25pct', 0) * 100:.1f}%\n"
        f"  stress scenarios tested: {len(s.get('stress_results', {}))}"
    )
