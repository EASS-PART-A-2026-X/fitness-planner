"""Page navigation, mirrored into the URL so a reload keeps the current view."""

import streamlit as st

PLAN_PAGES = {"plan", "detail", "edit"}
SECTIONS = {
    "home": "dashboard",
    "coach": "coach",
    "activities": "activities",
    "analytics": "analytics",
    "plans": "plans",
    "create": "plans",
    "plan": "plans",
    "detail": "plans",
    "edit": "plans",
}


def set_page_state(
    page: str,
    *,
    section: str | None = None,
    workout_id: int | None = None,
) -> None:
    st.session_state["page"] = page
    st.session_state["active_section"] = section or SECTIONS.get(page, "dashboard")
    if workout_id is not None:
        st.session_state["selected_workout_id"] = workout_id
    elif page not in PLAN_PAGES:
        st.session_state.pop("selected_workout_id", None)

    st.query_params["fp_view"] = page
    if workout_id is not None:
        st.query_params["fp_workout"] = str(workout_id)
    else:
        st.query_params.pop("fp_workout", None)


def go(page: str, *, workout_id: int | None = None) -> None:
    set_page_state(page, workout_id=workout_id)
    st.rerun()


def restore_page_from_url() -> None:
    page = st.query_params.get("fp_view")
    if page not in SECTIONS:
        page = "home"
    workout_id = st.query_params.get("fp_workout")
    if page in PLAN_PAGES:
        if workout_id and workout_id.isdigit():
            st.session_state["selected_workout_id"] = int(workout_id)
        else:
            page = "home"
    if page not in PLAN_PAGES:
        st.session_state.pop("selected_workout_id", None)
    st.session_state["page"] = page
    st.session_state["active_section"] = SECTIONS[page]


def notify(message: str) -> None:
    """Show a success message after the rerun that refreshes the data."""
    st.session_state["notice"] = message
    st.rerun()
