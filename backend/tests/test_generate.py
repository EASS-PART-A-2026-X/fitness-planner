"""Testing strategy for the AI routes (POST /workouts/generate and /{id}/generate).

Partitions:
- user input: valid | empty goal | whitespace goal | unknown field |
  unknown equipment | frequency/minutes out of range | long notes  -> 422, zero AI calls
- AI transport: answers | connection refused | read timeout (retried)
- AI status: 200 | 503/504 (retried) | 500 / 429 (no retry) -> 503 |
  502 / other 4xx -> 502
- AI body: valid | not JSON | wrong shape | breaks our plan limits -> 502
- ownership: own plan | another user's plan (404, no AI call)
All AI traffic goes through httpx.MockTransport: no network needed.
"""

import json

import httpx
import pytest

from app.ai_client import TIMEOUT

BODY = {
    "goal": "Build strength",
    "experience_level": "beginner",
    "frequency_per_week": 3,
    "minutes_per_session": 45,
    "equipment": ["dumbbells"],
    "notes": "Short sessions please",
}
DRAFT = {
    "title": "Dumbbell strength",
    "icon": "weights",
    "exercises": [
        {
            "name": "Goblet squat",
            "sets": 3,
            "reps": "10, 10, 8",
            "rest_seconds": 60,
            "notes": "Sit tall.",
        },
        {
            "name": "Push-ups",
            "sets": 2,
            "reps": "8, 8",
            "rest_seconds": 45,
            "notes": "",
        },
    ],
    "coach_notes": "Add one rep per week.",
}
UNAVAILABLE = {"detail": "AI service unavailable"}
BAD_OUTPUT = {"detail": "AI service returned invalid output"}


def answer(payload=DRAFT, status_code=200):
    return lambda request: httpx.Response(status_code, json=payload)


def test_generate_stores_the_plan_and_returns_coach_notes(
    authenticated_client, fake_ai
):
    calls = fake_ai(answer())

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "Dumbbell strength"
    assert created["emoji"] == "weights"
    assert created["goal"] == "Build strength"
    assert created["coach_notes"] == "Add one rep per week."
    assert created["exercises"][0] == DRAFT["exercises"][0]
    assert "notes" not in created["exercises"][1]
    stored = authenticated_client.get(f"/workouts/{created['id']}").json()
    assert stored["exercises"] == created["exercises"]
    # Only non-empty fields are sent, to keep the AI request small.
    assert json.loads(calls[0].content) == BODY


def test_minimal_request_and_plan_name_becomes_the_title(authenticated_client, fake_ai):
    calls = fake_ai(answer())
    body = {"plan_name": "Leg day", "goal": "Legs", "experience_level": "beginner"}

    response = authenticated_client.post(
        "/workouts/generate",
        json=body | {"frequency_per_week": 2, "minutes_per_session": 30},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Leg day"
    assert response.json()["frequency_per_week"] == 2
    assert "equipment" not in json.loads(calls[0].content)


def test_generate_sends_the_last_workout_to_the_ai(authenticated_client, fake_ai):
    workout = authenticated_client.post(
        "/workouts",
        json={"title": "Old", "exercises": [{"exercise": "Squats", "count": 12}]},
    ).json()
    authenticated_client.post(f"/workouts/{workout['id']}/complete")
    calls = fake_ai(answer())

    authenticated_client.post("/workouts/generate", json=BODY)

    assert json.loads(calls[0].content)["last_workout"] == {
        "name": "Old",
        "exercises": ["Squats 12"],
    }


@pytest.mark.parametrize(
    "change",
    [
        {"goal": ""},
        {"goal": "   "},
        {"golf": "typo"},
        {"equipment": ["spaceship"]},
        {"frequency_per_week": 0},
        {"minutes_per_session": 5},
        {"notes": "x" * 201},
    ],
)
def test_invalid_input_never_calls_the_ai(authenticated_client, fake_ai, change):
    calls = fake_ai(answer())

    response = authenticated_client.post("/workouts/generate", json=BODY | change)

    assert response.status_code == 422
    assert calls == []


def test_ai_down_returns_503_and_saves_nothing(authenticated_client, fake_ai):
    def refused(request):
        raise httpx.ConnectError("connection refused", request=request)

    calls = fake_ai(refused)

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert len(calls) == 3  # one try plus two retries
    assert authenticated_client.get("/workouts").json() == []


def test_read_timeout_is_retried_then_503(authenticated_client, fake_ai):
    def slow(request):
        raise httpx.ReadTimeout("no answer", request=request)

    calls = fake_ai(slow)

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 503
    assert len(calls) == 3


def test_transient_504_then_success(authenticated_client, fake_ai):
    responses = iter([httpx.Response(504), httpx.Response(200, json=DRAFT)])
    calls = fake_ai(lambda request: next(responses))

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 201
    assert len(calls) == 2


@pytest.mark.parametrize("code", [500, 429])
def test_ai_failure_status_is_503_without_retry(authenticated_client, fake_ai, code):
    calls = fake_ai(answer({"detail": "boom"}, code))

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 503
    assert response.json() == UNAVAILABLE
    assert len(calls) == 1


@pytest.mark.parametrize("code", [502, 422, 404])
def test_ai_bad_output_status_is_502(authenticated_client, fake_ai, code):
    calls = fake_ai(answer({"detail": "nope"}, code))

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 502
    assert response.json() == BAD_OUTPUT
    assert len(calls) == 1


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(200, text="<html>not json</html>"),
        answer({"title": "Missing everything"}),
        answer(DRAFT | {"icon": "rocket"}),
        answer(DRAFT | {"title": "x" * 201}),
    ],
)
def test_broken_contract_returns_502(authenticated_client, fake_ai, handler):
    fake_ai(handler)

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 502
    assert response.json() == BAD_OUTPUT
    assert authenticated_client.get("/workouts").json() == []


def test_regenerate_replaces_exercises_of_own_plan(authenticated_client, fake_ai):
    workout = authenticated_client.post(
        "/workouts",
        json={
            "title": "Mine",
            "goal": "Strength",
            "frequency_per_week": 3,
            "exercises": [{"exercise": "Squats", "count": 12}],
        },
    ).json()
    calls = fake_ai(answer())

    response = authenticated_client.post(
        f"/workouts/{workout['id']}/generate",
        json={"equipment": ["dumbbells"], "minutes_per_session": 40},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Mine"
    assert response.json()["exercises"][0]["name"] == "Goblet squat"
    sent = json.loads(calls[0].content)
    assert sent["plan_name"] == "Mine"
    assert sent["frequency_per_week"] == 3
    assert sent["minutes_per_session"] == 40


def test_regenerate_unknown_plan_is_404_without_ai_call(authenticated_client, fake_ai):
    calls = fake_ai(answer())

    response = authenticated_client.post(
        "/workouts/999/generate",
        json={"minutes_per_session": 30},
    )

    assert response.status_code == 404
    assert calls == []


def test_generate_requires_login(client, fake_ai):
    assert client.post("/workouts/generate", json=BODY).status_code == 401


def test_client_has_explicit_timeouts():
    assert (TIMEOUT.connect, TIMEOUT.write, TIMEOUT.read, TIMEOUT.pool) == (
        2.0,
        5.0,
        30.0,
        2.0,
    )


def test_backup_plan_is_marked_offline(authenticated_client, fake_ai):
    fake_ai(
        lambda request: httpx.Response(
            200, json=DRAFT, headers={"X-Plan-Source": "offline"}
        )
    )

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.status_code == 201
    assert response.json()["plan_source"] == "offline"


def test_ai_plan_is_marked_ai(authenticated_client, fake_ai):
    fake_ai(answer())

    response = authenticated_client.post("/workouts/generate", json=BODY)

    assert response.json()["plan_source"] == "ai"
