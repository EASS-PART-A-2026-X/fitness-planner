"""HTTP client for the Fitness Planner backend: the only module that does HTTP."""

import os
from typing import Any, NotRequired, TypedDict

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)
# The backend may retry a slow AI service (worst case about 92 s), so wait longer.
AI_TIMEOUT = httpx.Timeout(100.0, connect=2.0)
EQUIPMENT = (
    "bodyweight",
    "dumbbells",
    "barbell",
    "kettlebell",
    "bands",
    "machines",
    "bike",
    "pool",
)


class Exercise(TypedDict):
    exercise: NotRequired[str]
    count: NotRequired[int]
    name: NotRequired[str]
    sets: NotRequired[int]
    reps: NotRequired[str]
    rest_seconds: NotRequired[int]
    notes: NotRequired[str]


class WorkoutPlan(TypedDict):
    id: int
    emoji: str
    title: str
    goal: str
    frequency_per_week: int
    experience_level: str
    exercises: list[Exercise]


class WorkoutPlanCreate(TypedDict):
    emoji: str
    title: str
    goal: str
    frequency_per_week: int
    experience_level: str
    exercises: list[Exercise]


class WorkoutProgress(TypedDict):
    completed_this_week: int
    frequency_per_week: int
    week_start: str


class WorkoutHistoryWeek(TypedDict):
    week_start: str
    completed_sessions: int
    weekly_target: int


class CompletedSet(TypedDict):
    exercise_index: int
    set_index: int
    actual_reps: int


class WorkoutOverview(WorkoutPlan):
    completed_this_week: int
    week_start: str
    has_unfinished_workout: bool


class WorkoutSessionState(TypedDict):
    is_active: NotRequired[bool]
    checked_exercises: list[int]
    completed_sets: NotRequired[list[CompletedSet]]


class RecentWorkout(TypedDict):
    completed_on: str
    workout_name: str
    checked_exercises: list[Exercise]


class PlanRequest(TypedDict):
    plan_name: NotRequired[str]
    goal: str
    experience_level: str
    frequency_per_week: int
    minutes_per_session: int
    equipment: NotRequired[list[str]]
    notes: NotRequired[str]


class GeneratedWorkout(WorkoutPlan):
    coach_notes: str
    # "offline" when the AI was busy and the local backup coach wrote the plan.
    plan_source: NotRequired[str]


class User(TypedDict):
    id: int
    username: str


class AuthSession(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    user: User


class BackendError(Exception):
    """A safe-to-display error returned by or encountered while calling the API."""


class BackendUnavailable(BackendError):
    """The request could not reach the backend."""


class BackendNoAnswer(BackendError):
    """A write may have reached the backend, but its outcome is unknown."""


class SessionExpired(BackendError):
    """The supplied bearer token is no longer valid."""


class AIUnavailable(BackendError):
    """The backend could not get an answer from the AI coach."""


class AIBadOutput(BackendError):
    """The AI coach answered with something the backend could not use."""


def _validation_message(detail: Any) -> str:
    if not isinstance(detail, list):
        return (
            "The backend rejected the submitted values. Check the form and try again."
        )

    messages = []
    for issue in detail:
        if not isinstance(issue, dict):
            continue
        location = issue.get("loc", [])
        field = location[-1] if isinstance(location, list) and location else "input"
        message = issue.get("msg", "is invalid")
        messages.append(f"{field}: {message}")

    if not messages:
        return (
            "The backend rejected the submitted values. Check the form and try again."
        )

    return "Please fix: " + "; ".join(messages)


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    timeout: httpx.Timeout = TIMEOUT,
    **kwargs: Any,
) -> Any:
    headers = kwargs.pop("headers", {})
    if token:
        headers = {**headers, "Authorization": f"Bearer {token}"}
    try:
        response = httpx.request(
            method,
            f"{BACKEND_URL}{path}",
            timeout=timeout,
            headers=headers,
            **kwargs,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise BackendUnavailable(
            f"Cannot reach the backend at {BACKEND_URL}. "
            "Start it (docker compose up) and reload the page."
        ) from exc
    except httpx.RequestError as exc:
        if method.upper() != "GET":
            raise BackendNoAnswer(
                "The backend did not answer after the change was sent. "
                "Your change may have been saved. Reload the page and check "
                "before trying again."
            ) from exc
        raise BackendUnavailable(
            "The backend did not answer. Check that it is running, then reload this page."
        ) from exc

    if response.status_code == 401:
        try:
            detail = response.json().get("detail", "")
        except ValueError, AttributeError:
            detail = ""
        if path == "/auth/login":
            raise BackendError("Invalid username or password.")
        if path == "/auth/register":
            raise BackendError(str(detail) or "Could not create the account.")
        raise SessionExpired("Your session expired. Log in again to continue.")
    if response.status_code == 409:
        raise BackendError("That username is already taken. Choose another one.")
    if response.status_code == 422:
        try:
            detail = response.json().get("detail")
        except ValueError, AttributeError:
            detail = None
        raise BackendError(_validation_message(detail))
    if response.status_code == 404:
        raise BackendError(
            "That workout plan no longer exists. Reload the page to see the current plans."
        )
    if response.status_code == 503 and path.endswith("/generate"):
        raise AIUnavailable(
            "The AI coach is unavailable right now. Your plans still work; "
            "try again in a minute."
        )
    if response.status_code == 502 and path.endswith("/generate"):
        raise AIBadOutput(
            "The AI coach returned a plan we could not use. "
            "Try again or adjust your request."
        )
    if response.is_error:
        raise BackendError(
            f"The backend returned an error ({response.status_code}). "
            "Check the backend logs, then reload the page."
        )
    if response.status_code == 204:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise BackendError(
            "The server did not answer like the Fitness Planner API. "
            "Check BACKEND_URL and reload."
        ) from exc


def register(username: str, password: str) -> AuthSession:
    return _request(
        "POST",
        "/auth/register",
        json={"username": username, "password": password},
    )


def login(username: str, password: str) -> AuthSession:
    return _request(
        "POST",
        "/auth/login",
        json={"username": username, "password": password},
    )


def logout(token: str) -> None:
    _request("DELETE", "/auth/session", token=token)


def current_user(token: str) -> User:
    return _request("GET", "/auth/me", token=token)


def list_workouts(token: str) -> list[WorkoutPlan]:
    return _request("GET", "/workouts", token=token)


def list_workout_overview(token: str) -> list[WorkoutOverview]:
    return _request("GET", "/workouts/overview", token=token)


def read_workout(token: str, workout_id: int) -> WorkoutPlan:
    return _request("GET", f"/workouts/{workout_id}", token=token)


def workout_progress(token: str, workout_id: int) -> WorkoutProgress:
    return _request("GET", f"/workouts/{workout_id}/progress", token=token)


def create_workout(token: str, workout: WorkoutPlanCreate) -> WorkoutPlan:
    return _request("POST", "/workouts", token=token, json=workout)


def update_workout(
    token: str,
    workout_id: int,
    workout: WorkoutPlanCreate,
) -> WorkoutPlan:
    return _request("PATCH", f"/workouts/{workout_id}", token=token, json=workout)


def delete_workout(token: str, workout_id: int) -> None:
    _request("DELETE", f"/workouts/{workout_id}", token=token)


def complete_workout(
    token: str,
    workout_id: int,
    completed_sets: list[CompletedSet] | None = None,
) -> WorkoutProgress:
    kwargs = (
        {"json": {"completed_sets": completed_sets}}
        if completed_sets is not None
        else {}
    )
    return _request("POST", f"/workouts/{workout_id}/complete", token=token, **kwargs)


def workout_progress_history(
    token: str,
    weeks: int = 12,
) -> list[WorkoutHistoryWeek]:
    return _request(
        "GET",
        "/workouts/progress/history",
        token=token,
        params={"weeks": weeks},
    )


def recent_completions(token: str) -> list[RecentWorkout]:
    return _request("GET", "/workouts/recent-completions", token=token)


def generate_plan(token: str, request: PlanRequest) -> GeneratedWorkout:
    """Ask the AI coach for a new plan; the backend stores it and returns it."""
    return _request(
        "POST", "/workouts/generate", token=token, json=request, timeout=AI_TIMEOUT
    )


def regenerate_exercises(
    token: str,
    workout_id: int,
    minutes_per_session: int,
    equipment: list[str] | None = None,
    notes: str = "",
) -> GeneratedWorkout:
    """Replace an existing plan's exercises with a fresh AI suggestion."""
    body: dict = {"minutes_per_session": minutes_per_session}
    if equipment:
        body["equipment"] = equipment
    if notes:
        body["notes"] = notes
    return _request(
        "POST",
        f"/workouts/{workout_id}/generate",
        token=token,
        json=body,
        timeout=AI_TIMEOUT,
    )


def read_workout_session(token: str, workout_id: int) -> WorkoutSessionState:
    return _request("GET", f"/workouts/{workout_id}/session", token=token)


def start_workout_session(token: str, workout_id: int) -> WorkoutSessionState:
    return _request("POST", f"/workouts/{workout_id}/session/start", token=token)


def cancel_workout_session(token: str, workout_id: int) -> None:
    _request("DELETE", f"/workouts/{workout_id}/session", token=token)


def update_workout_session(
    token: str,
    workout_id: int,
    checked_exercises: list[int],
) -> WorkoutSessionState:
    return _request(
        "PUT",
        f"/workouts/{workout_id}/session",
        token=token,
        json={"checked_exercises": checked_exercises},
    )


def save_workout_session(
    token: str,
    workout_id: int,
    completed_sets: list[CompletedSet],
) -> WorkoutSessionState:
    return _request(
        "PUT",
        f"/workouts/{workout_id}/session",
        token=token,
        json={"completed_sets": completed_sets},
    )
