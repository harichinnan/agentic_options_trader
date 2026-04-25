# thetakit.cloud — Phase 2

Hosted distributional evaluation service on top of the open source `thetakit`
toolkit (Phase 1). This directory is a monorepo for the Phase 2 components.

See [../docs/spec-phase-2.md](../docs/spec-phase-2.md) for the authoritative
spec and [./STATUS.md](STATUS.md) for what's implemented in this session
vs what's deliberately stubbed.

## Layout

```
thetakit-cloud/
  apps/
    api/           # FastAPI backend (SQLite locally; Postgres in prod)
    compute/       # HMM + path simulator + aggregator (Modal in prod, in-proc locally)
    web/           # Next.js frontend [not in this scaffold — see STATUS.md]
  packages/
    mcp-client/    # Client library used by the OSS toolkit for hosted evals
  infra/
    modal/         # Modal deployment config [stubbed]
```

## Running locally

```bash
# From the repo root
source .venv/bin/activate
pip install -e './thetakit-cloud/apps/api' -e './thetakit-cloud/apps/compute' -e './thetakit-cloud/packages/mcp-client'

# Initialize the SQLite DB
python -m api.db init

# Run the API on http://localhost:8000
uvicorn api.main:app --reload

# Run the end-to-end smoke eval from the OSS CLI (once API key is minted)
thetakit auth --key <key-printed-at-api-start>
thetakit smoke-eval src/thetakit/templates/wheel.yaml --universe SPY,QQQ --from 2024-01-01 --to 2024-06-30
```

## Shipped vs stubbed

See [STATUS.md](STATUS.md).
