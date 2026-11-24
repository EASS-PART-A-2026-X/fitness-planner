import pytest
from pydantic import ValidationError

from app.models.workout import WorkoutExercise, WorkoutPlanCreate


def test_valid_workout_plan():
    plan = WorkoutPlanCreate(
        title="Full Body",
        goal="Muscle gain",
        frequency_per_week=3,
        experience_level="beginner",
        exercises=[{"exercise": "Pushups", "count": 20}],
    )

    assert plan.title == "Full Body"
    assert plan.frequency_per_week == 3
    assert plan.exercises == [WorkoutExercise(exercise="Pushups", count=20)]


@pytest.mark.parametrize("frequency", [1, 7])
def test_valid_frequency_boundaries(frequency):
    plan = WorkoutPlanCreate(
        title="Full Body",
        goal="Muscle gain",
        frequency_per_week=frequency,
        experience_level="beginner",
        exercises=[{"exercise": "Pushups", "count": 20}],
    )

    assert plan.frequency_per_week == frequency


@pytest.mark.parametrize(
    "exercise",
    [
        {"exercise": " ", "count": 1},
        {"exercise": "Pushups", "count": 0},
        {"exercise": "Pushups", "count": 10001},
        {"exercise": "Pushups", "count": 1, "sets": 3},
    ],
)
def test_invalid_exercise_is_rejected(exercise):
    with pytest.raises(ValidationError):
        WorkoutExercise.model_validate(exercise)
