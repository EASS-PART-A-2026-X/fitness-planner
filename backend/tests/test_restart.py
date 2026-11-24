from fastapi.testclient import TestClient

from app.db import database as db
from app.main import app


def test_accounts_and_workouts_survive_restart(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'workouts.db'}"
    monkeypatch.setattr(db, "engine", db.make_engine(database_url))

    with TestClient(app) as client:
        registration = client.post(
            "/auth/register",
            json={"username": "persistent-user", "password": "a-secure-password"},
        )
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/workouts",
            headers=headers,
            json={
                "title": "Persistent Workout",
                "goal": "Strength",
                "frequency_per_week": 3,
                "experience_level": "intermediate",
                "exercises": [{"exercise": "Squats", "count": 12}],
            },
        )
        assert response.status_code == 201
        workout_id = response.json()["id"]
        session_response = client.put(
            f"/workouts/{workout_id}/session",
            headers=headers,
            json={"checked_exercises": [0]},
        )
        assert session_response.status_code == 200

    monkeypatch.setattr(db, "engine", db.make_engine(database_url))

    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"username": "persistent-user", "password": "a-secure-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        workouts = client.get("/workouts", headers=headers).json()
        assert [workout["title"] for workout in workouts] == ["Persistent Workout"]
        assert workouts[0]["exercises"] == [{"exercise": "Squats", "count": 12}]
        assert client.get(
            f"/workouts/{workout_id}/session", headers=headers
        ).json() == {"is_active": True, "checked_exercises": [0]}
        overview = client.get("/workouts/overview", headers=headers).json()
        assert overview[0]["has_unfinished_workout"] is True
