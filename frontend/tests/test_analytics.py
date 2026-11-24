"""PostHog analytics: off without a key, the right events, and no personal data."""

import json

import httpx
import pytest
from test_app import WORKOUT, open_create, start_app

from ui import analytics


class FakePosthog:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.events: list[tuple[str, str, dict]] = []

    def capture(self, event, *, distinct_id, properties):
        self.events.append((event, distinct_id, properties))

    def shutdown(self):
        pass

    def names(self) -> list[str]:
        return [event for event, _, _ in self.events]


@pytest.fixture
def posthog(monkeypatch) -> FakePosthog:
    fake = FakePosthog()
    monkeypatch.setattr(analytics, "_client", lambda: fake)
    return fake


def test_analytics_is_off_without_a_key(monkeypatch):
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    analytics._client.clear()

    assert not analytics.enabled()
    analytics.capture("anything")  # no client, no error


def test_key_is_read_from_the_env_file_for_local_runs(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("POSTHOG_API_KEY=phc_from_file\n")
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    monkeypatch.setattr(analytics, "ENV_FILE", env_file)
    monkeypatch.setattr(analytics, "Posthog", FakePosthog)
    analytics._client.clear()

    assert analytics._client().args == ("phc_from_file",)


def test_client_uses_key_and_host_from_the_environment(monkeypatch):
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://eu.i.posthog.com")
    monkeypatch.setattr(analytics, "Posthog", FakePosthog)
    analytics._client.clear()
    try:
        client = analytics._client()
        assert client.args == ("phc_test",)
        assert client.kwargs == {"host": "https://eu.i.posthog.com"}
    finally:
        analytics._client.clear()


def test_capture_errors_never_break_the_app(monkeypatch):
    class Broken(FakePosthog):
        def capture(self, *args, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(analytics, "_client", lambda: Broken())
    monkeypatch.setattr(analytics, "distinct_id", lambda: "user-1")

    analytics.capture("plan_created")  # swallowed and logged


def test_page_views_are_sent_once_per_page(backend, posthog):
    at = start_app(backend, [WORKOUT])
    at.run()  # a rerun of the same page is not a new page view
    at.button(key="top-nav-plans").click().run()

    pages = [
        props["page"] for event, _, props in posthog.events if event == "$pageview"
    ]
    assert pages == ["home", "plans"]


def test_create_flow_events_carry_no_personal_data(backend, posthog):
    backend.post("/workouts").mock(
        return_value=httpx.Response(201, json=WORKOUT | {"id": 8, "title": "Legs"})
    )
    at = open_create(backend, "lower")
    at.text_input(key="create-0-title").input("Secret leg plan")
    at.text_input(key="create-0-goal").input("My private goal")
    at.text_input(key="create-0-name-0").input("Squats")
    at.button(key="create-0-submit").click().run()

    assert "workout_type_selected" in posthog.names()
    created = next(
        props for event, _, props in posthog.events if event == "plan_created"
    )
    assert created["workout_type"] == "lower"
    assert created["used_ai"] is False
    assert created["exercise_count"] == 1
    sent = json.dumps(posthog.events)
    for private in ("tester", "Secret leg plan", "My private goal", "Squats"):
        assert private not in sent
    # Identified by the account id from /auth/me, never by the username.
    assert {who for _, who, _ in posthog.events} == {"user-4"}


def test_without_an_account_id_the_username_is_hashed():
    assert analytics.distinct_id_for("tester").startswith("user-")
    assert "tester" not in analytics.distinct_id_for("tester")


def test_delete_is_tracked_with_its_source(backend, posthog):
    backend.delete("/workouts/7").mock(return_value=httpx.Response(204))
    at = start_app(backend, [WORKOUT])
    at.button(key="top-nav-plans").click().run()
    at.button(key="delete-workout-7").click().run()
    at.button(key="plans-7-confirm-delete").click().run()

    deleted = next(
        props for event, _, props in posthog.events if event == "plan_deleted"
    )
    assert deleted["source"] == "plans"
    assert deleted["workout_type"] == "running"
