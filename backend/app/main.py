from fastapi import FastAPI
from app.models.workout import WorkoutPlan

app = FastAPI(title="Fitness Planner API")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/workouts/")
def create_workout_plan(plan: WorkoutPlan):
    return {
        "message": "Workout plan successfully validated and received!",
        "plan": plan
    }