"""A deterministic, rule-based coach wrapped as a Pydantic AI ``FunctionModel``.

It is the default model (``AI_MODEL=test``), the fallback when a real model is
unavailable, and the baseline the evals compare models with. It builds a
balanced routine slot by slot (squat, push, pull, hinge, ...), choosing the
best exercise the user's equipment allows, and progresses from the last workout.
"""

import json
import re

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.catalog import (
    CATALOG_BY_NAME,
    CatalogEntry,
    Focus,
    goal_focus,
    session_minutes,
)
from app.schemas import PlanRequest

# Each slot lists exercises from best to fallback; the first one the user's
# equipment allows is used. Bodyweight options always come last.
SLOTS: dict[Focus, list[tuple[str, list[str]]]] = {
    "strength": [
        (
            "squat",
            ["Barbell back squat", "Goblet squat", "Leg press", "Bodyweight squats"],
        ),
        (
            "push",
            [
                "Barbell bench press",
                "Dumbbell bench press",
                "Chest press machine",
                "Push-ups",
            ],
        ),
        (
            "pull",
            [
                "Barbell bent-over row",
                "One-arm dumbbell row",
                "Seated cable row",
                "Banded rows",
                "Lat pulldown",
            ],
        ),
        (
            "hinge",
            [
                "Barbell deadlift",
                "Dumbbell Romanian deadlift",
                "Kettlebell swings",
                "Glute bridges",
            ],
        ),
        (
            "press",
            [
                "Barbell overhead press",
                "Dumbbell shoulder press",
                "Kettlebell clean and press",
                "Reverse lunges",
            ],
        ),
        ("core", ["Pallof press", "Plank hold (seconds)", "Dead bugs"]),
    ],
    "cardio": [
        (
            "engine",
            [
                "Freestyle laps",
                "Rowing machine intervals (seconds)",
                "Bike sprint intervals (seconds)",
                "Kettlebell swings",
                "Fast step-ups",
            ],
        ),
        ("legs", ["Goblet squat", "Reverse lunges", "Bodyweight squats"]),
        (
            "conditioning",
            [
                "Dumbbell thrusters",
                "Mountain climbers",
                "Jumping jacks",
                "Burpees",
                "Fast step-ups",
            ],
        ),
        (
            "engine2",
            [
                "Kickboard laps",
                "Steady bike ride (minutes)",
                "Banded lateral walks",
                "Glute bridges",
            ],
        ),
        ("core", ["Plank hold (seconds)", "Dead bugs"]),
    ],
    "mobility": [
        ("open", ["World's greatest stretch"]),
        ("spine", ["Cat-cow"]),
        ("shoulders", ["Band pull-aparts", "Downward dog to cobra"]),
        ("hips", ["Hip flexor stretch (seconds)"]),
        ("stability", ["Bird dogs", "Glute bridges"]),
    ],
    "core": [
        ("anti-extension", ["Dead bugs", "Plank hold (seconds)"]),
        ("anti-rotation", ["Pallof press", "Bird dogs"]),
        ("full-body", ["Turkish get-up", "Mountain climbers", "Bird dogs"]),
        ("hold", ["Plank hold (seconds)", "Dead bugs"]),
        ("hips", ["Glute bridges"]),
    ],
}
CUES = {
    "squat": "Sit down between your heels; knees track over toes.",
    "push": "Ribs down, lower with control, press smoothly.",
    "pull": "Lead with the elbow and squeeze the shoulder blade.",
    "hinge": "Hips back, flat back, feel the hamstrings stretch.",
    "press": "Squeeze glutes and press straight up, no back arch.",
    "core": "Brace like you're about to be poked in the belly.",
    "legs": "Stay tall and push through the whole foot.",
    "engine": "Hard but controlled; keep breathing steadily.",
    "engine2": "Easy pace: this is your recovery effort.",
    "conditioning": "Smooth reps beat fast sloppy ones.",
}
ICONS: dict[Focus, str] = {
    "strength": "weights",
    "cardio": "running",
    "mobility": "yoga",
    "core": "boxing",
}
JOINT_WORDS = ("knee", "joint", "ankle", "injur", "pain", "low impact", "hurt")


def _latest_request(messages: list[ModelMessage]) -> PlanRequest:
    for message in reversed(messages):
        if not isinstance(message, ModelRequest):
            continue
        for part in message.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return PlanRequest.model_validate(json.loads(part.content))
    raise ValueError("No training request in the conversation.")


def _allowed(entry: CatalogEntry, equipment: set[str], avoid_impact: bool) -> bool:
    has_gear = entry.equipment == "bodyweight" or entry.equipment in equipment
    return has_gear and not (avoid_impact and entry.high_impact)


def _last_reps(request: PlanRequest) -> dict[str, list[int]]:
    """'Goblet squat 12, 12, 10' -> {'goblet squat': [12, 12, 10]}."""
    if request.last_workout is None:
        return {}
    done = {}
    for line in request.last_workout.exercises:
        match = re.match(r"\s*(.*?)[\s:·-]*([\d,\s]+)$", line)
        if match and match.group(1):
            done[match.group(1).casefold()] = [
                int(value) for value in re.findall(r"\d+", match.group(2))
            ]
    return done


def _dose(entry: CatalogEntry, level: str) -> tuple[int, int, int]:
    """(sets, reps per set, rest seconds) for this exercise and level."""
    beginner, advanced = "begin" in level, "advan" in level
    sets = 2 if entry.focus == "mobility" else 4 if advanced else 3
    if entry.seconds_per_rep >= 60:  # minutes-based (steady ride)
        return 1, 10 if beginner else 15, 0
    if entry.seconds_per_rep >= 45:  # pool laps
        return sets, 4 if beginner else 6, 45
    if entry.seconds_per_rep >= 20:  # Turkish get-up
        return sets, 2, 60
    if entry.seconds_per_rep == 1:  # timed holds and intervals
        return sets, 30 if beginner else 45, 30
    reps = 8 if advanced and entry.focus == "strength" else 12 if beginner else 10
    rest = {"strength": 120 if advanced else 90, "cardio": 45, "core": 45}.get(
        entry.focus, 20
    )
    return sets, reps, rest


def build_plan(request: PlanRequest) -> dict:
    level = request.experience_level.casefold()
    focus = goal_focus(request.goal) or "strength"
    equipment = set(request.equipment) or {"bodyweight"}
    avoid_impact = any(word in request.notes.casefold() for word in JOINT_WORDS)
    last = _last_reps(request)

    exercises, used = [], set()
    for slot, names in SLOTS[focus]:
        for name in names:
            entry = CATALOG_BY_NAME[name.casefold()]
            if name in used or not _allowed(entry, equipment, avoid_impact):
                continue
            sets, reps, rest = _dose(entry, level)
            cue = CUES.get(slot, "Slow breaths; move only in a pain-free range.")
            previous = last.get(name.casefold())
            if previous and entry.seconds_per_rep < 20:
                reps = max(previous) + 1
                cue = f"Last time {max(previous)}: aim for {reps}."
            planned = [(e["name"], e["_reps"], e["rest_seconds"]) for e in exercises]
            # Only add it if the session still fits in the user's minutes.
            if session_minutes(planned + [(name, [reps] * sets, rest)]) > (
                request.minutes_per_session
            ):
                continue
            exercises.append(
                {
                    "name": name,
                    "sets": sets,
                    "reps": ", ".join([str(reps)] * sets),
                    "rest_seconds": rest,
                    "notes": cue,
                    "_reps": [reps] * sets,
                }
            )
            used.add(name)
            break
    for exercise in exercises:
        del exercise["_reps"]
    if not exercises:  # very short sessions: one easy bodyweight move
        exercises.append(
            {
                "name": "Bodyweight squats",
                "sets": 1,
                "reps": "10",
                "rest_seconds": 0,
                "notes": CUES["squat"],
            }
        )

    icon = ICONS[focus]
    if focus == "cardio" and "pool" in equipment:
        icon = "swimming"
    elif focus == "cardio" and "bike" in equipment:
        icon = "cycling"
    goal = request.goal.rstrip(".!")
    title = request.plan_name or f"{goal[:1].upper()}{goal[1:]} plan"
    progress = (
        f"It builds on {request.last_workout.name}. "
        if request.last_workout is not None
        else ""
    )
    return {
        "title": title[:60],
        "icon": icon,
        "exercises": exercises,
        "coach_notes": (
            f"{request.frequency_per_week} days a week, about "
            f"{request.minutes_per_session} minutes each. {progress}When every set feels easy, add a rep or a "
            "little weight."
        )[:200],
    }


def baseline_function(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    plan = build_plan(_latest_request(messages))
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, plan)])


def baseline_model() -> FunctionModel:
    return FunctionModel(baseline_function, model_name="baseline")
