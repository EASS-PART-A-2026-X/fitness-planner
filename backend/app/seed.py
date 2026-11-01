from sqlmodel import Session, select

from app.models.workout import WorkoutPlan

SEED_WORKOUTS: list[dict] = [
    {
        "user_id": 1,
        "title": "Full Body Beginner",
        "goal": "General fitness",
        "frequency_per_week": 3,
        "experience_level": "beginner",
        "exercises": "Squats\nPush-ups\nPlank",
    },
    {
        "user_id": 1,
        "title": "Upper Body",
        "goal": "Strength",
        "frequency_per_week": 2,
        "experience_level": "intermediate",
        "exercises": "Push-ups\nPull-ups\nShoulder press",
    },
    {
        "user_id": 1,
        "title": "Cardio Plan",
        "goal": "Improve endurance",
        "frequency_per_week": 4,
        "experience_level": "beginner",
        "exercises": "Walking\nCycling\nSwimming",
    },
]


def seed_if_empty(session: Session) -> int:
    existing = session.exec(select(WorkoutPlan).limit(1)).first()

    if existing is not None:
        return 0

    workouts = [WorkoutPlan.model_validate(row) for row in SEED_WORKOUTS]

    session.add_all(workouts)
    session.commit()

    return len(workouts)
