# Fitness Planner
An AI-powered workout routine and fitness goal planner that generates personalized training schedules.

**Purpose:** This tool prevents disorganized tracking by providing custom, structured AI-driven workout plans tailored to user goals.

**Operational principle:** After a user inputs their goals and preferences and clicks "Generate", the backend calls the AI service, processes the structured JSON output, and saves the workout plan to SQLite; afterwards, the user can view, edit, or track their active routine.

## User stories
1. As a user, I can input my fitness goals and current fitness level so that I receive a personalized workout routine.
2. As a user, I can view my active workout plan so that I know which exercises to perform each day.
3. As a user, I can update or delete my workout routine so that I can adapt it as I progress.

## Data sketch
`WorkoutPlan`: title (text, 1–200 chars), goal (text, 1–100 chars), duration_weeks (integer, 1–52, default 4), exercises (text, at most 5000 chars, one per line), created_at (timestamp).

## The AI service
Input: User profile, goals, available equipment, and weekly time commitment.  
Structured output: A structured JSON object containing a weekly breakdown of workout routines, sets, reps, and notes.

## Data flow
browser -> frontend (Streamlit) :8501 -> backend (FastAPI) :8000 -> SQLite (only the backend) -> ai-service (FastAPI + Pydantic AI) :8001 (called only by the backend)

## AI use
Tools: Gemeni · Help received: Structuring the initial FastAPI backend layout and README template · Checks I ran: Verified `/health` endpoint locally using `curl`.

## Open-source shortlist
| Repository | Stars (date checked) | License | Why it fits me |
|---|---|---|---|
| fastapi/fastapi | 103,177 (2026-10-17) | MIT | Core framework used for the backend API |
| streamlit/streamlit | 35,500 (2026-10-17) | Apache-2.0 | Potential frontend interface candidate |
| pydantic/pydantic-ai | 4,200 (2026-10-17) | MIT | Framework for structured AI outputs |

## How to run
1. Clone the repository and navigate to the project root.
2. Navigate to the backend directory and start the FastAPI development server:
   ```bash
   cd backend
   uv run fastapi dev