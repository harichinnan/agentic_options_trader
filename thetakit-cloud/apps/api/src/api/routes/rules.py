"""Rule CRUD + validation."""

from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from api.models import Rule
from api.schemas import RuleCreateRequest, RuleResponse, ValidateResponse
from thetakit.dsl import StrategyLoadError, ValidationError, validate_strategy

router = APIRouter(prefix="/v1/rules", tags=["rules"])


def _hash(y: str) -> str:
    return hashlib.sha256(y.encode()).hexdigest()[:32]


@router.post("/validate", response_model=ValidateResponse)
async def validate(body: RuleCreateRequest) -> ValidateResponse:
    try:
        strat = validate_strategy(body.yaml_source)
    except ValidationError as e:
        return ValidateResponse(
            valid=False,
            errors=[
                {"path": i.path, "message": i.message, "severity": i.severity}
                for i in e.issues
            ],
        )
    except StrategyLoadError as e:
        return ValidateResponse(valid=False, errors=[{"path": "<root>", "message": str(e)}])
    return ValidateResponse(
        valid=True, name=strat.name, strategy_type=strat.entry.strategy.value
    )


@router.post("", response_model=RuleResponse)
async def create_rule(
    body: RuleCreateRequest, current_user: CurrentUser, db: DbSession
) -> RuleResponse:
    try:
        validate_strategy(body.yaml_source)
    except (ValidationError, StrategyLoadError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    rule = Rule(
        user_id=current_user.id,
        name=body.name,
        yaml_source=body.yaml_source,
        content_hash=_hash(body.yaml_source),
    )
    db.add(rule)
    await db.flush()
    return RuleResponse(
        id=rule.id, name=rule.name, yaml_source=rule.yaml_source,
        content_hash=rule.content_hash, created_at=rule.created_at, updated_at=rule.updated_at,
    )


@router.get("", response_model=list[RuleResponse])
async def list_rules(current_user: CurrentUser, db: DbSession) -> list[RuleResponse]:
    stmt = select(Rule).where(Rule.user_id == current_user.id).order_by(Rule.updated_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [
        RuleResponse(
            id=r.id, name=r.name, yaml_source=r.yaml_source,
            content_hash=r.content_hash, created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str, current_user: CurrentUser, db: DbSession) -> RuleResponse:
    rule = await db.get(Rule, rule_id)
    if rule is None or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="not found")
    return RuleResponse(
        id=rule.id, name=rule.name, yaml_source=rule.yaml_source,
        content_hash=rule.content_hash, created_at=rule.created_at, updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    rule = await db.get(Rule, rule_id)
    if rule is None or rule.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(rule)
    return {"deleted": True}
