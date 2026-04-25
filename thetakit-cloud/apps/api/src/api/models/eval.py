"""Eval + Prediction models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class Eval(Base):
    __tablename__ = "evals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    rule_content_hash: Mapped[str] = mapped_column(String(64), index=True)
    rule_snapshot: Mapped[str] = mapped_column(Text)  # YAML captured at submit time
    universe: Mapped[list[str]] = mapped_column(JSON)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    eval_type: Mapped[str] = mapped_column(String(10))  # "smoke" | "full"
    model_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    credits_charged: Mapped[int] = mapped_column()
    modal_call_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    result_blob_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    eval_id: Mapped[str] = mapped_column(ForeignKey("evals.id"), index=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    statement: Mapped[str] = mapped_column(Text)
    probability: Mapped[float] = mapped_column()
    resolution_criterion: Mapped[str] = mapped_column(Text)
    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved: Mapped[bool] = mapped_column(default=False)
    resolved_outcome: Mapped[bool | None] = mapped_column(nullable=True)
    model_version: Mapped[str] = mapped_column(String(80))
