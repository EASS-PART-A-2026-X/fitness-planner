import streamlit as st

import fitness_planner_api as api
from ui.components import brand, safe_html
from ui.session import clear_login
from ui.state import go

NAV_ITEMS = (
    ("dashboard", "home", "Dashboard"),
    ("plans", "plans", "Plans"),
    ("create", "create", "＋ Create"),
    ("activities", "activities", "Activity"),
    ("analytics", "analytics", "Analytics"),
)


def render() -> None:
    active = st.session_state.get("active_section", "dashboard")
    # Remember where Rep came from for this page visit only, so the mascot markup
    # (and its entrance animation) changes when the page changes, not on every rerun.
    visit = st.session_state.get("fp-mascot")
    if not visit or visit["section"] != active:
        visit = {"section": active, "previous": visit["section"] if visit else None}
        st.session_state["fp-mascot"] = visit
    username = st.session_state["username"]
    with st.container(key="fp-topbar"):
        brand_col, *nav_cols, user_col, logout_col = st.columns(
            [1.6, 1, 1, 0.8, 0.85, 0.95, 1.4, 0.8], vertical_alignment="center"
        )
        with brand_col:
            brand(active, visit["previous"])
        for column, (section, page, label) in zip(nav_cols, NAV_ITEMS):
            if column.button(
                label,
                key=f"top-nav-{section}",
                type="primary" if active == section else "secondary",
                width="stretch",
            ):
                go(page)
        user_col.markdown(
            '<div class="fp-avatar-row">'
            f'<span class="fp-account-name">Signed in as <strong>{safe_html(username)}</strong></span>'
            f'<span class="fp-avatar">{safe_html(username[:2].upper())}</span></div>',
            unsafe_allow_html=True,
        )
        if logout_col.button("Log out", key="logout", width="stretch"):
            try:
                api.logout(st.session_state["access_token"])
            except api.BackendError as exc:
                st.session_state["notice"] = f"Signed out locally. {exc}"
            else:
                st.session_state["notice"] = "You are signed out."
            clear_login()
            st.rerun()
