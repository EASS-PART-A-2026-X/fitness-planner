from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import database as db
from app.models.workout import (
    WorkoutPlan,
    WorkoutPlanCreate,
    WorkoutPlanPublic,
    WorkoutPlanUpdate,
)
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()

    with Session(db.engine) as session:
        seed_if_empty(session)

    yield

    db.engine.dispose()


app = FastAPI(
    title="Fitness Planner API",
    lifespan=lifespan,
)


def get_workout_or_404(
    session: Session,
    workout_id: int,
) -> WorkoutPlan:
    workout = session.get(WorkoutPlan, workout_id)

    if workout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found",
        )

    return workout


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/workouts", response_model=list[WorkoutPlanPublic])
def read_workouts(
    session: db.SessionDep,
    user_id: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WorkoutPlan]:
    statement = select(WorkoutPlan).order_by(WorkoutPlan.id)

    if user_id is not None:
        statement = statement.where(WorkoutPlan.user_id == user_id)

    statement = statement.offset(offset).limit(limit)

    return list(session.exec(statement).all())


@app.post(
    "/workouts",
    response_model=WorkoutPlanPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_workout(
    workout_in: WorkoutPlanCreate,
    session: db.SessionDep,
) -> WorkoutPlan:
    db_workout = WorkoutPlan.model_validate(workout_in.model_dump())

    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)

    return db_workout


@app.get(
    "/workouts/{workout_id}",
    response_model=WorkoutPlanPublic,
)
def read_workout(
    workout_id: int,
    session: db.SessionDep,
) -> WorkoutPlan:
    return get_workout_or_404(session, workout_id)


@app.patch(
    "/workouts/{workout_id}",
    response_model=WorkoutPlanPublic,
)
def update_workout(
    workout_id: int,
    workout_in: WorkoutPlanUpdate,
    session: db.SessionDep,
) -> WorkoutPlan:
    db_workout = get_workout_or_404(session, workout_id)

    workout_data = workout_in.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for key, value in workout_data.items():
        setattr(db_workout, key, value)

    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)

    return db_workout


@app.delete(
    "/workouts/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workout(
    workout_id: int,
    session: db.SessionDep,
) -> None:
    workout = get_workout_or_404(session, workout_id)

    session.delete(workout)
    session.commit()
