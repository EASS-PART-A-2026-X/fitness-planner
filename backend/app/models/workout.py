from sqlmodel import SQLModel, Field
from typing import Optional

class WorkoutPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)  # Changed to int
    title: str = Field(index=True)
    goal: str
    frequency_per_week: int = Field(ge=1, le=7)
    experience_level: str
    exercises: str

class WorkoutPlanCreate(SQLModel):
    user_id: int  # Changed to int
    title: str
    goal: str
    frequency_per_week: int = Field(ge=1, le=7)
    experience_level: str
    exercises: str

class WorkoutPlanUpdate(SQLModel):
    title: Optional[str] = None
    goal: Optional[str] = None
    frequency_per_week: Optional[int] = Field(default=None, ge=1, le=7)
    experience_level: Optional[str] = None
    exercises: Optional[str] = None