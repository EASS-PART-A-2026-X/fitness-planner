from fastapi.testclient import TestClient

from app.db import database as db
from app.main import app
from app.models.workout import WorkoutPlanCreate
from app.seed import SEED_WORKOUTS, seed_if_empty


def test_data_survives_restart(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'workouts.db'}"

    monkeypatch.setattr(
        db,
        "engine",
        db.make_engine(database_url),
    )

    with TestClient(app) as client:
        initial_workouts = client.get("/workouts").json()

        assert len(initial_workouts) == len(SEED_WORKOUTS)

        response = client.post(
            "/workouts",
            json={
                "user_id": 2,
                "title": "Persistent Workout",
                "goal": "Strength",
                "frequency_per_week": 3,
                "experience_level": "intermediate",
                "exercises": "Squats\nPushups",
            },
        )

        assert response.status_code == 201

    monkeypatch.setattr(
        db,
        "engine",
        db.make_engine(database_url),
    )

    with TestClient(app) as client:
        workouts = client.get("/workouts").json()

        titles = [workout["title"] for workout in workouts]

        expected_titles = [workout["title"] for workout in SEED_WORKOUTS]

        expected_titles.append("Persistent Workout")

        assert titles == expected_titles


def test_seed_is_idempotent(session):
    for row in SEED_WORKOUTS:
        WorkoutPlanCreate.model_validate(row)

    assert seed_if_empty(session) == len(SEED_WORKOUTS)
    assert seed_if_empty(session) == 0
