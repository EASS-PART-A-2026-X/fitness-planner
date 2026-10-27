import pytest
from app.models.workout import WorkoutPlan

def test_valid_workout_plan():
    plan = WorkoutPlan(
        title="Full Body",
        goal="Muscle gain",
        duration_weeks=4,
        exercises="Pushups\nPullups"
    )
    assert plan.title == "Full Body"
    assert plan.duration_weeks == 4

def test_invalid_workout_plan_duration():
    with pytest.raises(ValueError):
        WorkoutPlan(
            title="Bad Plan",
            goal="Cardio",
            duration_weeks=0,  # חורג מהתנאי ge=1 שמוגדר במודל
            exercises="Running"
        )