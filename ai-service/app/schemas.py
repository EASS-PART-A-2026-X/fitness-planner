"""Request and output contracts for the AI coach.

Both sides are kept deliberately small: every field here is sent to (or
written by) the model on every request, and the free tier is metered in
requests and tokens. The ai-service owns these schemas; the backend keeps its
own copy in ``backend/app/ai_client.py`` and a contract test compares them.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Equipment = Literal[
    "bodyweight",
    "dumbbells",
    "barbell",
    "kettlebell",
    "bands",
    "machines",
    "bike",
    "pool",
]
Icon = Literal["weights", "running", "cycling", "yoga", "swimming", "boxing"]


class LastWorkout(BaseModel):
    """The most recent completed workout, so the coach can progress from it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    # Short lines such as "Goblet squat 12, 12, 10".
    exercises: list[str] = Field(default_factory=list, max_length=10)


class PlanRequest(BaseModel):
    """A user's training request. Every field is data, never an instruction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    plan_name: str = Field(default="", max_length=60)
    goal: str = Field(min_length=1, max_length=100)
    experience_level: str = Field(min_length=1, max_length=30)
    frequency_per_week: int = Field(ge=1, le=7)
    minutes_per_session: int = Field(ge=10, le=180)
    equipment: list[Equipment] = Field(default_factory=list, max_length=8)
    last_workout: LastWorkout | None = None
    notes: str = Field(default="", max_length=200)

    def prompt(self) -> str:
        """Compact JSON for the model: empty optional fields are left out."""
        return self.model_dump_json(exclude_defaults=True)


class PlannedExercise(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    sets: int = Field(ge=1, le=10)
    reps: str = Field(
        min_length=1, max_length=60, description="One number per set, e.g. '10, 10, 8'"
    )
    rest_seconds: int = Field(ge=0, le=300)
    notes: str = Field(default="", max_length=80, description="Short coaching cue")


class WorkoutPlanDraft(BaseModel):
    """One routine the user repeats on each training day."""

    title: str = Field(min_length=1, max_length=60)
    icon: Icon
    exercises: list[PlannedExercise] = Field(min_length=1, max_length=8)
    coach_notes: str = Field(default="", max_length=200)
