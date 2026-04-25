"""Billing routes — stubbed.

Stripe integration deferred to external SaaS. The ledger history endpoint
works today; purchase / checkout / webhook return 501 with a clear TODO.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from api.deps import CurrentUser, DbSession
from api.services import credit_service

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/history")
async def history(current_user: CurrentUser, db: DbSession) -> dict:
    entries = await credit_service.ledger_for_user(db, current_user.id, limit=200)
    balance = await credit_service.get_balance(db, current_user.id)
    return {
        "balance": balance,
        "history": [asdict(e) for e in entries],
    }


@router.post("/checkout")
async def checkout() -> None:
    raise HTTPException(
        status_code=501,
        detail="Stripe checkout integration not wired in this build. "
        "Stub endpoint only — see thetakit-cloud/STATUS.md.",
    )


@router.post("/webhook")
async def webhook() -> None:
    raise HTTPException(
        status_code=501,
        detail="Stripe webhook handling not wired in this build. "
        "Credit grants happen via POST /v1/auth/users (free tier) and "
        "programmatic credit_service.grant() calls.",
    )
