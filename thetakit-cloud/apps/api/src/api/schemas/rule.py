"""Rule schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RuleCreateRequest(BaseModel):
    name: str
    yaml_source: str


class RuleResponse(BaseModel):
    id: str
    name: str
    yaml_source: str
    content_hash: str
    created_at: datetime
    updated_at: datetime


class ValidateResponse(BaseModel):
    valid: bool
    name: str | None = None
    strategy_type: str | None = None
    errors: list[dict] = []
