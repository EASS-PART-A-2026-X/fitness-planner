from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class WorkoutPlanBase(SQLModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=100)
    frequency_per_week: int = Field(ge=1, le=7)
    experience_level: str = Field(min_length=1, max_length=50)
    exercises: str = Field(max_length=5000)


class WorkoutPlan(WorkoutPlanBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


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
    exercises: str | None = Field(default=None, max_length=5000)


class WorkoutPlanPublic(WorkoutPlanBase):
    id: int
