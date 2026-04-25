"""Pytest config for thetakit-cloud API tests.

Uses an ephemeral per-test SQLite DB so tests are isolated.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio

# Must be set before importing api modules
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["THETAKIT_DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"

from api.db import AsyncSessionLocal, init_db  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    await init_db()
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
