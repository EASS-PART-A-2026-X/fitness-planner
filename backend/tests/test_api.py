import pytest

VALID_WORKOUT = {
    "user_id": 1,
    "title": "Full Body",
    "goal": "Muscle gain",
    "frequency_per_week": 3,
    "experience_level": "beginner",
    "exercises": "Pushups\nPullups",
}


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_returns_201_and_read_workout(client):
    response = client.post("/workouts", json=VALID_WORKOUT)

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Full Body"
    assert data["user_id"] == 1
    assert data["frequency_per_week"] == 3
    assert data["id"] is not None

    workout_id = data["id"]

    get_response = client.get(f"/workouts/{workout_id}")

    assert get_response.status_code == 200
    assert get_response.json() == data


def test_list_filter_and_pagination(client):
    client.post("/workouts", json=VALID_WORKOUT)

    second_workout = {
        **VALID_WORKOUT,
        "user_id": 2,
        "title": "User 2 Workout",
    }
    client.post("/workouts", json=second_workout)

    third_workout = {
        **VALID_WORKOUT,
        "title": "Another User 1 Workout",
    }
    client.post("/workouts", json=third_workout)

    all_response = client.get("/workouts")

    assert all_response.status_code == 200
    assert len(all_response.json()) == 3

    filtered_response = client.get(
        "/workouts",
        params={"user_id": 1},
    )

    assert len(filtered_response.json()) == 2
    assert all(workout["user_id"] == 1 for workout in filtered_response.json())

    page_response = client.get(
        "/workouts",
        params={"offset": 1, "limit": 1},
    )

    assert page_response.status_code == 200
    assert len(page_response.json()) == 1

    assert (
        client.get(
            "/workouts",
            params={"limit": 101},
        ).status_code
        == 422
    )


def test_patch_changes_only_sent_fields(client):
    created = client.post(
        "/workouts",
        json=VALID_WORKOUT,
    ).json()

    workout_id = created["id"]

    response = client.patch(
        f"/workouts/{workout_id}",
        json={"title": "Updated Full Body"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Full Body"
    assert response.json()["goal"] == "Muscle gain"
    assert response.json()["frequency_per_week"] == 3

    null_response = client.patch(
        f"/workouts/{workout_id}",
        json={"title": None},
    )

    assert null_response.status_code == 200
    assert null_response.json()["title"] == "Updated Full Body"


def test_delete_returns_204_and_removes_workout(client):
    created = client.post(
        "/workouts",
        json=VALID_WORKOUT,
    ).json()

    workout_id = created["id"]

    response = client.delete(f"/workouts/{workout_id}")

    assert response.status_code == 204
    assert response.content == b""

    assert client.get(f"/workouts/{workout_id}").status_code == 404

    assert client.delete(f"/workouts/{workout_id}").status_code == 404


def test_missing_workout_returns_404(client):
    get_response = client.get("/workouts/999")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Workout plan not found"}

    patch_response = client.patch(
        "/workouts/999",
        json={},
    )

    assert patch_response.status_code == 404

    delete_response = client.delete("/workouts/999")

    assert delete_response.status_code == 404


@pytest.mark.parametrize(
    "invalid_changes",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"goal": ""},
        {"goal": "x" * 101},
        {"frequency_per_week": 0},
        {"frequency_per_week": 8},
        {"experience_level": " "},
        {"experience_level": "x" * 51},
        {"exercises": "x" * 5001},
        {"user_id": 0},
    ],
)
def test_invalid_workout_bodies_return_422(
    client,
    invalid_changes,
):
    invalid_body = {
        **VALID_WORKOUT,
        **invalid_changes,
    }

    response = client.post(
        "/workouts",
        json=invalid_body,
    )

    assert response.status_code == 422, invalid_changes


def test_missing_required_field_returns_422(client):
    response = client.post(
        "/workouts",
        json={"title": "Full Body"},
    )

    assert response.status_code == 422


def test_unknown_fields_are_rejected(client):
    invalid_body = {
        **VALID_WORKOUT,
        "unexpected_field": "not allowed",
    }

    response = client.post(
        "/workouts",
        json=invalid_body,
    )

    assert response.status_code == 422

    created = client.post(
        "/workouts",
        json=VALID_WORKOUT,
    ).json()

    patch_response = client.patch(
        f"/workouts/{created['id']}",
        json={"unexpected_field": "not allowed"},
    )

    assert patch_response.status_code == 422


@pytest.mark.parametrize(
    "invalid_changes",
    [
        {"frequency_per_week": 0},
        {"frequency_per_week": 8},
        {"title": ""},
        {"goal": "x" * 101},
    ],
)
def test_invalid_patch_returns_422(client, invalid_changes):
    created = client.post(
        "/workouts",
        json=VALID_WORKOUT,
    ).json()

    response = client.patch(
        f"/workouts/{created['id']}",
        json=invalid_changes,
    )

    assert response.status_code == 422


def test_each_test_starts_with_empty_database(client):
    response = client.get("/workouts")

    assert response.status_code == 200
    assert response.json() == []
