def test_register_login_and_logout(client):
    registration = client.post(
        "/auth/register",
        json={"username": "Tamar", "password": "a-secure-password"},
    )

    assert registration.status_code == 201
    registered = registration.json()
    assert registered["user"]["username"] == "tamar"
    assert registered["token_type"] == "bearer"
    assert "password" not in registered["user"]
    assert "password_hash" not in registered["user"]

    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    assert client.get("/auth/me", headers=headers).json() == registered["user"]
    assert client.get("/workouts", headers=headers).status_code == 200

    login = client.post(
        "/auth/login",
        json={"username": "TAMAR", "password": "a-secure-password"},
    )
    assert login.status_code == 200
    assert login.json()["user"] == registered["user"]

    assert client.delete("/auth/session", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_duplicate_usernames_are_case_insensitive(client):
    client.post(
        "/auth/register",
        json={"username": "tamar", "password": "a-secure-password"},
    )

    response = client.post(
        "/auth/register",
        json={"username": "TAMAR", "password": "another-password"},
    )

    assert response.status_code == 409


def test_invalid_credentials_do_not_issue_a_session(client):
    client.post(
        "/auth/register",
        json={"username": "tamar", "password": "a-secure-password"},
    )

    response = client.post(
        "/auth/login",
        json={"username": "tamar", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_registration_rejects_weak_credentials(client):
    assert (
        client.post(
            "/auth/register",
            json={"username": "x", "password": "short"},
        ).status_code
        == 422
    )


def test_new_account_does_not_inherit_legacy_workouts(client, session):
    from app.models.workout import WorkoutPlan

    session.add(
        WorkoutPlan(
            user_id=1,
            title="Legacy",
            goal="Old data",
            frequency_per_week=3,
            experience_level="beginner",
            exercises=[{"exercise": "Squat", "count": 10}],
        )
    )
    session.commit()

    registered = client.post(
        "/auth/register",
        json={"username": "new-user", "password": "a-secure-password"},
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    assert registered["user"]["id"] > 1
    assert client.get("/workouts", headers=headers).json() == []
