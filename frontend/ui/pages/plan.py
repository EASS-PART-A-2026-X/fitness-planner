"""One plan: its exercises, weekly progress, AI refresh and the start button."""

import streamlit as st

import fitness_planner_api as api
from ui import analytics
from ui.catalog import DEFAULT_MINUTES, EQUIPMENT_LABELS, MINUTE_CHOICES, TYPES_BY_ID
from ui.components import (
    art_svg,
    back_link,
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
from ui.forms import pick
from ui.state import go, notify


def _identity(workout: api.WorkoutPlan, eyebrow: str) -> str:
    """Picture, eyebrow, title and tags of a plan, as one HTML block."""
    chips = "".join(
        chip(text)
        for text in (
            workout["goal"],
            f"{workout['frequency_per_week']}× / week",
            workout["experience_level"],
        )
    )
    kind = TYPES_BY_ID.get(workout.get("emoji", ""))
    picture = (
        f'<div class="fp-type-art tone-{kind.tone}">{art_svg(kind.art)}</div>'
        if kind
        else workout_icon(workout.get("emoji", ""), workout["id"])
    )
    return (
        f'<div class="fp-plan-id">{picture}<div>'
        f'<div class="fp-eyebrow">{safe_html(eyebrow)}</div>'
        f'<div class="fp-page-title">{safe_html(workout["title"])}</div>'
        f'<div class="fp-meta">{chips}</div></div></div>'
    )


def plan_heading(workout: api.WorkoutPlan, eyebrow: str) -> None:
    html_block(f'<div class="fp-plan-heading">{_identity(workout, eyebrow)}</div>')


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
        minutes = pick(
            st,
            "Minutes per workout",
            MINUTE_CHOICES,
            f"plan-{workout_id}-minutes",
            DEFAULT_MINUTES,
            default=DEFAULT_MINUTES,
            format_func=lambda n: f"{n} min",
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
            analytics.capture(
                "ai_exercises_regenerated",
                workout_type=updated.get("emoji", ""),
                plan_source="offline" if backup else "ai",
                exercise_count=len(updated["exercises"]),
            )
            notify(
                f"Updated {plain(updated['title'])} with new exercises"
                + (
                    " from the backup coach (the AI coach is busy right now)."
                    if backup
                    else "."
                )
            )


def render(token: str, workout_id: int) -> None:
    if back_link("← All plans", "plan-back"):
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

    # One compact header panel: who the plan is on the left, this week's
    # progress and the actions on the right, so the exercises start right below.
    with st.container(key="fp-plan-hero"):
        id_col, action_col = st.columns(
            [1.7, 1], gap="large", vertical_alignment="center"
        )
        id_col.markdown(_identity(workout, "Workout plan"), unsafe_allow_html=True)
        with action_col:
            html_block(
                '<div class="fp-eyebrow">This week</div>'
                + segments(
                    progress["completed_this_week"], progress["frequency_per_week"]
                )
                + (
                    f'<div class="fp-meta">{chip("Started · resume where you left off", live=True)}</div>'
                    if active
                    else ""
                )
            )
            start_col, edit_col = st.columns([1.6, 1])
            if start_col.button(
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
                    analytics.capture(
                        "workout_started",
                        workout_type=workout.get("emoji", ""),
                        resumed=bool(active),
                        exercise_count=len(workout["exercises"]),
                    )
                    go("detail", workout_id=workout_id)
            if edit_col.button("Edit plan", key="edit-workout", width="stretch"):
                go("edit", workout_id=workout_id)

    section("Planned exercises")
    with card():
        coach_note(st.session_state.get(f"plan-{workout_id}-coach-notes", ""))
        exercise_list(workout["exercises"])
    ai_refresh(token, workout_id)
