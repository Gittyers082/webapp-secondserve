"""Smoke tests that run without a database."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_me_requires_login():
    assert client.get("/api/me").status_code == 401


def test_create_listing_requires_login():
    assert client.post("/api/listings", json={}).status_code == 401


def test_openapi_lists_core_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/api/me", "/api/listings", "/api/orders", "/api/admin/approvals"):
        assert path in paths
