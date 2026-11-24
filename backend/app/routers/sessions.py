"""Running a workout: weekly progress, live sessions and completions."""

from datetime import UTC, datetime

from fastapi import APIRouter, status

from app import auth, services
from app.db import database as db
from app.models.workout import (
    CompletedSet,
    WorkoutCompletion,
    WorkoutCompletionCreate,
    WorkoutProgressPublic,
    WorkoutSession,
    WorkoutSessionPublic,
    WorkoutSessionUpdate,
)

router = APIRouter(prefix="/workouts/{workout_id}", tags=["training sessions"])


def _completed_sets(raw: list[dict]) -> list[CompletedSet] | None:
    return [CompletedSet.model_validate(item) for item in raw] or None


@router.get("/progress", response_model=WorkoutProgressPublic)
def workout_progress(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutProgressPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    return services.read_progress(session, workout, current_user.id)


@router.post(
    "/complete",
    response_model=WorkoutProgressPublic,
    status_code=status.HTTP_201_CREATED,
)
def complete_workout(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
    completion_in: WorkoutCompletionCreate | None = None,
) -> WorkoutProgressPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    if completion_in is not None:
        services.validate_completed_sets(workout, completion_in.completed_sets)
        exercises = services.completion_exercises(
            workout.exercises, completion_in.completed_sets
        )
    else:
        exercises = workout.exercises

    services.discard_unfinished_session(session, current_user.id, workout.id)
    session.add(
        WorkoutCompletion(
            user_id=current_user.id,
            workout_id=workout.id,
            completed_on=datetime.now(UTC).date().isoformat(),
            checked_exercises=exercises,
        )
    )
    session.commit()
    return services.read_progress(session, workout, current_user.id)


@router.get(
    "/session",
    response_model=WorkoutSessionPublic,
    response_model_exclude_none=True,
)
def read_workout_session(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutSessionPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    unfinished = services.get_unfinished_session(session, current_user.id, workout.id)
    if unfinished is None:
        return WorkoutSessionPublic(is_active=False, checked_exercises=[])
    return WorkoutSessionPublic(
        is_active=True,
        checked_exercises=unfinished.checked_exercises,
        completed_sets=_completed_sets(unfinished.completed_sets),
    )


@router.post(
    "/session/start",
    response_model=WorkoutSessionPublic,
    response_model_exclude_none=True,
)
def start_workout_session(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutSessionPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    unfinished = services.get_unfinished_session(session, current_user.id, workout.id)
    if unfinished is None:
        unfinished = WorkoutSession(user_id=current_user.id, workout_id=workout.id)
        session.add(unfinished)
        session.commit()
        session.refresh(unfinished)
    return WorkoutSessionPublic(
        is_active=True,
        checked_exercises=unfinished.checked_exercises,
        completed_sets=_completed_sets(unfinished.completed_sets),
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def cancel_workout_session(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> None:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    services.discard_unfinished_session(session, current_user.id, workout.id)
    session.commit()


@router.put(
    "/session",
    response_model=WorkoutSessionPublic,
    response_model_exclude_none=True,
)
def update_workout_session(
    workout_id: int,
    session_in: WorkoutSessionUpdate,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutSessionPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    checked_exercises = sorted(set(session_in.checked_exercises))
    if any(index >= len(workout.exercises) for index in checked_exercises):
        raise services.unprocessable(
            "Checked exercise index is outside this workout plan."
        )
    completed_sets = session_in.completed_sets
    if completed_sets is not None:
        services.validate_completed_sets(workout, completed_sets)
        # An exercise is checked once every one of its sets is recorded.
        checked_exercises = [
            index
            for index, exercise in enumerate(workout.exercises)
            if {
                item.set_index
                for item in completed_sets
                if item.exercise_index == index
            }
            == set(range(services.exercise_set_count(exercise)))
        ]

    unfinished = services.get_unfinished_session(session, current_user.id, workout.id)
    if not checked_exercises and not completed_sets:
        if unfinished is not None:
            session.delete(unfinished)
    elif unfinished is None:
        session.add(
            WorkoutSession(
                user_id=current_user.id,
                workout_id=workout.id,
                checked_exercises=checked_exercises,
                completed_sets=[item.model_dump() for item in completed_sets or []],
            )
        )
    else:
        unfinished.checked_exercises = checked_exercises
        if completed_sets is not None:
            unfinished.completed_sets = [item.model_dump() for item in completed_sets]
        session.add(unfinished)
    session.commit()
    return WorkoutSessionPublic(
        is_active=bool(checked_exercises or completed_sets),
        checked_exercises=checked_exercises,
        completed_sets=completed_sets,
    )
