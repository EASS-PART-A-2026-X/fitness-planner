# Fitness Planner

An AI-powered workout planner. Describe your goal, your equipment and your time;
an AI coach drafts a structured routine, and the app guides you through every
set, times your rests, and tracks weekly consistency.

**Purpose:** prevent disorganized training by turning goals into structured,
trackable plans.

**Operational principle:** each person signs in before managing plans, and the
backend checks ownership on every request. Users create plans by hand or with
the AI coach, then start a session: each set and its actual reps are saved as
they go, so a session can be resumed later or cancelled without counting.
Finishing a session records a completion; dashboards and analytics compare
completed sessions with the weekly targets of all plans.

## User stories
1. As a user, I can create an account and sign in so that my plans are private.
2. As a user, I can ask the AI coach for a plan that fits my goal, equipment and
   time, and it is saved to my plans.
3. As a user, I can create, view, edit and delete plans by hand.
4. As a user, I can run a session: pick an exercise, record actual reps, rest
   with a timer, and see completed sets.
5. As a user, I can see my dashboard, recent activity and weekly analytics.

## Architecture

```
browser ──► frontend (Streamlit) :8501 ──► backend (FastAPI) :8000 ──► ai-service (FastAPI + Pydantic AI) :8001
                                                   │
                                                   └──► SQLite (only the backend touches it)
```

| Service | Folder | What it owns |
|---|---|---|
| frontend | `frontend/` | UI only. `fitness_planner_api.py` is the only module that makes HTTP calls; pages live in `ui/pages/`. |
| backend | `backend/` | Accounts, plans, sessions, completions, SQLite. Calls the AI service through `app/ai_client.py`. |
| ai-service | `ai-service/` | A Pydantic AI agent (`app/agent.py`) that drafts plans from a vetted exercise catalog. |

Streamlit was chosen because the product is a form-and-dashboard app that one
Python developer can build and test end to end (AppTest); the accepted cost is
less control over layout than a React frontend, handled with a small theme layer
(`frontend/ui/theme.py`).

## Run it

### With Docker Compose (recommended)

```bash
docker compose up --build --wait     # three healthy services
```

Open <http://localhost:8501>. The backend API docs are at
<http://localhost:8000/docs>. The AI service has **no published port**: only
the backend can reach it.

```bash
docker compose down        # stop; your data stays in the backend-data volume
docker compose down -v     # ⚠ stop AND delete all accounts and plans
```

No `.env` is needed: the AI coach defaults to an offline, rule-based model.
To use a real LLM for free, see [Free AI setup](#free-ai-setup).

### Locally (three terminals)

```bash
cd ai-service && uv run fastapi dev --port 8001
cd backend    && uv run fastapi dev                      # :8000
cd frontend   && uv run streamlit run streamlit_app.py   # :8501
```

| Variable | Used by | Default |
|---|---|---|
| `DATABASE_URL` | backend | `sqlite:///./data/database.db` |
| `AI_SERVICE_URL` | backend | `http://localhost:8001` |
| `BACKEND_URL` | frontend | `http://localhost:8000` |
| `AI_MODEL` | ai-service | `test` (offline rule-based coach) |
| `AI_FALLBACK` | ai-service | `baseline` (use the offline coach when the real model fails; `off` to disable) |
| `AI_COST_LIMIT_USD` | ai-service | unset (no cost cap) |

There is no seed data: every plan belongs to an account, so a fresh database
starts empty and you create an account on the sign-in screen.

## Test

```bash
cd ai-service && uv run pytest     # 33 passed, offline, no API key
cd backend    && uv run pytest     # 90 passed, AI calls faked with httpx.MockTransport
cd frontend   && uv run pytest     # 50 passed (AppTest + respx + live-backend integration)
```

Each folder also passes `uv run ruff check .` and `uv run ruff format --check .`.

Browser end-to-end tests start all three services themselves:

```bash
cd frontend
uv run playwright install chromium        # once (add --with-deps on WSL/Ubuntu)
uv run pytest -m e2e                      # 2 passed
```

## The AI service

**Input** (`PlanRequest`): goal, experience level, equipment, days per week,
minutes per session, free-text notes, and the user's last three completed
workouts (added by the backend). **Output** (`WorkoutPlanDraft`): title, icon,
frequency, 1–12 exercises with sets, per-set reps, rest and a coaching cue,
plus coach notes.

The agent has:
- `output_type=WorkoutPlanDraft` and instructions that treat every user field as
  data (prompt-injection defence);
- a deps tool, `exercises_for_equipment`, that lists catalog moves for the
  user's gear, and a plain tool, `estimate_minutes`;
- an output validator that sends `ModelRetry` when an exercise is unknown or
  needs missing equipment, the reps list does not match the sets, the session
  is over the minute budget, or the frequency is wrong;
- `UsageLimits(request_limit=5, tool_calls_limit=5, total_tokens_limit=20_000)`
  and a 25 s timeout per run.

### Free AI setup

The app never needs to spend money on AI:

1. Get a free Gemini API key at <https://aistudio.google.com/apikey>. Do **not**
   enable billing on that Google project, so it can never charge you.
2. Create `.env` in the repository root (it is git-ignored):
   ```bash
   AI_MODEL=google:gemini-2.5-flash-lite
   GOOGLE_API_KEY=your-key
   ```
3. Restart: `docker compose up --build --wait`, or restart the ai-service.

How it stays within the free tier and never "runs out":
- **Fewer tokens per plan.** Gemini's hidden "thinking" tokens are turned off
  (`thinking_budget=0`), the catalog tool returns only the fields the model
  needs, and each run is capped at 5 requests and 20,000 tokens.
- **Offline fallback.** If the daily or per-minute free quota is used up (429),
  the key is missing or wrong, the model is slower than 20 s, or it keeps
  returning invalid plans, the ai-service answers with the offline rule-based
  coach instead of an error. Users always get a plan.
- **See which one answered.** The response header `X-Plan-Source` is `ai` or
  `offline`, and the ai-service log prints `plan fell back to offline planner: …`
  whenever the fallback is used.

### Contract

| Call | Request | Success | Errors |
|---|---|---|---|
| ai-service `POST /plan` | `PlanRequest` (`extra="forbid"`) | 200 `WorkoutPlanDraft` | 422 bad request · 429 budget · 502 invalid output · 500 provider · 504 timeout |
| backend `POST /workouts/generate` | goal, level, equipment, days, minutes, notes | 201 stored plan + `coach_notes` | 422 (AI never called) · 503 · 502 |
| backend `POST /workouts/{id}/generate` | equipment, minutes, notes | 200 plan with new exercises | 404 · 422 · 503 · 502 |

The ai-service owns the schema. The backend keeps its own copy in
`backend/app/ai_client.py`, validates every response against it, and
`backend/tests/test_contract.py` compares the copy with a snapshot in both
directions. After an intentional change to the AI schema, regenerate the snapshot:

```bash
cd ai-service && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../backend/tests/ai_openapi.json
```

### Failures

With a real model and `AI_FALLBACK=baseline` (the default), quota (429),
provider errors, a missing key, timeouts and invalid model output never reach
the user: the ai-service answers 200 with an offline plan. The table below
shows what happens when the AI service itself is unreachable, or when
`AI_FALLBACK=off`.

Only one layer retries each failure: the agent retries invalid model output
(`retries=2`), and the backend retries network failures and 503/504
(3 attempts, exponential backoff). The frontend never retries.

| Failure | Backend status | What the user sees | Who retries |
|---|---|---|---|
| AI service down / refused / DNS | 503 | "The AI coach is unavailable right now. Your plans still work; try again in a minute." | backend |
| AI read timeout, 503 or 504 | 503 | same as above | backend |
| AI budget exceeded (429) or provider error (500) | 503 | same as above | nobody |
| AI output never valid (502), AI 4xx, or a broken body | 502 | "The AI coach returned a plan we could not use. Try again or adjust your request." | nobody (the agent already retried) |
| Invalid form input | 422 | "Please fix: …" (the field is named) | nobody |
| Backend unreachable | none | "Cannot reach the backend at … Start it (docker compose up) and reload the page." | nobody |
| Reply lost after a write | none | "…Your change may have been saved. Reload the page and check before trying again." | nobody |

Timeout budget, from the outside in: frontend 100 s for AI routes; backend 30 s
read × 3 attempts; ai-service 25 s per run; then the model's usage limits.
`/health` never calls the AI service, and plan CRUD keeps working while the AI
service is down.

### Evals

`ai-service/evals/cases.yaml` holds 10 hand-written cases in four slices:
ordinary, injection, missing-field and ambiguous. Run them with:

```bash
cd ai-service
uv run python -m evals.run_evals                                      # offline baseline
AI_MODEL=google:gemini-2.5-flash EVAL_REPEAT=3 uv run python -m evals.run_evals
```

Assertions: reps match sets, respects equipment, fits the time budget,
frequency matches, ignores injection, avoids high-impact moves when the user
mentions joint pain. Score: `FocusMatch`, the share of exercises that train the
goal's focus.

| Date | `AI_MODEL` | Settings | Cases | Assertions passed | FocusMatch avg | Requests / case |
|---|---|---|---|---|---|---|
| 2026-11-23 | `test` (rule-based baseline) | repeat=1 | 10 | 60 / 60 (100%) | 0.75 | 1 |

## Data sketch
`WorkoutPlan`: `id`, `user_id` (owner), `title` (1–200 chars), `goal`
(1–100), `frequency_per_week` (1–7), `experience_level` (1–50), an icon id, and
`exercises` (a JSON array of 1–100 items). Structured exercises are
`{name 1–200, sets 1–100, reps "10, 10, 8", rest_seconds 0–3600, notes ≤200}`;
older plans that use `{exercise, count}` still work.
`WorkoutSession` stores an unfinished session's completed sets.
`WorkoutCompletion` stores each finished session with the reps actually
performed. Weekly progress uses the UTC calendar week (Monday to Sunday).

## Security notes
Passwords are stored as salted PBKDF2 hashes. Sessions are random bearer tokens
stored hashed on the server, valid for 30 days, and revoked on logout. The
frontend remembers the token in a cookie that is readable by JavaScript,
because Streamlit's cookie component cannot set `HttpOnly`. Use HTTPS outside
local development. API keys live only in the git-ignored `.env`.

## AI use
Tools: Gemini, GitHub CLI, Claude Code.
Help received: SQLModel persistence and CRUD (Gemini). Claude Code did the
following:
- split the backend into routers and services;
- added the ai-service (agent, tools, validator, error mapping, evals) and the
  backend AI client with retries;
- added the contract test and Docker Compose;
- split and restyled the Streamlit frontend with a dark theme and added the AI
  Coach page;
- updated the stale tests.

Checks I ran: `uv run pytest` and both ruff commands in all three folders,
`uv run pytest -m e2e`, the eval harness, and a manual click-through with the
AI service stopped to confirm the 503 message.

## Open-source shortlist
| Repository | Stars (date checked) | License | Why it fits me |
|---|---|---|---|
| fastapi/fastapi | 103,177 (2026-10-17) | MIT | Core framework used for the backend API |
| streamlit/streamlit | 35,500 (2026-10-17) | Apache-2.0 | The frontend framework |
| tldr-pages/tldr | 64.1k (2026-10-17) | MIT | Added a Hebrew translation |
