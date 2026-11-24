"""Workout plan CRUD, dashboard summaries and AI plan generation."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, select

from app import auth, services
from app.ai_client import (
    AIClientDep,
    AIServiceBadOutput,
    AIServiceUnavailable,
    HistoryItem,
    PlanRequest,
    WorkoutPlanDraft,
)
from app.db import database as db
from app.models.workout import (
    GeneratedWorkoutPublic,
    GeneratePlanRequest,
    RecentWorkoutPublic,
    RegenerateExercisesRequest,
    WorkoutCompletion,
    WorkoutHistoryWeekPublic,
    WorkoutOverviewPublic,
    WorkoutPlan,
    WorkoutPlanCreate,
    WorkoutPlanPublic,
    WorkoutPlanUpdate,
    WorkoutSession,
)

router = APIRouter(prefix="/workouts", tags=["workout plans"])
AI_UNAVAILABLE = "AI service unavailable"
AI_BAD_OUTPUT = "AI service returned invalid output"


@router.get(
    "", response_model=list[WorkoutPlanPublic], response_model_exclude_none=True
)
def read_workouts(
    session: db.SessionDep,
    current_user: auth.CurrentUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WorkoutPlan]:
    statement = (
        select(WorkoutPlan)
        .where(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.id)
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


@router.get(
    "/overview",
    response_model=list[WorkoutOverviewPublic],
    response_model_exclude_none=True,
)
def read_workout_overview(
    session: db.SessionDep,
    current_user: auth.CurrentUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WorkoutOverviewPublic]:
    workouts = read_workouts(session, current_user, offset, limit)
    if not workouts:
        return []

    workout_ids = [workout.id for workout in workouts]
    week_start = services.current_week_start()
    completion_counts = dict(
        session.exec(
            select(WorkoutCompletion.workout_id, func.count(WorkoutCompletion.id))
            .where(
                WorkoutCompletion.user_id == current_user.id,
                WorkoutCompletion.workout_id.in_(workout_ids),
                WorkoutCompletion.completed_on >= week_start.isoformat(),
            )
            .group_by(WorkoutCompletion.workout_id)
        ).all()
    )
    unfinished_ids = set(
        session.exec(
            select(WorkoutSession.workout_id).where(
                WorkoutSession.user_id == current_user.id,
                WorkoutSession.workout_id.in_(workout_ids),
            )
        ).all()
    )
    return [
        WorkoutOverviewPublic.model_validate(
            workout.model_dump()
            | {
                "completed_this_week": completion_counts.get(workout.id, 0),
                "week_start": week_start.isoformat(),
                "has_unfinished_workout": workout.id in unfinished_ids,
            }
        )
        for workout in workouts
    ]


@router.post(
    "",
    response_model=WorkoutPlanPublic,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_workout(
    workout_in: WorkoutPlanCreate,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutPlan:
    db_workout = WorkoutPlan.model_validate(
        workout_in.model_dump(mode="json", exclude_none=True)
        | {"user_id": current_user.id}
    )
    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)
    return db_workout


@router.get(
    "/recent-completions",
    response_model=list[RecentWorkoutPublic],
    response_model_exclude_none=True,
)
def read_recent_completions(
    session: db.SessionDep,
    current_user: auth.CurrentUser,
    limit: Annotated[int, Query(ge=1, le=3)] = 3,
) -> list[RecentWorkoutPublic]:
    return [
        RecentWorkoutPublic(
            completed_on=completion.completed_on,
            workout_name=workout_name,
            checked_exercises=completion.checked_exercises,
        )
        for completion, workout_name in services.recent_completions(
            session, current_user.id, limit
        )
    ]


@router.get("/progress/history", response_model=list[WorkoutHistoryWeekPublic])
def read_workout_progress_history(
    session: db.SessionDep,
    current_user: auth.CurrentUser,
    weeks: Annotated[int, Query(ge=1, le=52)] = 12,
) -> list[WorkoutHistoryWeekPublic]:
    workouts = session.exec(
        select(WorkoutPlan).where(WorkoutPlan.user_id == current_user.id)
    ).all()
    if not workouts:
        return []

    first_week = services.current_week_start() - timedelta(weeks=weeks - 1)
    completion_dates = session.exec(
        select(WorkoutCompletion.completed_on).where(
            WorkoutCompletion.user_id == current_user.id,
            WorkoutCompletion.completed_on >= first_week.isoformat(),
        )
    ).all()
    weekly_counts: dict[str, int] = {}
    for completed_on in completion_dates:
        day = date.fromisoformat(completed_on)
        week_start = (day - timedelta(days=day.weekday())).isoformat()
        weekly_counts[week_start] = weekly_counts.get(week_start, 0) + 1

    weekly_target = sum(workout.frequency_per_week for workout in workouts)
    weeks_list = [(first_week + timedelta(weeks=n)).isoformat() for n in range(weeks)]
    return [
        WorkoutHistoryWeekPublic(
            week_start=week,
            completed_sessions=weekly_counts.get(week, 0),
            weekly_target=weekly_target,
        )
        for week in weeks_list
    ]


# --- AI coach -------------------------------------------------------------


def _history(session: Session, user_id: int) -> list[HistoryItem]:
    items = []
    for completion, name in services.recent_completions(session, user_id):
        exercises = [
            {
                "name": exercise.get("name") or exercise.get("exercise", "Exercise"),
                "reps": str(exercise.get("reps") or exercise.get("count", "")),
            }
            for exercise in completion.checked_exercises
        ]
        items.append(
            HistoryItem.model_validate(
                {
                    "workout_name": name,
                    "completed_on": completion.completed_on,
                    "exercises": exercises,
                }
            )
        )
    return items


def _ask_ai(ai: AIClientDep, request: PlanRequest) -> WorkoutPlanDraft:
    """Call the AI before any database write, mapping failures to 503 / 502."""
    try:
        return ai.plan(request)
    except AIServiceUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, AI_UNAVAILABLE
        ) from exc
    except AIServiceBadOutput as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, AI_BAD_OUTPUT) from exc


def _exercises(draft: WorkoutPlanDraft) -> list[dict]:
    return [
        exercise.model_dump(exclude={"notes"} if not exercise.notes else set())
        for exercise in draft.exercises
    ]


def _validated_plan(data: dict) -> WorkoutPlanCreate:
    try:
        return WorkoutPlanCreate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, AI_BAD_OUTPUT) from exc


@router.post(
    "/generate",
    response_model=GeneratedWorkoutPublic,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def generate_workout(
    body: GeneratePlanRequest,
    ai: AIClientDep,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> GeneratedWorkoutPublic:
    request = PlanRequest.model_validate(
        body.model_dump() | {"recent_history": _history(session, current_user.id)}
    )
    draft = _ask_ai(ai, request)
    plan = _validated_plan(
        {
            "title": draft.title,
            "goal": body.goal,
            "experience_level": body.experience_level,
            "frequency_per_week": draft.frequency_per_week,
            "emoji": draft.icon,
            "exercises": _exercises(draft),
        }
    )
    workout = create_workout(plan, session, current_user)
    return GeneratedWorkoutPublic.model_validate(
        workout.model_dump() | {"coach_notes": draft.coach_notes}
    )


@router.post(
    "/{workout_id}/generate",
    response_model=GeneratedWorkoutPublic,
    response_model_exclude_none=True,
)
def regenerate_exercises(
    workout_id: int,
    body: RegenerateExercisesRequest,
    ai: AIClientDep,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> GeneratedWorkoutPublic:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    request = PlanRequest.model_validate(
        body.model_dump()
        | {
            "goal": workout.goal,
            "experience_level": workout.experience_level,
            "days_per_week": workout.frequency_per_week,
            "plan_name": workout.title,
            "recent_history": _history(session, current_user.id),
        }
    )
    draft = _ask_ai(ai, request)
    exercises = _validated_plan(
        {"title": workout.title, "exercises": _exercises(draft)}
    ).model_dump(mode="json", exclude_none=True)["exercises"]
    updated = update_workout(
        workout_id, WorkoutPlanUpdate(exercises=exercises), session, current_user
    )
    return GeneratedWorkoutPublic.model_validate(
        updated.model_dump() | {"coach_notes": draft.coach_notes}
    )


# --- Single plan ----------------------------------------------------------


@router.get(
    "/{workout_id}",
    response_model=WorkoutPlanPublic,
    response_model_exclude_none=True,
)
def read_workout(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutPlan:
    return services.get_workout_or_404(session, workout_id, current_user.id)


@router.patch(
    "/{workout_id}",
    response_model=WorkoutPlanPublic,
    response_model_exclude_none=True,
)
def update_workout(
    workout_id: int,
    workout_in: WorkoutPlanUpdate,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> WorkoutPlan:
    db_workout = services.get_workout_or_404(session, workout_id, current_user.id)
    workout_data = workout_in.model_dump(
        mode="json", exclude_unset=True, exclude_none=True
    )
    # Changing the exercise list invalidates any half-finished session.
    if (
        "exercises" in workout_data
        and workout_data["exercises"] != db_workout.exercises
    ):
        services.discard_unfinished_session(session, current_user.id, workout_id)

    for key, value in workout_data.items():
        setattr(db_workout, key, value)

    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)
    return db_workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    session: db.SessionDep,
    current_user: auth.CurrentUser,
) -> None:
    workout = services.get_workout_or_404(session, workout_id, current_user.id)
    completions = session.exec(
        select(WorkoutCompletion).where(
            WorkoutCompletion.workout_id == workout.id,
            WorkoutCompletion.user_id == current_user.id,
        )
    ).all()
    for completion in completions:
        session.delete(completion)
    services.discard_unfinished_session(session, current_user.id, workout.id)
    session.delete(workout)
    session.commit()
