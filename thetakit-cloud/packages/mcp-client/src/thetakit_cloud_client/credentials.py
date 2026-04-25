"""Credentials file management for the OSS toolkit.

Per spec 6.1: `thetakit auth --key <key>` stores credentials in
~/.thetakit/credentials.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Credentials:
    api_key: str
    base_url: str = "http://localhost:8000"


def _cred_path() -> Path:
    override = os.environ.get("THETAKIT_CREDENTIALS")
    if override:
        return Path(override)
    return Path.home() / ".thetakit" / "credentials"


def save_credentials(creds: Credentials) -> Path:
    path = _cred_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(creds)))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def load_credentials() -> Credentials | None:
    path = _cred_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return Credentials(api_key=data["api_key"], base_url=data.get("base_url", "http://localhost:8000"))
