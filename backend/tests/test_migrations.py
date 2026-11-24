import json

from sqlalchemy import text
from sqlmodel import create_engine

from app.db import database as db


def test_legacy_exercise_text_is_migrated_to_json(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    monkeypatch.setattr(db, "engine", engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE workoutplan "
                "(id INTEGER PRIMARY KEY, exercises VARCHAR NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO workoutplan (id, exercises) VALUES (1, :exercises)"),
            {"exercises": "Squats\nPush-ups"},
        )

    try:
        db.migrate_workout_emoji()
        db.migrate_legacy_exercises()

        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT exercises FROM workoutplan WHERE id = 1")
            ).scalar_one()
            emoji = connection.execute(
                text("SELECT emoji FROM workoutplan WHERE id = 1")
            ).scalar_one()

        assert json.loads(stored) == [
            {"exercise": "Squats", "count": 1},
            {"exercise": "Push-ups", "count": 1},
        ]
        assert emoji == "🏋️"
    finally:
        engine.dispose()


def test_old_workout_completions_get_empty_checked_exercise_history(
    tmp_path,
    monkeypatch,
):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-completions.db'}")
    monkeypatch.setattr(db, "engine", engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE workoutcompletion "
                "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
                "workout_id INTEGER NOT NULL, completed_on VARCHAR NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO workoutcompletion "
                "(id, user_id, workout_id, completed_on) "
                "VALUES (1, 1, 1, '2026-11-13')"
            )
        )

    try:
        db.migrate_completion_exercises()

        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT checked_exercises FROM workoutcompletion WHERE id = 1")
            ).scalar_one()

        assert json.loads(stored) == []
    finally:
        engine.dispose()


def test_old_workout_sessions_get_empty_completed_sets(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-sessions.db'}")
    monkeypatch.setattr(db, "engine", engine)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE workoutsession "
                "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
                "workout_id INTEGER NOT NULL, checked_exercises JSON NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO workoutsession "
                "(id, user_id, workout_id, checked_exercises) "
                "VALUES (1, 1, 1, '[]')"
            )
        )

    try:
        db.migrate_workout_session_results()

        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT completed_sets FROM workoutsession WHERE id = 1")
            ).scalar_one()

        assert json.loads(stored) == []
    finally:
        engine.dispose()


STRUCTURED = [
    {"name": "Pull-ups", "sets": 3, "reps": "10, 10, 8", "rest_seconds": 60},
    {
        "name": "Plank",
        "sets": 2,
        "reps": "30, 30",
        "rest_seconds": 30,
        "notes": "Brace",
    },
]


def _run_exercise_migration(tmp_path, monkeypatch, stored: str) -> list:
    engine = create_engine(f"sqlite:///{tmp_path / 'plans.db'}")
    monkeypatch.setattr(db, "engine", engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE workoutplan "
                "(id INTEGER PRIMARY KEY, exercises VARCHAR NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO workoutplan (id, exercises) VALUES (1, :exercises)"),
            {"exercises": stored},
        )
    try:
        db.migrate_legacy_exercises()
        db.migrate_legacy_exercises()  # runs on every restart: must be idempotent
        with engine.connect() as connection:
            return json.loads(
                connection.execute(
                    text("SELECT exercises FROM workoutplan WHERE id = 1")
                ).scalar_one()
            )
    finally:
        engine.dispose()


def test_structured_exercises_survive_restarts(tmp_path, monkeypatch):
    stored = _run_exercise_migration(tmp_path, monkeypatch, json.dumps(STRUCTURED))

    assert stored == STRUCTURED


def test_exercises_wrapped_by_the_old_migration_are_repaired(tmp_path, monkeypatch):
    wrapped = json.dumps(STRUCTURED)
    for _ in range(3):  # the old bug nested one level per restart
        wrapped = json.dumps([{"exercise": wrapped, "count": 1}])

    stored = _run_exercise_migration(tmp_path, monkeypatch, wrapped)

    assert stored == STRUCTURED
