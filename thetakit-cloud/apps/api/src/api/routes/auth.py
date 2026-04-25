"""Auth routes — local-dev flavor.

Clerk integration replaces `POST /v1/auth/sessions` in production. For
local use and the OSS CLI, `POST /v1/auth/users` creates-or-gets a user
by email and returns a freshly-minted API key. This is intentionally
simple; see STATUS.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import CurrentUser, DbSession
from api.schemas import CreateUserRequest, MeResponse, MintKeyResponse
from api.services import auth_service, credit_service

router = APIRouter(prefix="/v1", tags=["auth"])


@router.post("/auth/users", response_model=MintKeyResponse)
async def create_user_and_mint_key(
    body: CreateUserRequest, db: DbSession
) -> MintKeyResponse:
    """Find-or-create user by email, return a new API key. Local-dev only."""
    user = await auth_service.create_or_get_user(db, email=body.email)
    raw, key = await auth_service.mint_api_key(db, user)
    return MintKeyResponse(api_key=raw, prefix=key.key_prefix, key_id=key.id)


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser, db: DbSession) -> MeResponse:
    balance = await credit_service.get_balance(db, current_user.id)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        plan=current_user.plan,
        credit_balance=balance,
        subscription_status=current_user.subscription_status,
    )


@router.delete("/api-keys/{key_id}")
async def revoke_key(key_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    ok = await auth_service.revoke_api_key(db, key_id=key_id, user_id=current_user.id)
    return {"revoked": ok}
