import json

import httpx
import pytest
import respx

import fitness_planner_api as api

TOKEN = "test-access-token"
WORKOUT = {
    "id": 3,
    "emoji": "🏋️",
    "title": "Full Body",
    "goal": "General fitness",
    "frequency_per_week": 3,
    "experience_level": "beginner",
    "exercises": [{"exercise": "Squats", "count": 12}],
}


@pytest.fixture
def backend():
    with respx.mock(base_url=api.BACKEND_URL, assert_all_called=False) as mock:
        yield mock


def test_login_returns_auth_session(backend):
    route = backend.post("/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": TOKEN,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {"id": 4, "username": "tamar"},
            },
        )
    )

    session = api.login("tamar", "a-secure-password")

    assert session["access_token"] == TOKEN
    assert route.calls[0].request.headers["content-type"] == "application/json"


def test_current_user_validates_a_saved_session(backend):
    route = backend.get("/auth/me").mock(
        return_value=httpx.Response(200, json={"id": 4, "username": "tamar"})
    )

    assert api.current_user(TOKEN) == {"id": 4, "username": "tamar"}
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


def test_list_workouts_sends_bearer_token_and_decodes_structured_exercises(backend):
    route = backend.get("/workouts").mock(
        return_value=httpx.Response(200, json=[WORKOUT])
    )

    assert api.list_workouts(TOKEN) == [WORKOUT]
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


def test_workout_overview_includes_progress_and_unfinished_status(backend):
    overview = {
        **WORKOUT,
        "completed_this_week": 2,
        "week_start": "2026-11-09",
        "has_unfinished_workout": True,
    }
    route = backend.get("/workouts/overview").mock(
        return_value=httpx.Response(200, json=[overview])
    )

    assert api.list_workout_overview(TOKEN) == [overview]
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


def test_create_sends_structured_exercise_array(backend):
    route = backend.post("/workouts").mock(
        return_value=httpx.Response(201, json=WORKOUT)
    )

    created = api.create_workout(
        TOKEN,
        {
            "emoji": "⚡",
            "title": "Full Body",
            "goal": "General fitness",
            "frequency_per_week": 3,
            "experience_level": "beginner",
            "exercises": [{"exercise": "Squats", "count": 12}],
        },
    )

    assert created == WORKOUT
    assert json.loads(route.calls[0].request.content)["emoji"] == "⚡"
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"
    assert json.loads(route.calls[0].request.content)["exercises"] == [
        {"exercise": "Squats", "count": 12}
    ]


def test_validation_error_is_translated_to_words(backend):
    backend.post("/workouts").mock(
        return_value=httpx.Response(
            422,
            json={
                "detail": [
                    {
                        "loc": ["body", "title"],
                        "msg": "String should have at least 1 character",
                    }
                ]
            },
        )
    )

    with pytest.raises(api.BackendError, match="Please fix: title:"):
        api.create_workout(TOKEN, {})


def test_cannot_connect_says_to_start_backend(backend):
    backend.get("/workouts").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(api.BackendUnavailable, match=r"Start it \(docker compose up\)"):
        api.list_workouts(TOKEN)


def test_lost_write_reply_warns_against_retrying(backend):
    backend.post("/workouts").mock(side_effect=httpx.ReadTimeout("timed out"))

    with pytest.raises(api.BackendNoAnswer, match="may have been saved"):
        api.create_workout(TOKEN, {})


def test_logout_revokes_the_token(backend):
    route = backend.delete("/auth/session").mock(return_value=httpx.Response(204))

    assert api.logout(TOKEN) is None
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


def test_progress_and_completion_use_authenticated_endpoints(backend):
    backend.get("/workouts/3/progress").mock(
        return_value=httpx.Response(
            200,
            json={
                "completed_this_week": 1,
                "frequency_per_week": 3,
                "week_start": "2026-11-09",
            },
        )
    )
    route = backend.post("/workouts/3/complete").mock(
        return_value=httpx.Response(
            201,
            json={
                "completed_this_week": 2,
                "frequency_per_week": 3,
                "week_start": "2026-11-09",
            },
        )
    )

    assert api.workout_progress(TOKEN, 3)["completed_this_week"] == 1
    assert api.complete_workout(TOKEN, 3)["completed_this_week"] == 2
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


def test_progress_history_requests_weekly_totals(backend):
    history = [
        {
            "week_start": "2026-11-09",
            "completed_sessions": 2,
            "weekly_target": 3,
        }
    ]
    route = backend.get("/workouts/progress/history").mock(
        return_value=httpx.Response(200, json=history)
    )

    assert api.workout_progress_history(TOKEN, weeks=1) == history
    assert route.calls[0].request.url.params["weeks"] == "1"


def test_recent_completions_returns_checked_exercise_history(backend):
    recent = [
        {
            "completed_on": "2026-11-13",
            "checked_exercises": [{"exercise": "Squats", "count": 12}],
        }
    ]
    route = backend.get("/workouts/recent-completions").mock(
        return_value=httpx.Response(200, json=recent)
    )

    assert api.recent_completions(TOKEN) == recent
    assert route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"


PLAN_REQUEST = {
    "goal": "Build strength",
    "experience_level": "beginner",
    "frequency_per_week": 3,
    "minutes_per_session": 45,
    "equipment": ["dumbbells"],
}


def test_generate_plan_posts_request_with_long_timeout(backend):
    route = backend.post("/workouts/generate").mock(
        return_value=httpx.Response(201, json=WORKOUT | {"coach_notes": "Go."})
    )

    created = api.generate_plan(TOKEN, PLAN_REQUEST)

    assert created["coach_notes"] == "Go."
    request = route.calls.last.request
    assert json.loads(request.content) == PLAN_REQUEST
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.extensions["timeout"]["read"] == 100.0
    assert request.extensions["timeout"]["connect"] == 2.0


def test_draft_plan_posts_request_with_long_timeout(backend):
    draft = {
        "title": "Run",
        "icon": "running",
        "exercises": WORKOUT["exercises"],
        "coach_notes": "Easy pace.",
    }
    route = backend.post("/workouts/draft").mock(
        return_value=httpx.Response(200, json=draft)
    )

    assert api.draft_plan(TOKEN, PLAN_REQUEST) == draft
    request = route.calls.last.request
    assert json.loads(request.content) == PLAN_REQUEST
    assert request.extensions["timeout"]["read"] == 100.0


@pytest.mark.parametrize(
    ("code", "error"), [(503, api.AIUnavailable), (502, api.AIBadOutput)]
)
def test_draft_plan_failures_are_typed(backend, code, error):
    backend.post("/workouts/draft").mock(
        return_value=httpx.Response(code, json={"detail": "x"})
    )

    with pytest.raises(error):
        api.draft_plan(TOKEN, PLAN_REQUEST)


def test_regenerate_exercises_targets_the_plan(backend):
    route = backend.post("/workouts/3/generate").mock(
        return_value=httpx.Response(200, json=WORKOUT | {"coach_notes": ""})
    )

    api.regenerate_exercises(TOKEN, 3, 20, ["bands"], "sore knee")
    api.regenerate_exercises(TOKEN, 3, 45)

    assert json.loads(route.calls[0].request.content) == {
        "minutes_per_session": 20,
        "equipment": ["bands"],
        "notes": "sore knee",
    }
    assert json.loads(route.calls[1].request.content) == {"minutes_per_session": 45}


@pytest.mark.parametrize(
    ("code", "error", "text"),
    [
        (503, api.AIUnavailable, "AI coach is unavailable"),
        (502, api.AIBadOutput, "could not use"),
    ],
)
def test_ai_failures_become_plain_sentences(backend, code, error, text):
    backend.post("/workouts/generate").mock(
        return_value=httpx.Response(code, json={"detail": "AI service unavailable"})
    )

    with pytest.raises(error, match=text):
        api.generate_plan(TOKEN, PLAN_REQUEST)


def test_non_api_server_is_reported(backend):
    backend.get("/workouts").mock(return_value=httpx.Response(200, text="<html>"))

    with pytest.raises(api.BackendError, match="did not answer like"):
        api.list_workouts(TOKEN)


def test_read_and_update_workout_session_use_authenticated_endpoints(backend):
    session = {"checked_exercises": [0]}
    get_route = backend.get("/workouts/3/session").mock(
        return_value=httpx.Response(200, json=session)
    )
    put_route = backend.put("/workouts/3/session").mock(
        return_value=httpx.Response(200, json=session)
    )

    assert api.read_workout_session(TOKEN, 3) == session
    assert api.update_workout_session(TOKEN, 3, [0]) == session
    assert get_route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"
    assert put_route.calls[0].request.headers["authorization"] == f"Bearer {TOKEN}"
    assert json.loads(put_route.calls[0].request.content) == {"checked_exercises": [0]}


def test_save_workout_session_persists_actual_repetitions(backend):
    completed_sets = [
        {"exercise_index": 0, "set_index": 1, "actual_reps": 3},
    ]
    route = backend.put("/workouts/3/session").mock(
        return_value=httpx.Response(
            200,
            json={"checked_exercises": [], "completed_sets": completed_sets},
        )
    )

    saved = api.save_workout_session(TOKEN, 3, completed_sets)

    assert saved["completed_sets"] == completed_sets
    assert json.loads(route.calls[0].request.content) == {
        "completed_sets": completed_sets
    }


def test_login_error_does_not_expose_backend_details(backend):
    backend.post("/auth/login").mock(
        return_value=httpx.Response(
            401,
            json={"detail": "Internal database message"},
        )
    )

    with pytest.raises(api.BackendError, match="Invalid username or password"):
        api.login("tamar", "wrong-password")
