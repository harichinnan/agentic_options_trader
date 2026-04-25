"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    email: str
    name: str | None = None


class MintKeyResponse(BaseModel):
    api_key: str = Field(..., description="Raw token, shown once.")
    prefix: str = Field(..., description="First 12 chars, safe to display.")
    key_id: str


class MeResponse(BaseModel):
    id: str
    email: str
    plan: str
    credit_balance: int
    subscription_status: str
