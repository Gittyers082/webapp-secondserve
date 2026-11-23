"""The run-jobs endpoint's secret check (no database needed)."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def jobs_secret(monkeypatch):
    monkeypatch.setenv("JOBS_SECRET", "correct-horse-battery-staple")
    get_settings.cache_clear()
    yield "correct-horse-battery-staple"
    get_settings.cache_clear()


def test_run_jobs_is_off_without_a_secret():
    get_settings.cache_clear()
    assert client.post("/api/internal/run-jobs").status_code == 404


def test_run_jobs_rejects_a_missing_or_wrong_secret(jobs_secret):
    assert client.post("/api/internal/run-jobs").status_code == 404
    wrong = client.post("/api/internal/run-jobs", headers={"X-Jobs-Secret": "guess"})
    assert wrong.status_code == 404


def test_run_jobs_is_hidden_from_the_api_docs():
    assert "/api/internal/run-jobs" not in client.get("/openapi.json").json()["paths"]
