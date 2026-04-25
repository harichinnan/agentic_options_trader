"""End-to-end HTTP tests via FastAPI TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from thetakit.dsl import get_template


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    import uuid
    email = f"{uuid.uuid4().hex[:8]}@test.example"
    r = client.post("/v1/auth/users", json={"email": email})
    assert r.status_code == 200
    token = r.json()["api_key"]
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_healthz(self, client: TestClient) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestAuth:
    def test_signup_grants_free_credits(self, client: TestClient) -> None:
        import uuid
        r = client.post("/v1/auth/users", json={"email": f"{uuid.uuid4().hex[:6]}@t.example"})
        assert r.status_code == 200
        body = r.json()
        token = body["api_key"]
        assert token.startswith("tk_")
        me = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["credit_balance"] == 50

    def test_invalid_token_rejected(self, client: TestClient) -> None:
        r = client.get("/v1/me", headers={"Authorization": "Bearer tk_bad"})
        assert r.status_code == 401

    def test_missing_token_rejected(self, client: TestClient) -> None:
        r = client.get("/v1/me")
        assert r.status_code == 401


class TestRules:
    def test_validate_good_rule(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            "/v1/rules/validate",
            json={"name": "test", "yaml_source": get_template("wheel")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_create_and_list_rules(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            "/v1/rules",
            json={"name": "my-wheel", "yaml_source": get_template("wheel")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        rule_id = r.json()["id"]

        listing = client.get("/v1/rules", headers=auth_headers).json()
        assert any(x["id"] == rule_id for x in listing)


class TestEvalSubmit:
    def test_insufficient_credits_returns_402(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        # Free tier is 50; a full eval costs 20. Two full evals = 40 credits. Three = 60, fails.
        body = {
            "rule_yaml": get_template("wheel"),
            "universe": ["SPY"],
            "start": "2024-01-01",
            "end": "2024-01-10",
            "eval_type": "full",
        }
        for _ in range(2):
            r = client.post("/v1/evals", json=body, headers=auth_headers)
            assert r.status_code == 202
        r = client.post("/v1/evals", json=body, headers=auth_headers)
        assert r.status_code == 402

    def test_smoke_eval_cycle(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        import time
        r = client.post(
            "/v1/evals",
            json={
                "rule_yaml": get_template("wheel"),
                "universe": ["SPY"],
                "start": "2024-01-02",
                "end": "2024-01-05",
                "eval_type": "smoke",
            },
            headers=auth_headers,
        )
        assert r.status_code == 202
        eval_id = r.json()["id"]
        # Poll a few times for completion
        for _ in range(30):
            r2 = client.get(f"/v1/evals/{eval_id}", headers=auth_headers)
            status = r2.json()["status"]
            if status in ("complete", "failed"):
                break
            time.sleep(0.2)
        assert status in ("complete", "failed")


class TestBilling:
    def test_checkout_is_stubbed(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post("/v1/billing/checkout", headers=auth_headers)
        assert r.status_code == 501

    def test_history_returns_grants(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.get("/v1/billing/history", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["balance"] == 50
        # At least the signup grant
        assert any(h["reason"] == "grant" for h in body["history"])
