"""Fitness Planner frontend: auth gate, top bar, then one page per view.

All HTTP lives in fitness_planner_api.py; pages live in ui/pages/.
"""

from pathlib import Path

import streamlit as st

import fitness_planner_api as api
from ui import analytics, dialogs, session
from ui.components import reset_cards
from ui.mascot import celebration_html
from ui.pages import auth, dashboard, editor, header, library, plan, workout
from ui.state import restore_page_from_url
from ui.theme import inject_theme

st.set_page_config(
    page_title="Fitness Planner",
    page_icon=str(Path(__file__).parent / "assets" / "rep-icon.svg"),  # Rep's face
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()
reset_cards()
session.init_cookies()

restored = session.restore_login()
if "access_token" in st.session_state and not restored:
    try:
        user = api.current_user(st.session_state["access_token"])
        st.session_state["user_id"] = user.get("id")
    except api.SessionExpired:
        session.clear_login()
        st.session_state["notice"] = "Your session expired. Please sign in again."
    except api.BackendError as exc:
        st.error(f"Could not verify your login. {exc}")
        st.stop()

if "access_token" not in st.session_state:
    auth_screen = st.empty()
    with auth_screen.container():
        auth.render()
    if "access_token" not in st.session_state:
        st.stop()
    auth_screen.empty()

session.persist_login_cookie()
restore_page_from_url()
header.render()

token = st.session_state["access_token"]
if notice := st.session_state.pop("notice", None):
    st.success(notice)
celebrate = st.session_state.pop("celebrate", None)

page = st.session_state["page"]
workout_id = st.session_state.get("selected_workout_id")
analytics.track_page(page)
if page == "create":
    editor.render_create(token)
elif page == "plan" and workout_id:
    plan.render(token, workout_id)
elif page == "detail" and workout_id:
    workout.render(token, workout_id)
elif page == "edit" and workout_id:
    editor.render_edit(token, workout_id)
elif page == "activities":
    library.render_activities(token)
elif page == "plans":
    library.render_plans(token)
elif page == "analytics":
    library.render_analytics(token)
else:
    dashboard.render(token)
dialogs.render_pending(token)
if celebrate:
    # Drawn last, so the animation starts once the page underneath has loaded.
    st.markdown(celebration_html(str(celebrate)), unsafe_allow_html=True)
