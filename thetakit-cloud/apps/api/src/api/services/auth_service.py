"""API key generation + verification.

Clerk OAuth + magic-link is deferred to external integration (spec 7.1).
For local development and the OSS CLI's `thetakit auth` flow, we use
API-key bearer auth: issue a random token, store its hash, and the
client sends the raw token on every request.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from api.models import ApiKey, User
from api.services import credit_service
from api.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _hash_token(raw: str) -> str:
    """Fast hash (sha256) — bcrypt/argon2 is the production recommendation but
    adds a dep for minimal gain on a 32-byte random secret. Upgrade in prod."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_token() -> tuple[str, str, str]:
    """Return (raw_token, token_hash, prefix)."""
    raw = "tk_" + secrets.token_urlsafe(32)
    return raw, _hash_token(raw), raw[:12]


async def create_or_get_user(session: "AsyncSession", *, email: str) -> User:
    """Find-or-create a user by email. Grants free-tier credits on first creation."""
    stmt = select(User).where(User.email == email)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing
    settings = get_settings()
    user = User(email=email)
    session.add(user)
    await session.flush()
    await credit_service.grant(
        session, user, settings.free_tier_credits,
        reason="grant", note="free tier signup bonus",
    )
    return user


async def mint_api_key(
    session: "AsyncSession", user: User, *, name: str = "default"
) -> tuple[str, ApiKey]:
    """Return (raw_token, stored_key). The raw token is shown once; only the hash is stored."""
    raw, hashed, prefix = _generate_token()
    key = ApiKey(
        user_id=user.id,
        key_hash=hashed,
        key_prefix=prefix,
        name=name,
    )
    session.add(key)
    await session.flush()
    return raw, key


async def verify_api_key(session: "AsyncSession", raw_token: str) -> User | None:
    """Return the owning User if token is valid and not revoked."""
    if not raw_token or not raw_token.startswith("tk_"):
        return None
    hashed = _hash_token(raw_token)
    stmt = select(ApiKey).where(ApiKey.key_hash == hashed)
    key = (await session.execute(stmt)).scalar_one_or_none()
    if key is None or key.revoked_at is not None:
        return None
    key.last_used_at = datetime.utcnow()
    user = await session.get(User, key.user_id)
    return user


async def revoke_api_key(
    session: "AsyncSession", *, key_id: str, user_id: str
) -> bool:
    key = await session.get(ApiKey, key_id)
    if key is None or key.user_id != user_id:
        return False
    if key.revoked_at is not None:
        return True
    key.revoked_at = datetime.utcnow()
    return True
