"""Shared fixtures for the AppTest suites (test_app.py, test_analytics.py)."""

import httpx
import pytest
import respx

import fitness_planner_api as api
from ui import analytics


@pytest.fixture(autouse=True)
def no_real_analytics(monkeypatch, tmp_path):
    """Tests must never send events to the real PostHog project in .env."""
    real_client = analytics._client  # tests may swap in a fake; clear the real cache
    monkeypatch.setenv("POSTHOG_API_KEY", "")
    monkeypatch.setattr(analytics, "ENV_FILE", tmp_path / "no.env")
    real_client.clear()
    yield
    real_client.clear()


@pytest.fixture
def backend():
    """The backend, mocked at the HTTP boundary; tests add the routes they need.

    test_api.py defines its own `backend`, which takes precedence there.
    """
    with respx.mock(base_url=api.BACKEND_URL, assert_all_called=False) as mock:
        mock.get("/auth/me").mock(
            return_value=httpx.Response(200, json={"id": 4, "username": "tester"})
        )
        mock.get("/workouts/recent-completions").mock(
            return_value=httpx.Response(200, json=[])
        )
        yield mock
