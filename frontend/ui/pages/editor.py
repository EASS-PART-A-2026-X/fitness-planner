"""Create and edit pages share one plan form."""

import random

import streamlit as st

import fitness_planner_api as api
from ui.components import WORKOUT_ICONS, icon_id_for_workout, page_header, plain
from ui.forms import exercise_editor, plan_details, show_errors, validate_workout
from ui.state import go, notify, set_page_state


def render_create(token: str) -> None:
    if st.button("← All plans", key="create-back"):
        go("plans")
    page_header(
        "Build your routine",
        "Create a workout",
        "Set your weekly rhythm, add each movement, and dial in work and recovery.",
    )
    version = st.session_state.setdefault("create-version", 0)
    prefix = f"create-{version}"
    icon_key = f"{prefix}-icon"
    if icon_key not in st.session_state:
        st.session_state[icon_key] = random.choice(tuple(WORKOUT_ICONS))

    details = plan_details(
        prefix, None, st.session_state[icon_key], "An icon is assigned automatically."
    )
    exercises = exercise_editor(prefix)
    if st.button(
        "Create workout", key=f"{prefix}-submit", type="primary", width="stretch"
    ):
        workout = details | {"exercises": exercises}
        if errors := validate_workout(workout):
            show_errors(errors)
            return
        try:
            created = api.create_workout(token, workout)
        except api.BackendError as exc:
            st.error(str(exc))
            return
        st.session_state["create-version"] += 1
        set_page_state("plans")
        notify(f"Created {plain(created['title'])}.")


def render_edit(token: str, workout_id: int) -> None:
    if st.button("← Back to plan", key="edit-back"):
        st.session_state.pop("delete_confirmation", None)
        go("plan", workout_id=workout_id)
    try:
        workout = api.read_workout(token, workout_id)
    except api.BackendError as exc:
        st.error(str(exc))
        return

    page_header("Make it yours", "Edit workout", "Adjust your plan as you progress.")
    prefix = f"edit-{workout_id}"
    icon_id = icon_id_for_workout(workout.get("emoji", ""), workout_id)
    details = plan_details(prefix, workout, icon_id, "This plan keeps its icon.")
    changes = details | {"exercises": exercise_editor(prefix, workout["exercises"])}

    save_col, delete_col = st.columns([3, 1])
    if save_col.button(
        "Save changes", key=f"{prefix}-save", type="primary", width="stretch"
    ):
        if errors := validate_workout(changes):
            show_errors(errors)
        else:
            try:
                api.update_workout(token, workout_id, changes)
            except api.BackendError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop(f"{prefix}-exercise-rows", None)
                st.session_state.pop(f"session-{workout_id}-exercise-index", None)
                st.session_state.pop("delete_confirmation", None)
                set_page_state("plan", workout_id=workout_id)
                notify(f"Saved {plain(changes['title'])}.")
    if delete_col.button("Delete", key=f"{prefix}-delete", width="stretch"):
        st.session_state["delete_confirmation"] = workout_id
        st.rerun()

    if st.session_state.get("delete_confirmation") == workout_id:
        st.warning(f"Delete {plain(workout['title'])}? This cannot be undone.")
        confirm_col, keep_col = st.columns(2)
        with confirm_col, st.container(key="fp-danger"):
            if st.button(
                "Yes, delete workout",
                key=f"{prefix}-confirm-delete",
                type="primary",
                width="stretch",
            ):
                try:
                    api.delete_workout(token, workout_id)
                except api.BackendError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop("delete_confirmation", None)
                    st.session_state.pop(f"{prefix}-exercise-rows", None)
                    set_page_state("plans")
                    notify(f"Deleted {plain(workout['title'])}.")
        if keep_col.button(
            "Keep workout", key=f"{prefix}-cancel-delete", width="stretch"
        ):
            st.session_state.pop("delete_confirmation", None)
            st.rerun()
