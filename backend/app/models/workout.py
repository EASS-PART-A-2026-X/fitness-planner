from typing import Annotated, Literal

from pydantic import AliasChoices, ConfigDict, model_validator
from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class WorkoutExercise(SQLModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exercise: str | None = Field(default=None, min_length=1, max_length=200)
    count: int | None = Field(default=None, ge=1, le=10000)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sets: int | None = Field(default=None, ge=1, le=100)
    reps: str | None = Field(default=None, min_length=1, max_length=1000)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    notes: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_exercise_shape(self):
        if self.exercise is not None or self.count is not None:
            if self.exercise is None or self.count is None:
                raise ValueError("Legacy exercises require exercise and count.")
            if any(
                value is not None
                for value in (
                    self.name,
                    self.sets,
                    self.reps,
                    self.rest_seconds,
                    self.notes,
                )
            ):
                raise ValueError("Use either legacy or structured exercise fields.")
            return self
        if self.name is None or self.sets is None or self.reps is None:
            raise ValueError("Structured exercises require name, sets, and reps.")
        return self


class WorkoutPlanBase(SQLModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("title", "workout_name"),
    )
    goal: str = Field(default="General fitness", min_length=1, max_length=100)
    frequency_per_week: int = Field(default=3, ge=1, le=7)
    experience_level: str = Field(default="beginner", min_length=1, max_length=50)
    emoji: str = Field(default="🏋️", min_length=1, max_length=8)
    exercises: list[WorkoutExercise] = Field(
        min_length=1,
        max_length=100,
        sa_column=Column(JSON, nullable=False),
    )


class WorkoutPlan(WorkoutPlanBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(ge=1, index=True)
    exercises: list[dict[str, str | int]] = Field(
        sa_column=Column(JSON, nullable=False),
    )
    emoji: str = Field(default="🏋️", max_length=8)


class WorkoutPlanCreate(WorkoutPlanBase):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class WorkoutPlanUpdate(SQLModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = Field(default=None, min_length=1, max_length=100)
    frequency_per_week: int | None = Field(default=None, ge=1, le=7)
    experience_level: str | None = Field(default=None, min_length=1, max_length=50)
    emoji: str | None = Field(default=None, min_length=1, max_length=8)
    exercises: list[WorkoutExercise] | None = Field(
        min_length=1,
        default=None,
        max_length=100,
        sa_column=Column(JSON, nullable=True),
    )


class WorkoutPlanPublic(WorkoutPlanBase):
    id: int


class WorkoutOverviewPublic(WorkoutPlanPublic):
    completed_this_week: int
    week_start: str
    has_unfinished_workout: bool


class WorkoutCompletion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(ge=1, index=True)
    workout_id: int = Field(foreign_key="workoutplan.id", index=True)
    completed_on: str = Field(index=True)
    checked_exercises: list[dict[str, str | int]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )


class WorkoutSession(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "workout_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(ge=1, index=True)
    workout_id: int = Field(foreign_key="workoutplan.id", index=True)
    checked_exercises: list[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    completed_sets: list[dict[str, int]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )


class CompletedSet(SQLModel):
    model_config = ConfigDict(extra="forbid")

    exercise_index: Annotated[int, Field(ge=0, lt=100)]
    set_index: Annotated[int, Field(ge=0, lt=100)]
    actual_reps: Annotated[int, Field(ge=0, le=10000)]


class WorkoutSessionUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    checked_exercises: list[Annotated[int, Field(ge=0, lt=100)]] = Field(
        default_factory=list, max_length=100
    )
    completed_sets: list[CompletedSet] | None = Field(default=None, max_length=10000)


class WorkoutSessionPublic(SQLModel):
    is_active: bool = False
    checked_exercises: list[int]
    completed_sets: list[CompletedSet] | None = None


class WorkoutCompletionCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    completed_sets: list[CompletedSet] = Field(max_length=10000)


class RecentWorkoutPublic(SQLModel):
    completed_on: str
    workout_name: str
    checked_exercises: list[WorkoutExercise]


class WorkoutProgressPublic(SQLModel):
    completed_this_week: int
    frequency_per_week: int
    week_start: str


class WorkoutHistoryWeekPublic(SQLModel):
    week_start: str
    completed_sessions: int
    weekly_target: int


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


class RegenerateExercisesRequest(SQLModel):
    """What the AI coach needs on top of an existing plan's details.

    Kept small on purpose: everything here is sent to the model.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    minutes_per_session: int = Field(ge=10, le=180)
    equipment: list[Equipment] = Field(default_factory=list, max_length=8)
    notes: str = Field(default="", max_length=200)


class GeneratePlanRequest(RegenerateExercisesRequest):
    plan_name: str = Field(default="", max_length=60)
    goal: str = Field(min_length=1, max_length=100)
    experience_level: str = Field(min_length=1, max_length=30)
    frequency_per_week: int = Field(ge=1, le=7)


class GeneratedWorkoutPublic(WorkoutPlanPublic):
    coach_notes: str = ""
    # "ai", or "offline" when the AI was busy and the local backup coach answered.
    plan_source: Literal["ai", "offline"] = "ai"
