import pytest

VALID_WORKOUT = {
    "title": "Full Body",
    "goal": "Muscle gain",
    "frequency_per_week": 3,
    "experience_level": "beginner",
    "exercises": [
        {"exercise": "Pushups", "count": 20},
        {"exercise": "Pullups", "count": 10},
    ],
}


def create_workout(client, body=VALID_WORKOUT):
    return client.post("/workouts", json=body)


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_workout_routes_require_authentication(client):
    assert client.get("/workouts").status_code == 401
    assert client.post("/workouts", json=VALID_WORKOUT).status_code == 401


def test_create_returns_201_and_read_workout(authenticated_client):
    response = create_workout(authenticated_client)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Full Body"
    assert data["frequency_per_week"] == 3
    assert data["emoji"] == "🏋️"
    assert data["exercises"] == VALID_WORKOUT["exercises"]
    assert "user_id" not in data
    assert data["id"] is not None

    get_response = authenticated_client.get(f"/workouts/{data['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == data


def test_list_and_pagination_are_scoped_to_authenticated_user(
    authenticated_client,
    client,
):
    create_workout(authenticated_client)
    create_workout(
        authenticated_client,
        {**VALID_WORKOUT, "title": "Second workout"},
    )
    second_account = client.post(
        "/auth/register",
        json={"username": "second-user", "password": "another-password"},
    ).json()
    second_headers = {"Authorization": f"Bearer {second_account['access_token']}"}
    private = client.post(
        "/workouts",
        json={**VALID_WORKOUT, "title": "Private workout"},
        headers=second_headers,
    )
    assert private.status_code == 201

    listed = authenticated_client.get("/workouts")
    assert [row["title"] for row in listed.json()] == [
        "Full Body",
        "Second workout",
    ]

    page = authenticated_client.get("/workouts", params={"offset": 1, "limit": 1})
    assert page.status_code == 200
    assert [row["title"] for row in page.json()] == ["Second workout"]
    assert (
        authenticated_client.get("/workouts", params={"limit": 101}).status_code == 422
    )


def test_other_users_cannot_read_update_or_delete_a_plan(
    authenticated_client,
    client,
):
    workout = create_workout(authenticated_client).json()
    other = client.post(
        "/auth/register",
        json={"username": "other-user", "password": "another-password"},
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}
    workout_id = workout["id"]

    assert client.get(f"/workouts/{workout_id}", headers=headers).status_code == 404
    assert (
        client.patch(
            f"/workouts/{workout_id}",
            json={"title": "Stolen"},
            headers=headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/workouts/{workout_id}", headers=headers).status_code == 404
    assert authenticated_client.get(f"/workouts/{workout_id}").status_code == 200


def test_client_cannot_assign_workout_to_another_user(authenticated_client):
    response = authenticated_client.post(
        "/workouts",
        json={**VALID_WORKOUT, "user_id": 1},
    )

    assert response.status_code == 422


def test_patch_changes_only_sent_fields(authenticated_client):
    created = create_workout(authenticated_client).json()
    response = authenticated_client.patch(
        f"/workouts/{created['id']}",
        json={"title": "Updated Full Body"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Full Body"
    assert response.json()["goal"] == "Muscle gain"
    assert response.json()["frequency_per_week"] == 3

    null_response = authenticated_client.patch(
        f"/workouts/{created['id']}",
        json={"title": None},
    )
    assert null_response.status_code == 200
    assert null_response.json()["title"] == "Updated Full Body"


def test_delete_returns_204_and_removes_workout(authenticated_client):
    created = create_workout(authenticated_client).json()
    workout_id = created["id"]

    response = authenticated_client.delete(f"/workouts/{workout_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert authenticated_client.get(f"/workouts/{workout_id}").status_code == 404
    assert authenticated_client.delete(f"/workouts/{workout_id}").status_code == 404


def test_missing_workout_returns_404(authenticated_client):
    assert authenticated_client.get("/workouts/999").status_code == 404
    assert authenticated_client.patch("/workouts/999", json={}).status_code == 404
    assert authenticated_client.delete("/workouts/999").status_code == 404


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
        {"exercises": [{"exercise": " ", "count": 1}]},
        {"exercises": [{"exercise": "Squat", "count": 0}]},
        {"exercises": [{"exercise": "x" * 201, "count": 1}]},
        {"exercises": [{"exercise": "Squat", "count": 1, "unexpected": True}]},
    ],
)
def test_invalid_workout_bodies_return_422(authenticated_client, invalid_changes):
    response = authenticated_client.post(
        "/workouts",
        json={**VALID_WORKOUT, **invalid_changes},
    )

    assert response.status_code == 422, invalid_changes


def test_missing_required_field_returns_422(authenticated_client):
    response = authenticated_client.post("/workouts", json={"title": "Full Body"})

    assert response.status_code == 422


def test_unknown_fields_are_rejected(authenticated_client):
    invalid_body = {**VALID_WORKOUT, "unexpected_field": "not allowed"}
    assert authenticated_client.post("/workouts", json=invalid_body).status_code == 422

    created = create_workout(authenticated_client).json()
    assert (
        authenticated_client.patch(
            f"/workouts/{created['id']}",
            json={"unexpected_field": "not allowed"},
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "invalid_changes",
    [
        {"frequency_per_week": 0},
        {"frequency_per_week": 8},
        {"title": ""},
        {"goal": "x" * 101},
        {"exercises": [{"exercise": "Jumping jacks", "count": -1}]},
    ],
)
def test_invalid_patch_returns_422(authenticated_client, invalid_changes):
    created = create_workout(authenticated_client).json()

    response = authenticated_client.patch(
        f"/workouts/{created['id']}",
        json=invalid_changes,
    )

    assert response.status_code == 422


def test_each_test_starts_with_empty_workouts(authenticated_client):
    assert authenticated_client.get("/workouts").json() == []


def test_exercises_round_trip_as_structured_json(authenticated_client):
    created = create_workout(authenticated_client).json()

    assert created["exercises"] == [
        {"exercise": "Pushups", "count": 20},
        {"exercise": "Pullups", "count": 10},
    ]
    assert authenticated_client.get(f"/workouts/{created['id']}").json() == created
