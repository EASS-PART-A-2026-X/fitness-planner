"""A deterministic, rule-based planner wrapped as a Pydantic AI ``FunctionModel``.

It is the default model (``AI_MODEL=test``), so the whole stack works offline
with no API key, and it doubles as the baseline the evals compare models with.
"""

import json

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.catalog import (
    WARM_UP_MINUTES,
    CatalogEntry,
    Focus,
    available_exercises,
    estimate_minutes,
    goal_focus,
)
from app.schemas import PlanRequest

ICONS: dict[Focus, str] = {
    "strength": "weights",
    "cardio": "running",
    "mobility": "yoga",
    "core": "boxing",
}
REST: dict[Focus, int] = {"strength": 90, "cardio": 30, "mobility": 15, "core": 45}
CUES: dict[Focus, str] = {
    "strength": "Controlled tempo; stop 1-2 reps before failure.",
    "cardio": "Keep a pace you could hold a short conversation at.",
    "mobility": "Breathe slowly and move only through a pain-free range.",
    "core": "Brace your ribs down and keep your lower back neutral.",
}
TITLES: dict[Focus, str] = {
    "strength": "Full-body strength",
    "cardio": "Cardio engine",
    "mobility": "Mobility flow",
    "core": "Core control",
}
JOINT_WORDS = ("knee", "joint", "ankle", "injur", "pain", "low impact")


def _latest_request(messages: list[ModelMessage]) -> PlanRequest:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return PlanRequest.model_validate(json.loads(part.content))
    raise ValueError("No training request in the conversation.")


def _rep_target(entry: CatalogEntry, level: str) -> int:
    if entry.seconds_per_rep >= 45:
        return 4 if "begin" in level else 6
    if entry.seconds_per_rep == 1:
        return 30 if "begin" in level else 45
    if entry.seconds_per_rep >= 20:
        return 2
    return 10 if "begin" in level else 12


def _history_names(request: PlanRequest) -> set[str]:
    return {
        exercise.name.casefold()
        for item in request.recent_history
        for exercise in item.exercises
    }


def build_plan(request: PlanRequest) -> dict:
    """Pick catalog moves for the goal and fit them into the minute budget."""
    level = request.experience_level.casefold()
    focus = goal_focus(request.goal) or "strength"
    avoid_impact = any(word in request.notes.casefold() for word in JOINT_WORDS)
    options = [
        entry
        for entry in available_exercises(frozenset(request.equipment))
        if not (avoid_impact and entry.high_impact)
    ]
    # Prefer gear the user brought, then bodyweight, so the plan uses the kit.
    options.sort(key=lambda entry: entry.equipment == "bodyweight")
    primary = [entry for entry in options if entry.focus == focus]
    support = [
        entry
        for kind in ("core", "mobility")
        if kind != focus
        for entry in options
        if entry.focus == kind
    ][:2]

    sets = 2 if "begin" in level else 4 if "advan" in level else 3
    done_before = _history_names(request)
    budget = request.minutes_per_session - WARM_UP_MINUTES
    exercises: list[dict] = []
    used = 0.0
    for entry in primary[:5] + support:
        rest = REST[entry.focus] + (
            30 if "advan" in level and focus == "strength" else 0
        )
        target = _rep_target(entry, level)
        if entry.name.casefold() in done_before and entry.seconds_per_rep < 20:
            target += 1
        reps = [target] * sets
        minutes = estimate_minutes(sets, reps, rest, entry.seconds_per_rep)
        if used + minutes > budget:
            continue
        used += minutes
        cue = CUES[entry.focus]
        if entry.name.casefold() in done_before:
            cue = "One more rep than last time. " + cue
        exercises.append(
            {
                "name": entry.name,
                "sets": sets,
                "reps": ", ".join(str(value) for value in reps),
                "rest_seconds": rest,
                "notes": cue,
            }
        )
        if len(exercises) == 6:
            break
    if not exercises:
        entry = options[0]
        exercises.append(
            {"name": entry.name, "sets": 1, "reps": "10", "rest_seconds": 0}
        )

    icon = ICONS[focus]
    if focus == "cardio" and "pool" in request.equipment:
        icon = "swimming"
    elif focus == "cardio" and "bike" in request.equipment:
        icon = "cycling"
    title = request.plan_name or TITLES[focus]
    return {
        "title": title[:200],
        "icon": icon,
        "frequency_per_week": request.days_per_week,
        "exercises": exercises,
        "coach_notes": (
            f"Train {request.days_per_week}x per week, about "
            f"{round(used) + WARM_UP_MINUTES} minutes including a short warm-up. "
            "Add one rep per set when every set feels comfortable."
        ),
    }


def baseline_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    plan = build_plan(_latest_request(messages))
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, plan)])


def baseline_model() -> FunctionModel:
    return FunctionModel(baseline_function, model_name="baseline")
