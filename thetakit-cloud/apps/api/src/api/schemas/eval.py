"""Eval schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SubmitEvalRequest(BaseModel):
    rule_yaml: str
    universe: list[str] = Field(..., min_length=1)
    start: date
    end: date
    eval_type: Literal["smoke", "full"] = "smoke"


class EvalListItem(BaseModel):
    id: str
    eval_type: str
    status: str
    universe: list[str]
    start_date: date
    end_date: date
    credits_charged: int
    created_at: datetime
    completed_at: datetime | None
    summary_stats: dict | None


class EvalResultResponse(BaseModel):
    id: str
    status: str
    eval_type: str
    stats: dict[str, Any] | None = None
    result_blob_key: str | None = None
    error_message: str | None = None
    summary_text: str | None = None
