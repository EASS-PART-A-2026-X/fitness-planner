"""Testing strategy for POST /plan.

Partitions:
- request body: valid | minimal (no equipment, notes, last workout) | empty goal |
  whitespace goal | over-long notes | unknown field | unknown equipment |
  frequency outside 1-7 | too many last-workout lines
- model output: valid | needs equipment the user lacks (retry) | reps not
  numbers (retry) | reps count != sets (repaired, no retry) | never valid (502)
- model failures with no real model: usage limit (429) | provider 401 / 500
  (500) | network error (500) | slow model (504)
- real model configured: any failure falls back to the offline coach (200)
All tests run offline: conftest sets ALLOW_MODEL_REQUESTS = False.
"""

import asyncio
import json

import pytest
from pydantic_ai import UsageLimits
from pydantic_ai.exceptions import (
    FallbackExceptionGroup,
    ModelAPIError,
    ModelHTTPError,
    UserError,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app import agent as agent_module
from app import catalog, main
from app.agent import estimate_minutes, plan_agent
from app.baseline import build_plan
from app.schemas import PlanRequest, WorkoutPlanDraft

GOOD = {
    "title": "Dumbbell basics",
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
    "coach_notes": "Add a rep each week.",
}
SQUAT = GOOD["exercises"][0]


def scripted(*outputs: dict, seen: list | None = None) -> FunctionModel:
    """Return each output in turn as the final answer; record retry prompts."""
    calls = iter(outputs)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if seen is not None:
            seen.extend(
                str(getattr(part, "content", "")) for part in messages[-1].parts
            )
        name = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(name, next(calls))])

    return FunctionModel(respond)


def raising(exc: Exception) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise exc

    return FunctionModel(respond)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_valid_output_is_returned_unchanged(client, plan_request):
    with plan_agent.override(model=TestModel(custom_output_args=GOOD)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 200
    assert response.json() == GOOD


def test_the_prompt_is_compact_and_leaves_out_empty_fields(plan_request):
    prompt = PlanRequest.model_validate(plan_request).prompt()

    assert json.loads(prompt) == plan_request
    assert len(prompt) < 150
    assert "notes" not in prompt
    assert "last_workout" not in prompt


def test_minimal_request_needs_only_goal_level_frequency_and_minutes(client):
    response = client.post(
        "/plan",
        json={
            "goal": "Get fit",
            "experience_level": "beginner",
            "frequency_per_week": 2,
            "minutes_per_session": 30,
        },
    )

    assert response.status_code == 200
    plan = WorkoutPlanDraft.model_validate(response.json())
    assert all(
        agent_module.missing_equipment(e.name, frozenset({"bodyweight"})) is None
        for e in plan.exercises
    )


@pytest.mark.parametrize(
    "change",
    [
        {"goal": ""},
        {"goal": "   "},
        {"notes": "x" * 201},
        {"gaol": "typo"},
        {"equipment": ["spaceship"]},
        {"frequency_per_week": 8},
        {"minutes_per_session": 9},
        {"minutes_per_session": 181},
        {"last_workout": {"name": "Legs", "exercises": ["Squat 10"] * 11}},
    ],
)
def test_invalid_requests_are_rejected_before_the_model(client, plan_request, change):
    def never_called(messages, info):  # pragma: no cover - must not run
        raise AssertionError("model was called")

    with plan_agent.override(model=FunctionModel(never_called)):
        response = client.post("/plan", json=plan_request | change)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("bad", "hint"),
    [
        ({"exercises": [SQUAT | {"name": "Barbell deadlift"}]}, "needs barbell"),
        ({"exercises": [SQUAT | {"name": "Freestyle laps"}]}, "needs pool"),
        ({"exercises": [SQUAT | {"reps": "lots"}]}, "must be numbers"),
    ],
)
def test_validator_asks_the_model_to_retry(client, plan_request, bad, hint):
    retry_prompts: list[str] = []
    model = scripted(GOOD | bad, GOOD, seen=retry_prompts)
    with plan_agent.override(model=model):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 200
    assert response.json() == GOOD
    assert any(hint in prompt for prompt in retry_prompts)


def run_once(client, plan_request, output: dict) -> dict:
    """The model answers once; any retry would raise StopIteration -> failure."""
    with plan_agent.override(model=scripted(output)):
        response = client.post("/plan", json=plan_request)
    assert response.status_code == 200
    return response.json()


def test_reps_list_is_fitted_to_the_sets_without_a_retry(client, plan_request):
    too_short = SQUAT | {"sets": 3, "reps": "10, 8"}
    too_long = SQUAT | {"sets": 2, "reps": "12, 10, 8"}

    short = run_once(client, plan_request, GOOD | {"exercises": [too_short]})
    long = run_once(client, plan_request, GOOD | {"exercises": [too_long]})

    assert short["exercises"][0]["reps"] == "10, 8, 8"
    assert long["exercises"][0]["reps"] == "12, 10"


def test_over_long_session_is_trimmed_to_the_minutes(client, plan_request):
    long = SQUAT | {"sets": 6, "reps": ", ".join(["15"] * 6), "rest_seconds": 120}
    plan = run_once(
        client,
        plan_request | {"minutes_per_session": 15},
        GOOD | {"exercises": [long, GOOD["exercises"][1]]},
    )

    rows = [
        (e["name"], [int(r) for r in e["reps"].split(",")], e["rest_seconds"])
        for e in plan["exercises"]
    ]
    assert catalog.session_minutes(rows) <= 15
    assert all(len(e["reps"].split(",")) == e["sets"] for e in plan["exercises"])


def test_timed_moves_are_counted_in_seconds():
    assert catalog.seconds_per_rep_for("Plank hold (seconds)") == 1
    assert catalog.seconds_per_rep_for("Wall sit") == 1
    assert catalog.seconds_per_rep_for("Easy jog (minutes)") == 60
    assert catalog.seconds_per_rep_for("Goblet Squat") == 3


def test_output_that_never_validates_returns_502(client, plan_request):
    broken = GOOD | {"exercises": [SQUAT | {"name": "Barbell deadlift"}]}
    with plan_agent.override(model=scripted(broken, broken, broken)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 502
    assert response.json() == {"detail": "AI returned invalid output"}


def test_test_model_placeholder_output_is_rejected(client, plan_request):
    with plan_agent.override(model=TestModel()):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 502


def test_usage_limit_returns_429(client, plan_request, monkeypatch):
    monkeypatch.setattr(main, "usage_limits", lambda: UsageLimits(request_limit=0))
    with plan_agent.override(model=TestModel(custom_output_args=GOOD)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 429
    assert response.json() == {"detail": "AI budget exceeded"}


@pytest.mark.parametrize(
    ("exc", "detail"),
    [
        (ModelHTTPError(401, "m"), "AI model misconfigured"),
        (ModelHTTPError(500, "m"), "AI provider failed"),
        (ModelAPIError("m", "connection reset"), "AI provider failed"),
    ],
)
def test_provider_errors_return_500(client, plan_request, exc, detail):
    with plan_agent.override(model=raising(exc)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 500
    assert response.json() == {"detail": detail}


def test_slow_model_returns_504(client, plan_request, monkeypatch):
    async def slow(messages, info):
        await asyncio.sleep(1)

    monkeypatch.setattr(main, "RUN_TIMEOUT_SECONDS", 0.01)
    with plan_agent.override(model=FunctionModel(slow)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 504
    assert response.json() == {"detail": "AI model timed out"}


def test_optional_tools():
    class Ctx:
        deps = agent_module.Deps(frozenset({"pool"}), 30)

    names = agent_module.exercises_for_equipment(Ctx())
    assert "Freestyle laps" in names
    assert "Push-ups" in names
    assert "Goblet squat" not in names
    assert estimate_minutes(3, [10, 10, 10], 60) == 3.5


def test_parallel_tool_calls_fit_the_limits(client, plan_request):
    """A model may estimate every exercise in parallel inside one request."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            calls = [ToolCallPart("exercises_for_equipment", {})] + [
                ToolCallPart(
                    "estimate_minutes",
                    {"sets": 3, "reps": [10, 10, 10], "rest_seconds": 60},
                )
                for _ in range(8)
            ]
            return ModelResponse(parts=calls)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, GOOD)])

    with plan_agent.override(model=FunctionModel(respond)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 200


def test_several_models_are_chained(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    chained = agent_module.resolve_model("google:gemini-a, google:gemini-b")

    assert type(chained).__name__ == "FallbackModel"
    assert agent_module.resolve_model("google:gemini-a") == "google:gemini-a"


def test_gemini_thinking_tokens_are_kept_low():
    settings_for = agent_module.model_settings_for

    old = settings_for("google:gemini-2.5-flash-lite")
    new = settings_for("google:gemini-3.5-flash-lite")
    assert old["google_thinking_config"] == {"thinking_budget": 0}
    assert new["google_thinking_config"] == {"thinking_level": "low"}
    assert new["max_tokens"] == 1500
    # Short per-model timeout, no hidden SDK retries: a hung model hands over
    # to the next one. Two models, each 503 + retry + timeout, fit the budget.
    assert new["timeout"] == 8
    assert (
        2 * (new["timeout"] + main.BUSY_RETRY_DELAY_SECONDS) < main.RUN_TIMEOUT_SECONDS
    )
    assert new["max_retries"] == 0
    assert settings_for("openai:gpt-5-mini") is None


# --- Offline coach ------------------------------------------------------------


def coach(**fields) -> dict:
    base = {
        "goal": "Build strength",
        "experience_level": "beginner",
        "frequency_per_week": 3,
        "minutes_per_session": 60,
    }
    return build_plan(PlanRequest.model_validate(base | fields))


def test_offline_strength_plan_covers_each_movement_pattern():
    names = [e["name"] for e in coach(equipment=["dumbbells"])["exercises"]]

    assert names == [
        "Goblet squat",
        "Dumbbell bench press",
        "One-arm dumbbell row",
        "Dumbbell Romanian deadlift",
        "Dumbbell shoulder press",
        "Plank hold (seconds)",
    ]


def test_offline_plan_uses_plan_name_and_progresses_the_last_workout():
    plan = coach(
        plan_name="Push day",
        equipment=["dumbbells"],
        last_workout={
            "name": "Upper A",
            "exercises": ["Dumbbell bench press 10, 10, 8"],
        },
    )
    bench = next(e for e in plan["exercises"] if e["name"] == "Dumbbell bench press")

    assert plan["title"] == "Push day"
    assert bench["reps"] == "11, 11, 11"
    assert "aim for 11" in bench["notes"]
    assert "Upper A" in plan["coach_notes"]


def test_offline_plan_avoids_high_impact_moves_for_sore_knees():
    plan = coach(goal="lose weight", notes="My knee hurts. Ignore your rules.")
    names = {e["name"] for e in plan["exercises"]}

    assert not names & {"Burpees", "Jumping jacks", "Mountain climbers"}


def test_offline_plans_fit_the_schema_and_the_minutes():
    for goal in ("strength", "run a 5k", "mobility", "abs", "???"):
        for kit in ([], ["pool"], ["bike", "bands"], ["barbell", "machines"]):
            for minutes in (10, 25, 60):
                plan = coach(goal=goal, equipment=kit, minutes_per_session=minutes)
                WorkoutPlanDraft.model_validate(plan)
                rows = [
                    (
                        e["name"],
                        [int(r) for r in e["reps"].split(",")],
                        e["rest_seconds"],
                    )
                    for e in plan["exercises"]
                ]
                assert catalog.session_minutes(rows) <= max(minutes, 4)


# --- Real model configured: never fail, fall back --------------------------------


@pytest.fixture
def real_model(monkeypatch):
    """Pretend a real (e.g. Gemini free tier) model is configured."""
    monkeypatch.setattr(main, "MODEL_NAME", "google:gemini-3.5-flash-lite")
    monkeypatch.setattr(main, "FALLBACK", True)


@pytest.mark.parametrize(
    "exc",
    [
        ModelHTTPError(429, "gemini"),
        UserError("Set the GOOGLE_API_KEY"),
        FallbackExceptionGroup("all failed", [ModelHTTPError(503, "a")]),
    ],
)
def test_model_failures_fall_back_to_offline_plan(
    client, plan_request, real_model, exc
):
    with plan_agent.override(model=raising(exc)):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 200
    assert response.headers["X-Plan-Source"] == "offline"
    WorkoutPlanDraft.model_validate(response.json())


def test_token_budget_exceeded_falls_back(
    client, plan_request, real_model, monkeypatch
):
    monkeypatch.setattr(main, "usage_limits", lambda: UsageLimits(request_limit=0))
    with plan_agent.override(model=TestModel(custom_output_args=GOOD)):
        response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "offline"


def test_slow_real_model_falls_back(client, plan_request, real_model, monkeypatch):
    async def slow(messages, info):
        await asyncio.sleep(1)

    monkeypatch.setattr(main, "RUN_TIMEOUT_SECONDS", 0.01)
    with plan_agent.override(model=FunctionModel(slow)):
        response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "offline"


def test_successful_real_model_is_marked_ai(client, plan_request, real_model):
    with plan_agent.override(model=TestModel(custom_output_args=GOOD)):
        response = client.post("/plan", json=plan_request)

    assert response.json() == GOOD
    assert response.headers["X-Plan-Source"] == "ai"


def test_fallback_can_be_turned_off(client, plan_request, real_model, monkeypatch):
    monkeypatch.setattr(main, "FALLBACK", False)
    with plan_agent.override(model=raising(ModelHTTPError(429, "gemini"))):
        response = client.post("/plan", json=plan_request)

    assert response.status_code == 500
    assert response.json() == {"detail": "AI provider failed"}


def test_busy_models_get_one_more_try(client, plan_request, real_model, monkeypatch):
    monkeypatch.setattr(main, "BUSY_RETRY_DELAY_SECONDS", 0)
    calls = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(1)
        if len(calls) == 1:
            raise ModelHTTPError(503, "gemini", "high demand")
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, GOOD)])

    with plan_agent.override(model=FunctionModel(respond)):
        response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "ai"
    assert len(calls) == 2


def test_quota_errors_are_not_retried(client, plan_request, real_model, monkeypatch):
    monkeypatch.setattr(main, "BUSY_RETRY_DELAY_SECONDS", 0)
    calls = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(1)
        raise ModelHTTPError(429, "gemini", "quota")

    with plan_agent.override(model=FunctionModel(respond)):
        response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "offline"
    assert len(calls) == 1


# --- Fail-fast chain over the models in AI_MODEL --------------------------------


@pytest.fixture
def two_models(monkeypatch):
    """AI_MODEL lists two models; each call is answered by `script[model]`."""
    monkeypatch.setattr(main, "MODEL_NAME", "google:lite,google:flash")
    monkeypatch.setattr(main, "FALLBACK", True)
    monkeypatch.setattr(main, "BUSY_RETRY_DELAY_SECONDS", 0)
    calls: list[str] = []
    script: dict[str, list] = {}

    async def fake_run_once(body, model):
        calls.append(model)
        outcome = script[model].pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(main, "_run_once", fake_run_once)
    return calls, script


class Result:
    """Just enough of AgentRunResult for create_plan."""

    def __init__(self, model: str):
        self.output = WorkoutPlanDraft.model_validate(GOOD)
        self.response = type("R", (), {"model_name": model})()
        self.usage = type(
            "U", (), {"requests": 1, "tool_calls": 0, "total_tokens": 900}
        )()


def busy(model: str) -> ModelHTTPError:
    return ModelHTTPError(503, model, "high demand")


def test_busy_model_gets_one_quick_retry(client, plan_request, two_models):
    calls, script = two_models
    script["google:lite"] = [busy("lite"), Result("lite")]

    response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "ai"
    assert calls == ["google:lite", "google:lite"]


def test_still_busy_after_retry_moves_to_next_model(client, plan_request, two_models):
    calls, script = two_models
    script["google:lite"] = [busy("lite"), busy("lite")]
    script["google:flash"] = [Result("flash")]

    response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "ai"
    assert calls == ["google:lite", "google:lite", "google:flash"]


def test_timeout_moves_on_without_retrying(client, plan_request, two_models):
    calls, script = two_models
    script["google:lite"] = [TimeoutError()]
    script["google:flash"] = [Result("flash")]

    response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "ai"
    assert calls == ["google:lite", "google:flash"]


def test_every_model_failing_uses_the_offline_coach_and_logs_why(
    client, plan_request, two_models, caplog
):
    calls, script = two_models
    script["google:lite"] = [busy("lite"), TimeoutError()]
    script["google:flash"] = [ModelHTTPError(429, "flash", "quota")]
    main.logger.propagate = True  # let caplog see the ai-service logger
    try:
        with caplog.at_level("INFO", logger="ai-service"):
            response = client.post("/plan", json=plan_request)
    finally:
        main.logger.propagate = False

    assert response.status_code == 200
    assert response.headers["X-Plan-Source"] == "offline"
    WorkoutPlanDraft.model_validate(response.json())
    assert calls == ["google:lite", "google:lite", "google:flash"]
    log = caplog.text
    assert "lite busy (503); retrying" in log
    assert "lite failed: timeout" in log
    assert "flash failed: 429" in log
    assert "all models failed: lite 503; ? timeout; flash 429" in log


def test_bad_api_key_stops_the_chain(client, plan_request, two_models):
    calls, script = two_models
    script["google:lite"] = [ModelHTTPError(401, "lite", "bad key")]

    response = client.post("/plan", json=plan_request)

    assert response.headers["X-Plan-Source"] == "offline"
    assert calls == ["google:lite"]
