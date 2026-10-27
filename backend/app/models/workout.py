from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class WorkoutPlan(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Title of the workout plan")
    goal: str = Field(..., min_length=1, max_length=100, description="Fitness goal (e.g., Weight loss, Muscle gain)")
    duration_weeks: int = Field(default=4, ge=1, le=52, description="Duration in weeks")
    exercises: str = Field(..., max_length=5000, description="List of exercises, one per line")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")