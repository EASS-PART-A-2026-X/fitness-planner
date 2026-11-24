import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/database.db",
)


def make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    db_file = engine.url.database

    if db_file:
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)


def _unwrap_double_encoded(exercises: list) -> list | None:
    """Undo an earlier bug that wrapped a JSON exercise list in one legacy item.

    A structured list such as [{"name": ...}] was stored as
    [{"exercise": "[{\\"name\\": ...}]", "count": 1}], sometimes several times.
    Returns the original list, or None if the value is not wrapped.
    """
    unwrapped = None
    while (
        len(exercises) == 1
        and isinstance(exercises[0], dict)
        and exercises[0].get("count") == 1
        and isinstance(exercises[0].get("exercise"), str)
        and exercises[0]["exercise"].lstrip().startswith("[")
    ):
        try:
            inner = json.loads(exercises[0]["exercise"])
        except json.JSONDecodeError:
            break
        if not isinstance(inner, list) or not all(isinstance(i, dict) for i in inner):
            break
        exercises = unwrapped = inner
    return unwrapped


def migrate_legacy_exercises() -> None:
    """Convert pre-JSON text exercise lists; leave valid JSON lists untouched."""
    with engine.begin() as connection:
        rows = connection.execute(text("SELECT id, exercises FROM workoutplan")).all()
        for workout_id, stored_exercises in rows:
            if not isinstance(stored_exercises, str):
                continue
            try:
                exercises = json.loads(stored_exercises)
            except json.JSONDecodeError:
                exercises = None

            if isinstance(exercises, list) and all(
                isinstance(item, dict) for item in exercises
            ):
                repaired = _unwrap_double_encoded(exercises)
                if repaired is not None:
                    connection.execute(
                        text(
                            "UPDATE workoutplan SET exercises = :exercises "
                            "WHERE id = :id"
                        ),
                        {"exercises": json.dumps(repaired), "id": workout_id},
                    )
                continue

            names = [
                line.strip() for line in stored_exercises.splitlines() if line.strip()
            ]
            if not names and stored_exercises.strip():
                names = [stored_exercises.strip()]
            converted = [{"exercise": name, "count": 1} for name in names]
            connection.execute(
                text("UPDATE workoutplan SET exercises = :exercises WHERE id = :id"),
                {"exercises": json.dumps(converted), "id": workout_id},
            )


def migrate_workout_emoji() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("workoutplan")}
    if "emoji" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE workoutplan "
                "ADD COLUMN emoji VARCHAR(8) NOT NULL DEFAULT '🏋️'"
            )
        )


def migrate_completion_exercises() -> None:
    columns = {
        column["name"] for column in inspect(engine).get_columns("workoutcompletion")
    }
    if "checked_exercises" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE workoutcompletion "
                "ADD COLUMN checked_exercises JSON NOT NULL DEFAULT '[]'"
            )
        )


def migrate_workout_session_results() -> None:
    columns = {
        column["name"] for column in inspect(engine).get_columns("workoutsession")
    }
    if "completed_sets" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE workoutsession "
                "ADD COLUMN completed_sets JSON NOT NULL DEFAULT '[]'"
            )
        )


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
