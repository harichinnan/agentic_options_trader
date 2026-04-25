"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import __version__
from api.db import init_db
from api.routes import auth as auth_routes
from api.routes import billing as billing_routes
from api.routes import evals as evals_routes
from api.routes import mcp_proxy as mcp_routes
from api.routes import rules as rules_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="thetakit.cloud",
    version=__version__,
    description=(
        "Hosted distributional evaluation service for premium-selling strategies. "
        "Phase 2 scaffold — see /STATUS.md for what's shipped vs stubbed."
    ),
    lifespan=lifespan,
)

app.include_router(auth_routes.router)
app.include_router(rules_routes.router)
app.include_router(evals_routes.router)
app.include_router(billing_routes.router)
app.include_router(mcp_routes.router)


@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "version": __version__}
