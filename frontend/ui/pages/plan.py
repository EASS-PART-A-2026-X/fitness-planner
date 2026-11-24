"""One plan: its exercises, weekly progress, AI refresh and the start button."""

import streamlit as st

import fitness_planner_api as api
from ui.components import (
    card,
    chip,
    coach_note,
    exercise_list,
    html_block,
    plain,
    safe_html,
    section,
    segments,
    workout_icon,
)
from ui.pages.coach import EQUIPMENT_LABELS
from ui.state import go, notify


def plan_heading(workout: api.WorkoutPlan, eyebrow: str) -> None:
    chips = "".join(
        chip(text)
        for text in (
            workout["goal"],
            f"{workout['frequency_per_week']}× / week",
            workout["experience_level"],
        )
    )
    html_block(
        f'<div class="fp-eyebrow">{safe_html(eyebrow)}</div>'
        '<div class="fp-workout" style="margin:.5rem 0 1.5rem">'
        f"{workout_icon(workout.get('emoji', ''), workout['id'])}"
        f'<div><div class="fp-page-title" style="margin:0">{safe_html(workout["title"])}</div>'
        f'<div class="fp-meta">{chips}</div></div></div>'
    )


def ai_refresh(token: str, workout_id: int) -> None:
    with st.expander("✦ Refresh exercises with AI"):
        st.caption(
            "The coach rebuilds this plan's exercises from its goal and your last "
            "session with it."
        )
        equipment = st.multiselect(
            "Equipment (optional, bodyweight if empty)",
            api.EQUIPMENT,
            format_func=EQUIPMENT_LABELS.get,
            key=f"plan-{workout_id}-equipment",
        )
        minutes = st.slider(
            "Minutes per workout",
            10,
            120,
            45,
            step=5,
            key=f"plan-{workout_id}-minutes",
        )
        notes = st.text_input(
            "Short note for the coach (optional)",
            max_chars=200,
            key=f"plan-{workout_id}-notes",
        )
        if st.button(
            "Generate exercises with AI",
            key=f"plan-{workout_id}-generate-exercises",
            width="stretch",
        ):
            try:
                with st.spinner("Your coach is rebuilding this plan..."):
                    updated = api.regenerate_exercises(
                        token, workout_id, minutes, equipment, notes.strip()
                    )
            except api.BackendError as exc:
                st.error(str(exc))
                return
            st.session_state[f"plan-{workout_id}-coach-notes"] = updated.get(
                "coach_notes", ""
            )
            backup = updated.get("plan_source") == "offline"
            notify(
                f"Updated {plain(updated['title'])} with new exercises"
                + (
                    " from the backup coach (the AI coach is busy right now)."
                    if backup
                    else "."
                )
            )


def render(token: str, workout_id: int) -> None:
    if st.button("← All plans", key="plan-back"):
        go("plans")
    try:
        workout = api.read_workout(token, workout_id)
        progress = api.workout_progress(token, workout_id)
        saved = api.read_workout_session(token, workout_id)
    except api.BackendError as exc:
        st.error(str(exc))
        return
    active = saved.get(
        "is_active", bool(saved.get("checked_exercises") or saved.get("completed_sets"))
    )

    plan_heading(workout, "Workout plan")
    main_col, side_col = st.columns([1.7, 1], gap="large")
    with main_col:
        section("Planned exercises")
        with card():
            coach_note(st.session_state.get(f"plan-{workout_id}-coach-notes", ""))
            exercise_list(workout["exercises"])
        ai_refresh(token, workout_id)

    with side_col:
        section("This week")
        with card():
            html_block(
                segments(
                    progress["completed_this_week"], progress["frequency_per_week"]
                )
            )
            if active:
                html_block(
                    '<div class="fp-meta" style="margin-top:.8rem">'
                    f"{chip('Workout started · resume where you left off', live=True)}</div>"
                )
            st.write("")
            if st.button(
                "Resume workout ▶" if active else "Start workout ▶",
                key="start-workout",
                type="primary",
                width="stretch",
            ):
                try:
                    api.start_workout_session(token, workout_id)
                except api.BackendError as exc:
                    st.error(f"Could not start your workout. {exc}")
                else:
                    go("detail", workout_id=workout_id)
            if st.button("Edit plan", key="edit-workout", width="stretch"):
                go("edit", workout_id=workout_id)
