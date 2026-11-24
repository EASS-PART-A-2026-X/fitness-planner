"""Shared queries and rules used by several routers."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.workout import (
    CompletedSet,
    WorkoutCompletion,
    WorkoutPlan,
    WorkoutProgressPublic,
    WorkoutSession,
)


def current_week_start() -> date:
    today = datetime.now(UTC).date()
    return today - timedelta(days=today.weekday())


def get_workout_or_404(session: Session, workout_id: int, user_id: int) -> WorkoutPlan:
    workout = session.exec(
        select(WorkoutPlan).where(
            WorkoutPlan.id == workout_id,
            WorkoutPlan.user_id == user_id,
        )
    ).first()
    if workout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout plan not found",
        )
    return workout


def get_unfinished_session(
    session: Session, user_id: int, workout_id: int
) -> WorkoutSession | None:
    return session.exec(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.workout_id == workout_id,
        )
    ).first()


def discard_unfinished_session(session: Session, user_id: int, workout_id: int) -> None:
    unfinished = get_unfinished_session(session, user_id, workout_id)
    if unfinished is not None:
        session.delete(unfinished)


def read_progress(
    session: Session, workout: WorkoutPlan, user_id: int
) -> WorkoutProgressPublic:
    week_start = current_week_start()
    completed = session.exec(
        select(func.count(WorkoutCompletion.id)).where(
            WorkoutCompletion.user_id == user_id,
            WorkoutCompletion.workout_id == workout.id,
            WorkoutCompletion.completed_on >= week_start.isoformat(),
        )
    ).one()
    return WorkoutProgressPublic(
        completed_this_week=completed,
        frequency_per_week=workout.frequency_per_week,
        week_start=week_start.isoformat(),
    )


def exercise_set_count(exercise: dict) -> int:
    return int(exercise.get("sets", 1))


def unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
    )


def validate_completed_sets(
    workout: WorkoutPlan, completed_sets: Sequence[CompletedSet]
) -> None:
    """Each set is recorded once and points at a real exercise and set."""
    keys = [(item.exercise_index, item.set_index) for item in completed_sets]
    if len(set(keys)) != len(keys):
        raise unprocessable("A set can only be recorded once.")
    for item in completed_sets:
        if item.exercise_index >= len(workout.exercises):
            raise unprocessable("Set exercise index is outside this workout plan.")
        if item.set_index >= exercise_set_count(workout.exercises[item.exercise_index]):
            raise unprocessable("Set index is outside this exercise.")


def completion_exercises(
    exercises: list[dict], completed_sets: Sequence[CompletedSet]
) -> list[dict]:
    """Summarise what was actually performed, in plan order."""
    by_exercise: dict[int, list[CompletedSet]] = {}
    for completed_set in completed_sets:
        by_exercise.setdefault(completed_set.exercise_index, []).append(completed_set)

    results = []
    for exercise_index, exercise in enumerate(exercises):
        performed = sorted(
            by_exercise.get(exercise_index, []), key=lambda item: item.set_index
        )
        if not performed:
            continue
        if "name" in exercise:
            results.append(
                {
                    "name": exercise["name"],
                    "sets": len(performed),
                    "reps": ", ".join(str(item.actual_reps) for item in performed),
                    "rest_seconds": exercise.get("rest_seconds", 60),
                }
            )
        else:
            results.append(
                {
                    "exercise": exercise["exercise"],
                    "count": sum(item.actual_reps for item in performed),
                }
            )
    return results


def recent_completions(
    session: Session, user_id: int, limit: int = 3
) -> list[tuple[WorkoutCompletion, str]]:
    return list(
        session.exec(
            select(WorkoutCompletion, WorkoutPlan.title)
            .join(WorkoutPlan, WorkoutPlan.id == WorkoutCompletion.workout_id)
            .where(WorkoutCompletion.user_id == user_id)
            .order_by(
                WorkoutCompletion.completed_on.desc(), WorkoutCompletion.id.desc()
            )
            .limit(limit)
        ).all()
    )
