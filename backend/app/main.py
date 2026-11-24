from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import auth
from app.db import database as db
from app.routers import sessions, workouts
from app.services import current_week_start

__all__ = ["app", "current_week_start"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    db.migrate_workout_emoji()
    db.migrate_completion_exercises()
    db.migrate_workout_session_results()
    db.migrate_legacy_exercises()

    yield

    db.engine.dispose()


app = FastAPI(
    title="Fitness Planner API",
    description=(
        "Accounts, workout plans, live training sessions and weekly progress. "
        "AI plan generation is delegated to the ai-service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(workouts.router)
app.include_router(sessions.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness only: never calls the AI service."""
    return {"status": "ok"}
