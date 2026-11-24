"""Popup dialogs. Deleting a plan always asks here first, wherever it starts.

The open dialog is remembered in session state and drawn once per run by
`render_pending`, so it stays open across reruns until the user picks a button
or dismisses it.
"""

import streamlit as st

import fitness_planner_api as api
from ui.components import html_block, plain, safe_html, workout_icon
from ui.state import notify, set_page_state

PENDING_KEY = "fp-delete-dialog"


def ask_delete(workout: api.WorkoutPlan, key_prefix: str) -> None:
    """Button callback: open the delete dialog for this plan."""
    st.session_state[PENDING_KEY] = {"workout": workout, "prefix": key_prefix}


def _close() -> None:
    st.session_state.pop(PENDING_KEY, None)


def _forget_plan(workout_id: int) -> None:
    """Drop every bit of UI state that belongs to a deleted plan."""
    prefixes = tuple(f"{kind}-{workout_id}-" for kind in ("edit", "session", "plan"))
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(prefixes):
            del st.session_state[key]


@st.dialog("Delete this plan?", on_dismiss=_close)
def _confirm_delete(token: str, workout: api.WorkoutPlan, key_prefix: str) -> None:
    workout_id = workout["id"]
    html_block(
        '<div class="fp-workout" style="margin:.25rem 0 1rem">'
        f"{workout_icon(workout.get('emoji', ''), workout_id)}"
        f'<div><div class="fp-workout-title">{safe_html(workout["title"])}</div>'
        '<div class="fp-exercise-note">This removes the plan and its progress. '
        "It can't be undone.</div></div></div>"
    )
    keep_col, delete_col = st.columns(2)
    if keep_col.button("Keep it", key=f"{key_prefix}-cancel-delete", width="stretch"):
        _close()
        st.rerun()
    with delete_col, st.container(key="fp-danger"):
        if st.button(
            "Delete plan",
            key=f"{key_prefix}-confirm-delete",
            type="primary",
            width="stretch",
        ):
            try:
                api.delete_workout(token, workout_id)
            except api.BackendError as exc:
                st.error(str(exc))
                return
            _close()
            _forget_plan(workout_id)
            set_page_state("plans")
            notify(f"Deleted {plain(workout['title'])}.")


def render_pending(token: str) -> None:
    if pending := st.session_state.get(PENDING_KEY):
        _confirm_delete(token, pending["workout"], pending["prefix"])
