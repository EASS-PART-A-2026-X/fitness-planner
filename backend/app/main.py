from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select

from app.db.database import create_db_and_tables, get_session
from app.models.workout import WorkoutPlan, WorkoutPlanCreate, WorkoutPlanUpdate

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Fitness Planner API", lifespan=lifespan)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/workouts/", response_model=WorkoutPlan)
def create_workout(workout_in: WorkoutPlanCreate, session: Session = Depends(get_session)):
    db_workout = WorkoutPlan.model_validate(workout_in.model_dump())
    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)
    return db_workout

@app.get("/workouts/", response_model=List[WorkoutPlan])
def read_workouts(user_id: Optional[int] = None, session: Session = Depends(get_session)):  # Updated to Optional[int]
    statement = select(WorkoutPlan)
    if user_id is not None:
        statement = statement.where(WorkoutPlan.user_id == user_id)
    workouts = session.exec(statement).all()
    return workouts

@app.get("/workouts/{workout_id}", response_model=WorkoutPlan)
def read_workout(workout_id: int, session: Session = Depends(get_session)):
    workout = session.get(WorkoutPlan, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    return workout

@app.put("/workouts/{workout_id}", response_model=WorkoutPlan)
def update_workout(workout_id: int, workout_in: WorkoutPlanUpdate, session: Session = Depends(get_session)):
    db_workout = session.get(WorkoutPlan, workout_id)
    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    
    workout_data = workout_in.model_dump(exclude_unset=True)
    for key, value in workout_data.items():
        setattr(db_workout, key, value)
        
    session.add(db_workout)
    session.commit()
    session.refresh(db_workout)
    return db_workout

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, session: Session = Depends(get_session)):
    workout = session.get(WorkoutPlan, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    session.delete(workout)
    session.commit()
    return {"ok": True}