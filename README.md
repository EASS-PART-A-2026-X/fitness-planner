<div align="center">

<img src="docs/rep.svg" width="180" alt="Rep, the Fitness Planner mascot: a round green buddy with a coral headband, waving">

# Fitness Planner

**Your training plan, a pocket coach, and a tiny green cheerleader named Rep.**

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-frontend-FF4B4B?logo=streamlit&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![Pydantic AI](https://img.shields.io/badge/Pydantic%20AI-coach-E92063)
![Tests](https://img.shields.io/badge/tests-221%20passing-10B981)

</div>

---

## 👋 Meet Rep

Most workouts don't fail at the gym. They fail the night before, when "I'll just
wing it" turns into skipping it. Fitness Planner fixes the boring part: you say
what you're training, an AI coach drafts the exercises, and Rep, the mascot in the
corner, waves, thinks, lifts, runs and cheers you through every page.

When you finish a workout, Rep jumps for joy in a full-screen confetti
celebration. You earned it.

## ✨ How it works, in three steps

| | Step | What happens |
|---|---|---|
| 🏃 | **Pick** | Choose a workout from a picture grid (running, yoga, pilates, upper body, HIIT, swimming… 12 in all) or name your own. |
| 📝 | **Plan** | Set your goal, sessions per week and level. Press **✦ Generate exercises** and the AI coach fills in sets, reps and rest, or tap quick-add chips and build it yourself. Change anything before you save. |
| 🎉 | **Train & celebrate** | Start a session, log the reps you *actually* did, rest with a countdown ring, and finish to a big celebration. Your streak and weekly chart update. |

## 🧰 What's inside

- **Picture-first plan builder.** Every workout type has its own line-art athlete, colour and starter exercises.
- **AI coach that drafts but never decides.** It suggests exercises; nothing is saved until you press *Create plan*. If the AI is busy, an offline backup coach steps in so you're never stuck.
- **A friendly exercise editor.** One "Reps" number for every set (or flip on *Different reps per set*), a rest slider, and a remove button on every row.
- **Guided live sessions.** Pick an exercise, log each set, skip or wait out the rest timer, and resume any time.
- **Progress you can see.** Dashboard, activity timeline, streaks and a 12-week consistency chart.
- **Safe deletes.** Deleting a plan, from the Plans list or the edit page, always asks first in a popup.
- **Private by default.** Accounts, hashed passwords and per-user ownership checks on every request.

## 🚀 Quick start

```bash
docker compose up --build --wait
```

Open <http://localhost:8501>, create an account, and pick your first workout.
No API key needed: the coach runs offline until you [add a free one](#free-ai-setup).

---

## The project, in detail

**Purpose:** prevent disorganized training by turning goals into structured,
trackable plans.

**Operational principle:** each person signs in before managing plans, and the
backend checks ownership on every request. Users create a plan in two steps
(pick a workout type, then fill in details and exercises, optionally drafted by
the AI coach), then start a session: each set and its actual reps are saved as
they go, so a session can be resumed later or cancelled without counting.
Finishing a session records a completion; dashboards and analytics compare
completed sessions with the weekly targets of all plans.

## User stories
1. As a user, I can create an account and sign in so that my plans are private.
2. As a user, I can pick a workout type and ask the AI coach to draft exercises
   that fit my goal, equipment and time, edit them, and save the plan.
3. As a user, I can create, view, edit and delete plans by hand; deleting always
   asks for confirmation.
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
| ai-service | `ai-service/` | A Pydantic AI agent (`app/agent.py`) that drafts workout plans, with an offline rule-based coach as fallback. |

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
| `POSTHOG_API_KEY` | frontend | unset (analytics off) |
| `POSTHOG_HOST` | frontend | `https://us.i.posthog.com` |

There is no seed data: every plan belongs to an account, so a fresh database
starts empty and you create an account on the sign-in screen.

## Test

```bash
cd ai-service && uv run pytest     # 50 passed, offline, no API key
cd backend    && uv run pytest     # 101 passed, AI calls faked with httpx.MockTransport
cd frontend   && uv run pytest     # 68 passed (AppTest + respx + live-backend integration)
```

Each folder also passes `uv run ruff check .` and `uv run ruff format --check .`.

Browser end-to-end tests start all three services themselves:

```bash
cd frontend
uv run playwright install chromium        # once (add --with-deps on WSL/Ubuntu)
uv run pytest -m e2e                      # 2 passed
```

## The AI service

The request is deliberately small, because every field is sent to the model:

**Input** (`PlanRequest`): goal (≤100 chars), experience level (≤30), workouts
per week, minutes per workout (10–180), and optionally a plan name (≤60), equipment, a short note (≤200) and
the last completed workout as up to 10 short lines such as
`"Goblet squat 12, 12, 10"` (the backend adds it). Empty optional fields are
left out of the JSON. **Output** (`WorkoutPlanDraft`): title (≤60), icon, 1–8
exercises with sets, per-set reps, rest and a short cue (≤80), and coach notes
(≤200).

The agent has:
- `output_type=WorkoutPlanDraft` and instructions that treat every user field as
  data (prompt-injection defence);
- two optional tools the model may call: a deps tool,
  `exercises_for_equipment` (example moves for the user's gear), and a plain
  tool, `estimate_minutes`. Instructions tell the model to answer directly, so
  a plan normally takes **one request**;
- an output validator that sends `ModelRetry` when an exercise needs equipment
  the user did not list (e.g. "Barbell deadlift" with only dumbbells) or reps
  are not numbers, and repairs a reps list of the wrong length and a session
  longer than the user's minutes (it drops sets, then exercises) itself
  instead of spending another request;
- `UsageLimits(request_limit=4, tool_calls_limit=15, total_tokens_limit=12_000)`,
  `max_tokens=1500` for the answer, an 8 s timeout per model call and a 25 s
  budget for the whole chain before the offline coach answers.

### Free AI setup

The app never needs to spend money on AI:

1. Get a free Gemini API key at <https://aistudio.google.com/apikey>. Do **not**
   enable billing on that Google project, so it can never charge you.
2. Create `.env` in the repository root (it is git-ignored):
   ```bash
   AI_MODEL=google:gemini-3.5-flash-lite,google:gemini-3.5-flash
   GOOGLE_API_KEY=your-key
   ```
3. Restart: `docker compose up --build --wait`, or restart the ai-service.

How it stays within the free tier and never "runs out":
- **A small request, usually one call.** Only goal, level, workouts per week
  and the optional fields you fill in are sent, as compact JSON. Measured with
  Gemini 3.5 Flash-Lite: about 900–2,000 tokens and 1–2 requests per plan
  (it was about 4,000 tokens and 3 requests before). Gemini's hidden
  "thinking" is kept at `thinking_level="low"`.
- **Several free models, failing fast.** `AI_MODEL` lists models in order
  (Flash-Lite, then Flash). Each call gets 8 s. A "high demand" (503) answer
  gets one quick retry after 0.75 s; a timeout, quota (429) or invalid answer
  moves straight to the next model. A bad or missing key stops the chain.
- **Offline fallback.** If the daily or per-minute free quota is used up (429),
  the key is missing or wrong, every model is busy or slow, or it keeps
  returning invalid plans, the ai-service answers with the offline rule-based
  coach instead of an error. Users always get a plan.
- **See which one answered.** The response header `X-Plan-Source` is `ai` or
  `offline`. The ai-service log prints `plan ok: model=… requests=… tokens=…`
  on success and, on failure, which model failed and how, e.g.
  `gemini-3.5-flash-lite busy (503); retrying in 0.75s`,
  `gemini-3.5-flash failed: timeout; trying the next model` and
  `plan used the offline coach: all models failed: … 503; … timeout`.
- **Friendly notice.** When the backup coach wrote the plan, the backend
  returns `plan_source: "offline"` and the Create page says so ("The AI
  coach is busy right now, so your backup coach drafted these exercises…"). To debug,
  set `AI_FALLBACK=off` in `.env`: failures then show "The AI coach is
  unavailable right now" instead of a backup plan.

### Contract

| Call | Request | Success | Errors |
|---|---|---|---|
| ai-service `POST /plan` | `PlanRequest` (`extra="forbid"`) | 200 `WorkoutPlanDraft` | 422 bad request · 429 budget · 502 invalid output · 500 provider · 504 timeout |
| backend `POST /workouts/draft` | goal, level, workouts/week, minutes; optional plan name, equipment, note | 200 draft (title, icon, exercises, `coach_notes`), **not stored** (used by the Create page) | 422 (AI never called) · 503 · 502 |
| backend `POST /workouts/generate` | same as `/draft` | 201 stored plan + `coach_notes` | 422 (AI never called) · 503 · 502 |
| backend `POST /workouts/{id}/generate` | minutes; optional equipment, note | 200 plan with new exercises | 404 · 422 · 503 · 502 |

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
uv run python -m evals.run_evals                     # offline coach (default)
EVAL_MODEL=google:gemini-3.5-flash-lite EVAL_REPEAT=3 uv run python -m evals.run_evals
```

`EVAL_MODEL` is separate from the app's `AI_MODEL`, so a plain eval run never
spends free-tier quota.

Assertions: reps match sets, respects equipment, fits the time budget, ignores injection, avoids
high-impact moves when the user mentions joint pain. Score: `ReasonableSize`
(1.0 for the requested 4–6 exercises).

| Date | Model | Settings | Cases | Assertions passed | ReasonableSize avg | Requests / case |
|---|---|---|---|---|---|---|
| 2026-11-24 | `test` (offline coach) | repeat=1 | 10 | 50 / 50 (100%) | 0.90 | 1 |

## Product analytics (PostHog)

Analytics are **off by default**. To turn them on, put your PostHog project key
in `.env` (and `POSTHOG_HOST=https://eu.i.posthog.com` for an EU project), then
restart the frontend:

```bash
POSTHOG_API_KEY=phc_your_project_key
```

`frontend/ui/analytics.py` sends events from the Streamlit server with the
PostHog Python SDK, in the background, so a slow or unreachable PostHog never
slows down or breaks a page. People are identified as `user-<account id>`;
usernames, passwords, plan titles, goals and notes are **never** sent, only
counts, workout types and which page or button was used.

| Event | When | Properties |
|---|---|---|
| `$pageview` | the visible page changes | `page` |
| `signed_up`, `logged_in`, `logged_out` | account actions | none |
| `workout_type_selected` | a picture card (or a custom name) is picked | `workout_type` |
| `ai_exercises_drafted` / `ai_draft_failed` | ✦ Generate exercises | `workout_type`, `plan_source`, `exercise_count`, `minutes_per_session`, `equipment_count` / `error` |
| `plan_created` | Create plan | `workout_type`, `custom_name`, `used_ai`, `exercise_count`, `sessions_per_week`, `experience_level` |
| `plan_updated`, `plan_deleted` | edit saved / delete confirmed | `workout_type`, `exercise_count` / `source` |
| `ai_exercises_regenerated` | AI refresh on a plan | `workout_type`, `plan_source`, `exercise_count` |
| `workout_started`, `workout_completed`, `workout_cancelled` | live sessions | `workout_type`, `resumed`, `sets_done`, `total_sets`, `exercise_count` |

Useful first insights: a funnel `workout_type_selected → plan_created →
workout_started → workout_completed`, and the share of `plan_created` with
`used_ai = true`.

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
- redesigned the UI (navy glow theme, glass cards, stat tiles), replaced the AI
  Coach page with the two-step picture-grid Create flow and the backend
  `/workouts/draft` endpoint, rebuilt the exercise editor, added delete
  dialogs, the finish-workout celebration and the mascot logo (`docs/rep.svg`);
- added optional PostHog product analytics (`frontend/ui/analytics.py`);
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
