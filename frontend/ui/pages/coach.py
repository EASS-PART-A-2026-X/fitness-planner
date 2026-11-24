"""AI Coach: describe a goal, get a stored plan back from the backend."""

import streamlit as st

import fitness_planner_api as api
from ui.components import (
    card,
    chip,
    coach_note,
    exercise_list,
    html_block,
    page_header,
    safe_html,
    workout_icon,
)
from ui.state import go

LEVELS = ("beginner", "intermediate", "advanced")
EQUIPMENT_LABELS = {
    "bodyweight": "Bodyweight",
    "dumbbells": "Dumbbells",
    "barbell": "Barbell",
    "kettlebell": "Kettlebell",
    "bands": "Resistance bands",
    "machines": "Gym machines",
    "bike": "Bike",
    "pool": "Pool",
}


def plan_request_form(prefix: str) -> api.PlanRequest:
    goal_col, level_col = st.columns([2, 1])
    goal = goal_col.text_input(
        "Goal",
        max_chars=100,
        placeholder="e.g. Build strength, run a 5k, fix my posture",
        key=f"{prefix}-goal",
    )
    level = level_col.selectbox("Experience level", LEVELS, key=f"{prefix}-level")
    equipment = st.multiselect(
        "Equipment you have",
        api.EQUIPMENT,
        default=["bodyweight"],
        format_func=EQUIPMENT_LABELS.get,
        key=f"{prefix}-equipment",
    )
    days_col, minutes_col = st.columns(2)
    days = days_col.slider("Days per week", 1, 7, 3, key=f"{prefix}-days")
    minutes = minutes_col.slider(
        "Minutes per session", 10, 120, 45, step=5, key=f"{prefix}-minutes"
    )
    notes = st.text_area(
        "Anything the coach should know? (optional)",
        max_chars=500,
        placeholder="Injuries, preferences, what you liked last time...",
        key=f"{prefix}-notes",
    )
    return {
        "goal": goal.strip(),
        "experience_level": level,
        "equipment": equipment,
        "days_per_week": days,
        "minutes_per_session": minutes,
        "notes": notes.strip(),
    }


def check_request(request: api.PlanRequest) -> list[str]:
    errors = []
    if not request["goal"]:
        errors.append("Tell the coach your goal.")
    if not request["equipment"]:
        errors.append("Pick at least one kind of equipment.")
    return errors


def show_result(result: api.GeneratedWorkout) -> None:
    with card():
        chips = "".join(
            chip(text)
            for text in (
                result["goal"],
                f"{result['frequency_per_week']}× / week",
                f"{len(result['exercises'])} exercises",
            )
        )
        html_block(
            '<div class="fp-eyebrow">Saved to your plans</div>'
            '<div class="fp-workout" style="margin:.6rem 0 .3rem">'
            f"{workout_icon(result.get('emoji', ''), result['id'])}"
            f'<div><div class="fp-workout-title">{safe_html(result["title"])}</div>'
            f'<div class="fp-meta">{chips}</div></div></div>'
        )
        coach_note(result.get("coach_notes", ""))
        exercise_list(result["exercises"])
        open_col, again_col = st.columns(2)
        if open_col.button(
            "Open plan", key="coach-open", type="primary", width="stretch"
        ):
            st.session_state.pop("coach-result", None)
            go("plan", workout_id=result["id"])
        if again_col.button("Draft another", key="coach-again", width="stretch"):
            st.session_state.pop("coach-result", None)
            st.rerun()


def render(token: str) -> None:
    page_header(
        "AI Coach",
        "Plan it with AI",
        "Describe your goal, your gear and your time. The coach drafts a routine "
        "from a vetted exercise catalog and saves it to your plans.",
    )
    if result := st.session_state.get("coach-result"):
        show_result(result)
        return

    with card():
        request = plan_request_form("coach")
        submitted = st.button(
            "✦ Generate my plan", key="coach-submit", type="primary", width="stretch"
        )
    if not submitted:
        return
    if errors := check_request(request):
        st.warning("Please fix: " + " ".join(errors))
        return
    try:
        with st.spinner("Your coach is drafting a plan..."):
            result = api.generate_plan(token, request)
    except api.BackendError as exc:
        # Inputs keep their values, so the user can simply try again.
        st.error(str(exc))
        return
    st.session_state["coach-result"] = result
    st.rerun()
