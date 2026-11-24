"""Login state, kept in session_state and in a browser cookie."""

import streamlit as st
from streamlit_cookies_controller import CookieController

import fitness_planner_api as api

SESSION_COOKIE = "fitness_planner_session"
SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60
_cookies: CookieController | None = None


def init_cookies() -> None:
    """The controller is a component: it must be created on every script run."""
    global _cookies
    _cookies = CookieController(key="fitness-planner-cookies")


def _all_cookies() -> dict | None:
    values = _cookies.getAll() if _cookies is not None else None
    return values if isinstance(values, dict) else None


def clear_login() -> None:
    cookie_values = _all_cookies()
    if cookie_values is not None and SESSION_COOKIE in cookie_values:
        _cookies.remove(SESSION_COOKIE)
    for key in list(st.session_state):
        if key in {
            "access_token",
            "username",
            "user_id",
            "fp-analytics-page",
            "page",
            "active_section",
            "selected_workout_id",
            "delete_confirmation",
            "login-password",
            "register-password",
            "pending-cookie",
            "coach-result",
        } or key.startswith(("create-", "edit-", "session-", "coach-")):
            st.session_state.pop(key, None)
    st.query_params.clear()


def save_login(session: api.AuthSession) -> None:
    st.session_state["access_token"] = session["access_token"]
    st.session_state["username"] = session["user"]["username"]
    st.session_state["user_id"] = session["user"].get("id")
    st.session_state["page"] = "home"
    st.session_state["active_section"] = "dashboard"
    st.session_state["pending-cookie"] = {
        "token": session["access_token"],
        "expires_in": session["expires_in"],
    }


def persist_login_cookie() -> None:
    pending = st.session_state.pop("pending-cookie", None)
    if not pending:
        return
    if _all_cookies() is not None:
        _cookies.set(
            SESSION_COOKIE,
            pending["token"],
            max_age=min(pending["expires_in"], SESSION_LIFETIME_SECONDS),
            secure=(st.context.url or "").startswith("https://"),
            same_site="lax",
        )
    else:
        st.session_state["notice"] = (
            "You are signed in, but this browser could not save your login. "
            "You may need to sign in again after closing the tab."
        )


def restore_login() -> bool:
    if "access_token" in st.session_state:
        return False
    cookie_values = _all_cookies() or {}
    token = cookie_values.get(SESSION_COOKIE)
    if not isinstance(token, str) or not token:
        return False
    try:
        user = api.current_user(token)
    except api.SessionExpired:
        _cookies.remove(SESSION_COOKIE)
        st.session_state["notice"] = "Your saved login expired. Please sign in again."
    except api.BackendError as exc:
        st.session_state["restore_error"] = str(exc)
    else:
        st.session_state["access_token"] = token
        st.session_state["username"] = user["username"]
        st.session_state["user_id"] = user.get("id")
        st.session_state["page"] = "home"
        st.session_state["active_section"] = "dashboard"
        return True
    return False
