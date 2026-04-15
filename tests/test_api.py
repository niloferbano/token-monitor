from fastapi.testclient import TestClient

from app.core.api import quota_manager
from app.main import app

API_HEADERS = {"X-API-Key": "dev-secret-key"}


def setup_function() -> None:
    quota_manager.tenants.clear()
    quota_manager.seen_requests.clear()


def test_register_tenant_and_check_quota() -> None:
    client = TestClient(app)

    register_response = client.post(
        "/quota/tenants",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "budget_tokens": 10,
            "window_seconds": 60,
        },
    )
    assert register_response.status_code == 201
    assert register_response.json() == {
        "tenant_id": "tenant-a",
        "budget_tokens": 10,
        "window_seconds": 60,
    }

    check_response = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "requested_tokens": 4,
            "now_sec": 100,
        },
    )
    assert check_response.status_code == 200
    assert check_response.json() == {
        "tenant_id": "tenant-a",
        "request_id": "req-1",
        "allowed": True,
        "deduplicated": False,
        "used_tokens": 4,
        "remaining_tokens": 6,
        "budget_tokens": 10,
        "window_seconds": 60,
        "reason": None,
    }


def test_check_quota_returns_429_when_budget_exceeded() -> None:
    client = TestClient(app)
    client.post(
        "/quota/tenants",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "budget_tokens": 5,
            "window_seconds": 60,
        },
    )

    allowed_response = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "requested_tokens": 3,
            "now_sec": 100,
        },
    )
    rejected_response = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-2",
            "requested_tokens": 3,
            "now_sec": 101,
        },
    )

    assert allowed_response.status_code == 200
    assert rejected_response.status_code == 429
    assert rejected_response.json() == {"detail": "Budget exceeded"}


def test_check_quota_returns_404_for_unknown_tenant() -> None:
    client = TestClient(app)

    response = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "missing-tenant",
            "request_id": "req-1",
            "requested_tokens": 3,
            "now_sec": 100,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tenant not found"}


def test_duplicate_request_returns_deduplicated_response() -> None:
    client = TestClient(app)
    client.post(
        "/quota/tenants",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "budget_tokens": 10,
            "window_seconds": 60,
        },
    )

    first = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "requested_tokens": 4,
            "now_sec": 100,
        },
    )
    duplicate = client.post(
        "/quota/check",
        headers=API_HEADERS,
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "requested_tokens": 4,
            "now_sec": 100,
        },
    )

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["deduplicated"] is True


def test_check_quota_returns_401_for_invalid_api_key() -> None:
    client = TestClient(app)

    response = client.post(
        "/quota/check",
        headers={"X-API-Key": "wrong-key"},
        json={
            "tenant_id": "tenant-a",
            "request_id": "req-1",
            "requested_tokens": 3,
            "now_sec": 100,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
