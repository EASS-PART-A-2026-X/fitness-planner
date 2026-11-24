from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.main import current_week_start
from app.models.workout import WorkoutCompletion, WorkoutSession

WORKOUT = {
    "title": "Full Body",
    "goal": "Strength",
    "frequency_per_week": 3,
    "experience_level": "beginner",
    "exercises": [{"exercise": "Squat", "count": 10}],
}


def test_progress_increments_and_is_scoped_to_owner(authenticated_client):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    workout_id = workout["id"]

    initial = authenticated_client.get(f"/workouts/{workout_id}/progress")
    assert initial.json()["completed_this_week"] == 0
    assert initial.json()["frequency_per_week"] == 3

    completed = authenticated_client.post(f"/workouts/{workout_id}/complete")
    assert completed.status_code == 201
    assert completed.json()["completed_this_week"] == 1

    second = authenticated_client.post(f"/workouts/{workout_id}/complete")
    assert second.json()["completed_this_week"] == 2
    assert (
        authenticated_client.get(f"/workouts/{workout_id}/progress").json()[
            "completed_this_week"
        ]
        == 2
    )


def test_ai_workout_shape_is_accepted_by_the_workout_api(authenticated_client):
    response = authenticated_client.post(
        "/workouts",
        json={
            "workout_name": "פלג גוף עליון - כוח",
            "exercises": [
                {
                    "name": "שכיבות שמיכה",
                    "sets": 3,
                    "reps": "10, 10, 8",
                    "rest_seconds": 60,
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "פלג גוף עליון - כוח"
    assert response.json()["exercises"] == [
        {
            "name": "שכיבות שמיכה",
            "sets": 3,
            "reps": "10, 10, 8",
            "rest_seconds": 60,
        }
    ]


def test_workout_session_is_persisted_and_included_in_home_overview(
    authenticated_client,
    client,
):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    workout_id = workout["id"]

    saved = authenticated_client.put(
        f"/workouts/{workout_id}/session",
        json={"checked_exercises": [0]},
    )
    assert saved.status_code == 200
    assert saved.json() == {"is_active": True, "checked_exercises": [0]}
    assert (
        authenticated_client.get(f"/workouts/{workout_id}/session").json()
        == saved.json()
    )

    overview = authenticated_client.get("/workouts/overview")
    assert overview.status_code == 200
    assert overview.json()[0]["completed_this_week"] == 0
    assert overview.json()[0]["frequency_per_week"] == 3
    assert overview.json()[0]["has_unfinished_workout"] is True

    other = client.post(
        "/auth/register",
        json={"username": "session-owner", "password": "another-password"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert (
        client.get(f"/workouts/{workout_id}/session", headers=headers).status_code
        == 404
    )
    assert (
        client.put(
            f"/workouts/{workout_id}/session",
            json={"checked_exercises": [0]},
            headers=headers,
        ).status_code
        == 404
    )

    cleared = authenticated_client.put(
        f"/workouts/{workout_id}/session",
        json={"checked_exercises": []},
    )
    assert cleared.json() == {"is_active": False, "checked_exercises": []}
    assert (
        authenticated_client.get("/workouts/overview").json()[0][
            "has_unfinished_workout"
        ]
        is False
    )


def test_workout_session_rejects_an_index_outside_the_plan(authenticated_client):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()

    response = authenticated_client.put(
        f"/workouts/{workout['id']}/session",
        json={"checked_exercises": [1]},
    )

    assert response.status_code == 422


def test_completion_clears_unfinished_session(authenticated_client):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    workout_id = workout["id"]
    authenticated_client.put(
        f"/workouts/{workout_id}/session",
        json={"checked_exercises": [0]},
    )

    response = authenticated_client.post(f"/workouts/{workout_id}/complete")

    assert response.status_code == 201
    assert authenticated_client.get(f"/workouts/{workout_id}/session").json() == {
        "is_active": False,
        "checked_exercises": [],
    }
    recent = authenticated_client.get("/workouts/recent-completions").json()
    assert recent[0]["checked_exercises"] == WORKOUT["exercises"]
    overview = authenticated_client.get("/workouts/overview").json()[0]
    assert overview["completed_this_week"] == 1
    assert overview["has_unfinished_workout"] is False


def test_completed_sets_save_actual_reps_and_are_recorded_in_history(
    authenticated_client,
):
    workout = authenticated_client.post(
        "/workouts",
        json={
            **WORKOUT,
            "exercises": [
                {
                    "name": "Push-ups",
                    "sets": 2,
                    "reps": "4, 4",
                    "rest_seconds": 30,
                }
            ],
        },
    ).json()
    workout_id = workout["id"]
    actual_sets = [
        {"exercise_index": 0, "set_index": 0, "actual_reps": 3},
        {"exercise_index": 0, "set_index": 1, "actual_reps": 2},
    ]

    saved = authenticated_client.put(
        f"/workouts/{workout_id}/session",
        json={"completed_sets": actual_sets[:1]},
    )
    assert saved.status_code == 200
    assert saved.json()["completed_sets"] == actual_sets[:1]
    assert (
        authenticated_client.get(f"/workouts/{workout_id}/session").json()[
            "completed_sets"
        ]
        == actual_sets[:1]
    )

    completed = authenticated_client.post(
        f"/workouts/{workout_id}/complete",
        json={"completed_sets": actual_sets},
    )

    assert completed.status_code == 201
    assert authenticated_client.get(f"/workouts/{workout_id}/session").json() == {
        "is_active": False,
        "checked_exercises": [],
    }
    assert authenticated_client.get("/workouts/recent-completions").json()[0][
        "checked_exercises"
    ] == [
        {
            "name": "Push-ups",
            "sets": 2,
            "reps": "3, 2",
            "rest_seconds": 30,
        }
    ]


def test_workout_history_summarizes_weekly_completions(authenticated_client, session):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    current_week = current_week_start()
    previous_week = current_week - timedelta(weeks=1)
    user_id = authenticated_client.get("/auth/me").json()["id"]
    session.add_all(
        [
            WorkoutCompletion(
                user_id=user_id,
                workout_id=workout["id"],
                completed_on=completed_on,
            )
            for completed_on in (
                previous_week.isoformat(),
                current_week.isoformat(),
                current_week.isoformat(),
            )
        ]
    )
    session.commit()

    response = authenticated_client.get(
        "/workouts/progress/history",
        params={"weeks": 2},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "week_start": previous_week.isoformat(),
            "completed_sessions": 1,
            "weekly_target": 3,
        },
        {
            "week_start": current_week.isoformat(),
            "completed_sessions": 2,
            "weekly_target": 3,
        },
    ]


def test_recent_completions_include_checked_exercises(authenticated_client):
    workout = authenticated_client.post(
        "/workouts",
        json={
            **WORKOUT,
            "exercises": [
                {"exercise": "Squat", "count": 10},
                {"exercise": "Lunge", "count": 8},
            ],
        },
    ).json()
    workout_id = workout["id"]

    for _ in range(4):
        authenticated_client.post(f"/workouts/{workout_id}/complete")

    recent = authenticated_client.get("/workouts/recent-completions")

    assert recent.status_code == 200
    assert len(recent.json()) == 3
    assert [
        completion["checked_exercises"][0]["exercise"] for completion in recent.json()
    ] == ["Squat", "Squat", "Squat"]
    assert (
        authenticated_client.get(
            "/workouts/recent-completions", params={"limit": 1}
        ).json()[0]["checked_exercises"][0]["exercise"]
        == "Squat"
    )


def test_changing_exercise_list_clears_unfinished_session(authenticated_client):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    workout_id = workout["id"]
    authenticated_client.put(
        f"/workouts/{workout_id}/session",
        json={"checked_exercises": [0]},
    )

    updated = authenticated_client.patch(
        f"/workouts/{workout_id}",
        json={"exercises": [{"exercise": "Lunges", "count": 12}]},
    )

    assert updated.status_code == 200
    assert authenticated_client.get(f"/workouts/{workout_id}/session").json() == {
        "is_active": False,
        "checked_exercises": [],
    }


def test_deleting_workout_clears_unfinished_session(authenticated_client, session):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    authenticated_client.put(
        f"/workouts/{workout['id']}/session",
        json={"checked_exercises": [0]},
    )

    deleted = authenticated_client.delete(f"/workouts/{workout['id']}")

    assert deleted.status_code == 204
    assert session.exec(select(WorkoutSession)).all() == []


def test_progress_for_another_users_plan_is_not_visible(authenticated_client, client):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    other = client.post(
        "/auth/register",
        json={"username": "another", "password": "another-password"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert (
        client.get(f"/workouts/{workout['id']}/progress", headers=headers).status_code
        == 404
    )
    assert (
        client.post(f"/workouts/{workout['id']}/complete", headers=headers).status_code
        == 404
    )


def test_old_completions_are_not_counted_this_week(authenticated_client, session):
    workout = authenticated_client.post("/workouts", json=WORKOUT).json()
    last_week = current_week_start() - timedelta(days=1)
    user_id = authenticated_client.get("/auth/me").json()["id"]
    session.add(
        WorkoutCompletion(
            user_id=user_id,
            workout_id=workout["id"],
            completed_on=last_week.isoformat(),
        )
    )
    session.commit()

    response = authenticated_client.get(f"/workouts/{workout['id']}/progress")

    assert response.json()["completed_this_week"] == 0


def test_week_starts_on_monday():
    assert current_week_start().weekday() == 0
    assert current_week_start() <= datetime.now(UTC).date()
