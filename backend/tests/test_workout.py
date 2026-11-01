import pytest
from pydantic import ValidationError

from app.models.workout import WorkoutPlanCreate


def test_valid_workout_plan():
    plan = WorkoutPlanCreate(
        user_id=1,
        title="Full Body",
        goal="Muscle gain",
        frequency_per_week=3,
        experience_level="beginner",
        exercises="Pushups\nPullups",
    )

    assert plan.title == "Full Body"
    assert plan.frequency_per_week == 3
    assert plan.user_id == 1


@pytest.mark.parametrize("frequency", [1, 7])
def test_valid_frequency_boundaries(frequency):
    plan = WorkoutPlanCreate(
        user_id=1,
        title="Full Body",
        goal="Muscle gain",
        frequency_per_week=frequency,
        experience_level="beginner",
        exercises="Pushups",
    )

    assert plan.frequency_per_week == frequency


@pytest.mark.parametrize("frequency", [0, 8])
def test_invalid_workout_plan_frequency(frequency):
    with pytest.raises(ValidationError):
        WorkoutPlanCreate(
            user_id=1,
            title="Full Body",
            goal="Muscle gain",
            frequency_per_week=frequency,
            experience_level="beginner",
            exercises="Pushups",
        )
