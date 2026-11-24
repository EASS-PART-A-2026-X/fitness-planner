import streamlit as st

import fitness_planner_api as api
from ui.components import brand, card, html_block, icon
from ui.session import save_login

FEATURES = (
    (
        "sparkles",
        "AI coach",
        "Describe your goal and gear; get a plan that fits your time.",
    ),
    ("timer", "Guided sessions", "Log every set, rest with a timer, resume any time."),
    ("chart", "Real progress", "Weekly targets, streaks and a consistency chart."),
)


def render() -> None:
    if notice := st.session_state.pop("notice", None):
        st.info(notice)
    if error := st.session_state.pop("restore_error", None):
        st.error(f"Could not verify your saved login. {error}")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        brand()
        features = "".join(
            f"<li>{icon(name)}<span><strong>{title}</strong>{text}</span></li>"
            for name, title, text in FEATURES
        )
        html_block(
            '<div class="fp-auth-title">Train with a plan.<br>'
            '<span class="fp-accent">Finish with proof.</span></div>'
            f'<ul class="fp-features">{features}</ul>'
        )
        st.caption("Your plans stay private to your account.")

    with right, card():
        st.subheader("Welcome")
        st.caption("Sign in or create a free account.")
        login_tab, register_tab = st.tabs(["Log in", "Create account"])

        with login_tab, st.form("login-form"):
            username = st.text_input("Username", key="login-username")
            password = st.text_input("Password", type="password", key="login-password")
            if st.form_submit_button("Log in", type="primary", width="stretch"):
                _submit(api.login, username, password, "login-password")

        with register_tab, st.form("register-form"):
            username = st.text_input("Username", key="register-username")
            password = st.text_input(
                "Password (at least 8 characters)",
                type="password",
                key="register-password",
            )
            if st.form_submit_button("Create account", type="primary", width="stretch"):
                _submit(api.register, username, password, "register-password")


def _submit(action, username: str, password: str, password_key: str) -> None:
    try:
        session = action(username, password)
    except api.BackendError as exc:
        st.error(str(exc))
    else:
        st.session_state.pop(password_key, None)
        save_login(session)
