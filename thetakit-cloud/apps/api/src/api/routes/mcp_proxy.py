"""MCP-compatible endpoints the OSS toolkit can call with an API key.

These are simple passthroughs to the same eval service used by the web
routes — they exist because the OSS MCP client in packages/mcp-client
needs a stable HTTP surface.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from api.deps import CurrentUser, DbSession
from api.routes.evals import _run_eval_background, _to_list_item, _format_summary
from api.services import credit_service, eval_service

router = APIRouter(prefix="/v1/mcp", tags=["mcp"])


class RunEvalBody(BaseModel):
    rule_yaml: str
    universe: list[str] = Field(..., min_length=1)
    start: date
    end: date


@router.post("/run_smoke_eval")
async def run_smoke_eval(
    body: RunEvalBody, current_user: CurrentUser, db: DbSession,
    background: BackgroundTasks,
) -> dict:
    try:
        row = await eval_service.submit_eval(
            db, current_user,
            rule_yaml=body.rule_yaml, universe=body.universe,
            start=body.start, end=body.end, eval_type="smoke",
        )
    except credit_service.InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={"code": "insufficient_credits", "required": e.required, "available": e.available},
        ) from e
    await db.commit()
    background.add_task(_run_eval_background, row.id)
    return {"handle": row.id, "status": row.status, "eval_type": "smoke"}


@router.post("/run_full_eval")
async def run_full_eval(
    body: RunEvalBody, current_user: CurrentUser, db: DbSession,
    background: BackgroundTasks,
) -> dict:
    try:
        row = await eval_service.submit_eval(
            db, current_user,
            rule_yaml=body.rule_yaml, universe=body.universe,
            start=body.start, end=body.end, eval_type="full",
        )
    except credit_service.InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={"code": "insufficient_credits", "required": e.required, "available": e.available},
        ) from e
    await db.commit()
    background.add_task(_run_eval_background, row.id)
    return {"handle": row.id, "status": row.status, "eval_type": "full"}


@router.get("/eval/{handle}")
async def get_eval(handle: str, current_user: CurrentUser, db: DbSession) -> dict:
    from api.models import Eval

    row = await db.get(Eval, handle)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "handle": row.id,
        "status": row.status,
        "eval_type": row.eval_type,
        "stats": row.summary_stats,
        "summary_text": _format_summary(row),
        "error_message": row.error_message,
    }
