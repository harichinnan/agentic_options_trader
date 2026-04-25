"""Credit ledger + Stripe webhook idempotency."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class CreditLedger(Base):
    """Append-only. Balance is derived by summing deltas per user.

    Reasons:
      - grant: signup bonus, promotional, refund adjustment
      - purchase: user bought a credit pack
      - subscription_grant: monthly grant from subscription
      - consumption: eval charged
      - refund: failed eval → credits returned
    """

    __tablename__ = "credit_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)  # positive or negative
    reason: Mapped[str] = mapped_column(String(40))
    eval_id: Mapped[str | None] = mapped_column(ForeignKey("evals.id"), nullable=True, index=True)
    stripe_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class StripeEvent(Base):
    """Webhook idempotency store — every event processed exactly once."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)  # Stripe event id
    type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
