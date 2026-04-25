"""Env-driven config."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THETAKIT_", env_file=".env", extra="ignore")

    # DB
    database_url: str = "sqlite+aiosqlite:///./thetakit_cloud.db"
    # Data dir for eval result blobs (S3 in prod)
    data_dir: Path = Field(default=Path("./data/eval_blobs"))
    # Free tier credit grant on signup
    free_tier_credits: int = 50
    # Eval costs
    smoke_eval_cost: int = 1
    full_eval_cost: int = 20
    # Model version identifier
    model_version: str = "minimal-student-t-v0"
    # Secret for Modal callback auth
    modal_callback_secret: str = "dev-secret-change-me"


def get_settings() -> Settings:
    return Settings()
