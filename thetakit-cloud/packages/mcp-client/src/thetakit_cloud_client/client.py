"""HTTP client for thetakit.cloud."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx


class CloudError(Exception):
    def __init__(self, status: int, detail: Any):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


@dataclass
class CloudClient:
    api_key: str
    base_url: str = "http://localhost:8000"
    timeout: float = 30.0

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as c:
            r = c.post(path, headers=self._headers(), json=body)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise CloudError(r.status_code, detail)
        return r.json()

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as c:
            r = c.get(path, headers=self._headers())
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise CloudError(r.status_code, detail)
        return r.json()

    # ---- OSS-facing API --------------------------------------------------

    def me(self) -> dict[str, Any]:
        return self._get("/v1/me")

    def run_smoke_eval(
        self, *, rule_yaml: str, universe: list[str], start: date, end: date
    ) -> dict[str, Any]:
        return self._post(
            "/v1/mcp/run_smoke_eval",
            {
                "rule_yaml": rule_yaml,
                "universe": universe,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

    def run_full_eval(
        self, *, rule_yaml: str, universe: list[str], start: date, end: date
    ) -> dict[str, Any]:
        return self._post(
            "/v1/mcp/run_full_eval",
            {
                "rule_yaml": rule_yaml,
                "universe": universe,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )

    def get_eval(self, handle: str) -> dict[str, Any]:
        return self._get(f"/v1/mcp/eval/{handle}")

    def health(self) -> dict[str, Any]:
        return self._get("/healthz")
