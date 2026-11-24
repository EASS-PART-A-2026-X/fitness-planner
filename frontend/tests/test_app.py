"""AppTest suite: the real page script with HTTP mocked at the boundary (respx).

Testing strategy: every screen has loading, empty, error and content states;
writes show success only after the backend confirms; AI failures (503/502)
show a sentence and keep the user's input.
"""

import ast
import json
from pathlib import Path

import httpx
import pytest
import respx
from streamlit.testing.v1 import AppTest

import fitness_planner_api as api

FRONTEND = Path(__file__).parents[1]
APP = FRONTEND / "streamlit_app.py"
TOKEN = "test-token"
COOKIE_NAME = "fitness_planner_session"
WORKOUT = {
    "id": 7,
    "emoji": "running",
    "title": "Full Body",
    "goal": "General fitness",
    "frequency_per_week": 3,
    "experience_level": "beginner",
    "exercises": [
        {"exercise": "Squats", "count": 12},
        {"exercise": "Push-ups", "count": 10},
    ],
}
PROGRESS = {
    "completed_this_week": 1,
    "frequency_per_week": 3,
    "week_start": "2026-11-23",
}
HISTORY = [
    {"week_start": "2026-11-16", "completed_sessions": 2, "weekly_target": 3},
    {"week_start": "2026-11-23", "completed_sessions": 1, "weekly_target": 3},
]


@pytest.fixture
def backend():
    with respx.mock(base_url=api.BACKEND_URL, assert_all_called=False) as mock:
        mock.get("/auth/me").mock(
            return_value=httpx.Response(200, json={"id": 4, "username": "tester"})
        )
        mock.get("/workouts/recent-completions").mock(
            return_value=httpx.Response(200, json=[])
        )
        yield mock


def start_app(
    backend,
    workouts: list[dict] | None = None,
    unfinished_ids: set[int] = frozenset(),
    history: list[dict] | None = None,
) -> AppTest:
    if workouts is not None:
        overview = [
            workout
            | {
                "completed_this_week": PROGRESS["completed_this_week"],
                "week_start": PROGRESS["week_start"],
                "has_unfinished_workout": workout["id"] in unfinished_ids,
            }
            for workout in workouts
        ]
        backend.get("/workouts/overview").mock(
            return_value=httpx.Response(200, json=overview)
        )
    backend.get("/workouts/progress/history").mock(
        return_value=httpx.Response(200, json=history or [])
    )
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["access_token"] = TOKEN
    at.session_state["username"] = "tester"
    return at.run()


def set_workout_detail(backend, workout=WORKOUT, completed_sets=None, active=False):
    backend.get(f"/workouts/{workout['id']}").mock(
        return_value=httpx.Response(200, json=workout)
    )
    backend.get(f"/workouts/{workout['id']}/progress").mock(
        return_value=httpx.Response(200, json=PROGRESS)
    )
    session = {"is_active": active, "checked_exercises": []}
    if completed_sets is not None:
        session["completed_sets"] = completed_sets
    backend.get(f"/workouts/{workout['id']}/session").mock(
        return_value=httpx.Response(200, json=session)
    )
    backend.post(f"/workouts/{workout['id']}/session/start").mock(
        return_value=httpx.Response(200, json=session | {"is_active": True})
    )


def markdown_text(at: AppTest) -> str:
    return "\n".join(item.value for item in at.markdown)


# --- Architecture ------------------------------------------------------------


def test_only_the_api_module_talks_http_or_databases():
    forbidden = {"httpx", "requests", "sqlmodel", "sqlite3", "sqlalchemy"}
    for path in [APP, *(FRONTEND / "ui").rglob("*.py")]:
        tree = ast.parse(path.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported & forbidden, path


def test_light_theme_mascot_and_mobile_styles_are_configured():
    theme = (FRONTEND / "ui" / "theme.py").read_text()
    config = (FRONTEND / ".streamlit" / "config.toml").read_text()

    assert "--primary: #10B981" in theme
    assert "--bg: #F8FAFC" in theme
    assert "@media (max-width: 760px)" in theme
    assert "prefers-reduced-motion: reduce" in theme
    assert 'base = "light"' in config
    assert "gatherUsageStats = false" in config


# --- Auth --------------------------------------------------------------------


def test_page_requires_login_or_account_creation(backend):
    at = AppTest.from_file(str(APP), default_timeout=30).run()

    assert [tab.label for tab in at.tabs] == ["Log in", "Create account"]
    assert any("private to your account" in item.value for item in at.caption)
    assert not backend.get("/workouts/overview").called


def test_registration_opens_the_dashboard_and_saves_the_cookie(backend):
    backend.post("/auth/register").mock(
        return_value=httpx.Response(
            201,
            json={
                "access_token": TOKEN,
                "token_type": "bearer",
                "expires_in": 2592000,
                "user": {"id": 4, "username": "new-user"},
            },
        )
    )
    backend.get("/workouts/overview").mock(return_value=httpx.Response(200, json=[]))
    backend.get("/workouts/progress/history").mock(
        return_value=httpx.Response(200, json=[])
    )
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["fitness-planner-cookies"] = {}
    at.run()
    at.text_input(key="register-username").input("new-user")
    at.text_input(key="register-password").input("a-secure-password")

    at.button(key="FormSubmitter:register-form-Create account").click().run()

    assert at.button(key="logout")
    assert at.button(key="empty-create-workout")
    assert at.session_state["username"] == "new-user"
    assert at.session_state["fitness-planner-cookies"][COOKIE_NAME] == TOKEN


def test_saved_browser_session_is_validated_and_restored(backend):
    at = AppTest.from_file(str(APP), default_timeout=30)
    backend.get("/workouts/overview").mock(
        return_value=httpx.Response(
            200,
            json=[
                WORKOUT
                | {
                    "completed_this_week": 1,
                    "week_start": "2026-11-23",
                    "has_unfinished_workout": False,
                }
            ],
        )
    )
    backend.get("/workouts/progress/history").mock(
        return_value=httpx.Response(200, json=[])
    )
    at.session_state["fitness-planner-cookies"] = {COOKIE_NAME: TOKEN}

    at.run()

    assert at.session_state["access_token"] == TOKEN
    assert at.button(key="open-workout-7")


def test_logout_revokes_and_removes_the_saved_session(backend):
    at = start_app(backend, [])
    at.session_state["fitness-planner-cookies"] = {COOKIE_NAME: TOKEN}
    revoke = backend.delete("/auth/session").mock(return_value=httpx.Response(204))

    at.button(key="logout").click().run()

    assert revoke.called
    assert COOKIE_NAME not in at.session_state["fitness-planner-cookies"]
    assert [tab.label for tab in at.tabs] == ["Log in", "Create account"]


def test_expired_saved_session_is_removed(backend):
    backend.get("/auth/me").mock(
        return_value=httpx.Response(401, json={"detail": "Authentication required."})
    )
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["fitness-planner-cookies"] = {COOKIE_NAME: TOKEN}

    at.run()

    assert COOKIE_NAME not in at.session_state["fitness-planner-cookies"]
    assert any("saved login expired" in item.value for item in at.info)


# --- Dashboard ---------------------------------------------------------------


def test_dashboard_empty_state_offers_ai_and_manual_paths(backend):
    at = start_app(backend, [])

    assert "Your first workout starts here" in markdown_text(at)
    assert at.button(key="empty-coach")
    assert at.button(key="empty-create-workout")


def test_dashboard_shows_plans_progress_and_stats(backend):
    at = start_app(backend, [WORKOUT], history=HISTORY)
    text = markdown_text(at)

    assert at.button(key="open-workout-7").label == "Open"
    assert "Full Body" in text
    assert "1 of 3 sessions this week" in text
    assert 'aria-valuenow="33"' in text
    assert "Welcome back" in text


def test_unfinished_workout_offers_resume(backend):
    at = start_app(backend, [WORKOUT], unfinished_ids={7})

    assert at.button(key="open-workout-7").label == "Resume"
    assert "Finish your workout!" in markdown_text(at)


def test_backend_down_shows_next_step_without_traceback(backend):
    backend.get("/workouts/overview").mock(side_effect=httpx.ConnectError("refused"))

    at = start_app(backend)

    assert not at.exception
    assert "Start it (docker compose up)" in at.error[0].value
    assert any("reload this page" in item.value for item in at.info)


def test_user_text_is_escaped_in_html(backend):
    at = start_app(backend, [WORKOUT | {"title": "<script>alert(1)</script>"}])

    text = markdown_text(at)
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


# --- Analytics & activity ----------------------------------------------------


def test_analytics_shows_chart_and_streak(backend):
    at = start_app(backend, [WORKOUT], history=HISTORY)
    at.button(key="top-nav-analytics").click().run()

    assert any("Training progress" in item.value for item in at.subheader)
    assert "Streak" in markdown_text(at)
    assert not at.exception


def test_activity_page_lists_recent_sessions(backend):
    at = start_app(backend, [WORKOUT])
    backend.get("/workouts/recent-completions").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "completed_on": "2026-11-20",
                    "workout_name": "Full Body",
                    "checked_exercises": [
                        {"name": "Squats", "sets": 2, "reps": "9, 8"}
                    ],
                }
            ],
        )
    )
    at.button(key="top-nav-activities").click().run()

    assert "Squats · 9, 8" in markdown_text(at)


# --- AI coach ----------------------------------------------------------------

GENERATED = WORKOUT | {
    "id": 9,
    "title": "Dumbbell strength",
    "emoji": "weights",
    "exercises": [
        {
            "name": "Goblet squat",
            "sets": 3,
            "reps": "10, 10, 8",
            "rest_seconds": 60,
            "notes": "Sit tall.",
        }
    ],
    "coach_notes": "Add a rep each week.",
}


def open_coach(backend) -> AppTest:
    at = start_app(backend, [WORKOUT])
    at.button(key="top-nav-coach").click().run()
    at.text_input(key="coach-goal").input("Build strength")
    at.multiselect(key="coach-equipment").select("dumbbells")
    at.text_area(key="coach-notes").input("Short sessions")
    return at


def test_coach_sends_the_request_and_shows_the_saved_plan(backend):
    route = backend.post("/workouts/generate").mock(
        return_value=httpx.Response(201, json=GENERATED)
    )
    at = open_coach(backend)

    at.button(key="coach-submit").click().run()

    assert json.loads(route.calls[0].request.content) == {
        "goal": "Build strength",
        "experience_level": "beginner",
        "equipment": ["bodyweight", "dumbbells"],
        "days_per_week": 3,
        "minutes_per_session": 45,
        "notes": "Short sessions",
    }
    text = markdown_text(at)
    assert "Dumbbell strength" in text
    assert "Add a rep each week." in text
    assert "Goblet squat" in text
    assert at.button(key="coach-open")


@pytest.mark.parametrize(
    ("status", "message"),
    [(503, "AI coach is unavailable"), (502, "could not use")],
)
def test_coach_failures_show_a_sentence_and_keep_input(backend, status, message):
    backend.post("/workouts/generate").mock(
        return_value=httpx.Response(status, json={"detail": "x"})
    )
    at = open_coach(backend)

    at.button(key="coach-submit").click().run()

    assert message in at.error[0].value
    assert at.text_input(key="coach-goal").value == "Build strength"
    assert at.text_area(key="coach-notes").value == "Short sessions"
    assert not at.exception


def test_coach_requires_a_goal_before_calling_the_backend(backend):
    route = backend.post("/workouts/generate")
    at = start_app(backend, [WORKOUT])
    at.button(key="top-nav-coach").click().run()

    at.button(key="coach-submit").click().run()

    assert not route.called
    assert "Tell the coach your goal" in at.warning[0].value


def test_plan_page_regenerates_exercises_with_ai(backend):
    set_workout_detail(backend)
    route = backend.post("/workouts/7/generate").mock(
        return_value=httpx.Response(
            200, json=GENERATED | {"id": 7, "title": "Full Body"}
        )
    )
    at = start_app(backend, [WORKOUT])
    at.button(key="open-workout-7").click().run()

    at.button(key="plan-7-generate-exercises").click().run()

    assert json.loads(route.calls[0].request.content) == {
        "equipment": ["bodyweight"],
        "minutes_per_session": 45,
        "notes": "",
    }
    assert any("Updated Full Body" in item.value for item in at.success)


# --- Create / edit / delete --------------------------------------------------


def test_create_plan_sends_structured_exercises_and_shows_success(backend):
    at = start_app(backend, [])
    at.button(key="empty-create-workout").click().run()
    post = backend.post("/workouts").mock(
        return_value=httpx.Response(201, json=WORKOUT | {"id": 8, "title": "Strength"})
    )
    at.session_state["create-0-icon"] = "weights"

    at.text_input(key="create-0-title").input("Strength")
    at.text_input(key="create-0-goal").input("Build strength")
    at.text_input(key="create-0-experience").input("beginner")
    at.text_input(key="create-0-name-0").input("Deadlifts")
    at.number_input(key="create-0-sets-0").set_value(3)
    at.text_input(key="create-0-reps-0").input("8, 8, 6")
    at.number_input(key="create-0-rest-0").set_value(90)
    at.button(key="create-0-submit").click().run()

    assert json.loads(post.calls[0].request.content) == {
        "emoji": "weights",
        "title": "Strength",
        "goal": "Build strength",
        "frequency_per_week": 3,
        "experience_level": "beginner",
        "exercises": [
            {"name": "Deadlifts", "sets": 3, "reps": "8, 8, 6", "rest_seconds": 90}
        ],
    }
    assert any("Created Strength" in item.value for item in at.success)


def test_create_plan_can_add_exercise_rows(backend):
    at = start_app(backend, [])
    at.button(key="empty-create-workout").click().run()
    at.button(key="create-0-add-exercise").click().run()

    assert at.text_input(key="create-0-name-1")
    assert at.number_input(key="create-0-rest-1")


def test_missing_fields_are_caught_before_any_request(backend):
    at = start_app(backend, [])
    at.button(key="empty-create-workout").click().run()
    post = backend.post("/workouts")

    at.text_input(key="create-0-goal").input("Build strength")
    at.text_input(key="create-0-experience").input("beginner")
    at.button(key="create-0-submit").click().run()

    assert not post.called
    assert "Title is required" in at.warning[0].value
    assert "Exercise 1 needs a name" in at.warning[0].value


def test_backend_validation_error_is_shown_in_words(backend):
    at = start_app(backend, [])
    at.button(key="empty-create-workout").click().run()
    backend.post("/workouts").mock(
        return_value=httpx.Response(
            422, json={"detail": [{"loc": ["body", "title"], "msg": "too long"}]}
        )
    )
    at.text_input(key="create-0-title").input("Plan")
    at.text_input(key="create-0-goal").input("Goal")
    at.text_input(key="create-0-experience").input("beginner")
    at.text_input(key="create-0-name-0").input("Squats")
    at.button(key="create-0-submit").click().run()

    assert "Please fix: title: too long" in at.error[0].value


def test_legacy_plan_converts_to_structured_exercises_when_saved(backend):
    set_workout_detail(backend)
    at = start_app(backend, [WORKOUT])
    patch = backend.patch("/workouts/7").mock(
        return_value=httpx.Response(200, json=WORKOUT | {"title": "Updated"})
    )

    at.button(key="open-workout-7").click().run()
    at.button(key="edit-workout").click().run()
    assert at.text_input(key="edit-7-name-0").value == "Squats"
    assert at.text_input(key="edit-7-reps-0").value == "12"
    at.text_input(key="edit-7-title").input("Updated")
    at.button(key="edit-7-save").click().run()

    body = json.loads(patch.calls[0].request.content)
    assert body["title"] == "Updated"
    assert body["emoji"] == "running"
    assert body["exercises"] == [
        {"name": "Squats", "sets": 1, "reps": "12", "rest_seconds": 60},
        {"name": "Push-ups", "sets": 1, "reps": "10", "rest_seconds": 60},
    ]
    assert any("Saved Updated" in item.value for item in at.success)


def test_edit_preserves_ai_coaching_notes(backend):
    structured = WORKOUT | {"exercises": GENERATED["exercises"]}
    set_workout_detail(backend, workout=structured)
    patch = backend.patch("/workouts/7").mock(
        return_value=httpx.Response(200, json=structured)
    )
    at = start_app(backend, [structured])

    at.button(key="open-workout-7").click().run()
    at.button(key="edit-workout").click().run()
    at.button(key="edit-7-save").click().run()

    assert (
        json.loads(patch.calls[0].request.content)["exercises"]
        == (GENERATED["exercises"])
    )


def test_delete_requires_confirmation(backend):
    set_workout_detail(backend)
    at = start_app(backend, [WORKOUT])
    delete = backend.delete("/workouts/7").mock(return_value=httpx.Response(204))

    at.button(key="open-workout-7").click().run()
    at.button(key="edit-workout").click().run()
    at.button(key="edit-7-delete").click().run()
    assert not delete.called
    at.button(key="edit-7-confirm-delete").click().run()

    assert delete.called
    assert any("Deleted Full Body" in item.value for item in at.success)


# --- Live session ------------------------------------------------------------

STRUCTURED = WORKOUT | {
    "exercises": [{"name": "Push-ups", "sets": 2, "reps": "4, 4", "rest_seconds": 30}]
}


def test_session_saves_actual_reps_and_starts_rest_timer(backend):
    set_workout_detail(backend, workout=STRUCTURED, completed_sets=[])
    saved = [{"exercise_index": 0, "set_index": 0, "actual_reps": 3}]
    save = backend.put("/workouts/7/session").mock(
        return_value=httpx.Response(
            200, json={"checked_exercises": [], "completed_sets": saved}
        )
    )
    at = start_app(backend, [STRUCTURED])

    at.button(key="open-workout-7").click().run()
    at.button(key="start-workout").click().run()
    at.number_input(key="session-7-actual-0-0").set_value(3)
    at.button(key="session-7-complete-set").click().run()

    assert json.loads(save.calls[0].request.content) == {"completed_sets": saved}
    assert at.session_state["session-7-timer-mode"] == "rest"
    assert at.button(key="session-7-timer-mode-skip-rest")


def test_finish_workout_records_completion(backend):
    set_workout_detail(backend, completed_sets=[])
    complete = backend.post("/workouts/7/complete").mock(
        return_value=httpx.Response(201, json=PROGRESS | {"completed_this_week": 2})
    )
    at = start_app(backend, [WORKOUT])

    at.button(key="open-workout-7").click().run()
    at.button(key="start-workout").click().run()
    at.button(key="finish-workout").click().run()

    assert json.loads(complete.calls[0].request.content) == {"completed_sets": []}
    assert any("Workout complete!" in item.value for item in at.success)


def test_lost_reply_on_save_warns_it_may_have_been_saved(backend):
    set_workout_detail(backend, workout=STRUCTURED, completed_sets=[])
    backend.put("/workouts/7/session").mock(side_effect=httpx.ReadTimeout("slow"))
    at = start_app(backend, [STRUCTURED])

    at.button(key="open-workout-7").click().run()
    at.button(key="start-workout").click().run()
    at.button(key="session-7-complete-set").click().run()

    assert "may have been saved" in at.error[0].value
