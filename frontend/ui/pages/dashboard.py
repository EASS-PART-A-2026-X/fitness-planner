import streamlit as st

import fitness_planner_api as api
from ui import charts
from ui.components import (
    activity_timeline,
    card,
    chip,
    empty_state,
    hero,
    html_block,
    safe_html,
    section,
    segments,
    stat_tiles,
    workout_icon,
)
from ui.state import go


def load_overview(token: str) -> list[api.WorkoutOverview] | None:
    try:
        with st.spinner("Loading your workout plans..."):
            return api.list_workout_overview(token)
    except api.BackendError as exc:
        st.error(str(exc))
        st.info("Check that the backend is available, then reload this page.")
        return None


def workout_card(workout: api.WorkoutOverview, button_label: str) -> None:
    workout_id = workout["id"]
    live = workout["has_unfinished_workout"]
    chips = [
        chip(workout["goal"]),
        chip(f"{workout['frequency_per_week']}× / week"),
    ]
    if live:
        chips.insert(0, chip("Finish your workout!", live=True))
    with card():
        info_col, progress_col, action_col = st.columns(
            [3, 2, 1.1], vertical_alignment="center"
        )
        info_col.markdown(
            '<div class="fp-workout">'
            f"{workout_icon(workout.get('emoji', ''), workout_id)}"
            f'<div><div class="fp-workout-title">{safe_html(workout["title"])}</div>'
            f'<div class="fp-meta">{"".join(chips)}</div></div></div>',
            unsafe_allow_html=True,
        )
        progress_col.markdown(
            segments(workout["completed_this_week"], workout["frequency_per_week"]),
            unsafe_allow_html=True,
        )
        if action_col.button(
            "Resume" if live else button_label,
            key=f"open-workout-{workout_id}",
            type="primary" if live else "secondary",
            width="stretch",
        ):
            go("plan", workout_id=workout_id)


def first_plan_prompt() -> None:
    with card():
        empty_state(
            "Your first workout starts here",
            "Let the AI coach draft a plan from your goal and equipment, "
            "or build one exercise by exercise.",
            "sparkles",
        )
        _, coach_col, create_col, _ = st.columns([1, 1.3, 1.3, 1])
        if coach_col.button(
            "Plan it with AI", key="empty-coach", type="primary", width="stretch"
        ):
            go("coach")
        if create_col.button(
            "Build it yourself", key="empty-create-workout", width="stretch"
        ):
            go("create")


def render(token: str) -> None:
    workouts = load_overview(token)
    if workouts is None:
        return

    done = sum(workout["completed_this_week"] for workout in workouts)
    target = sum(workout["frequency_per_week"] for workout in workouts)
    percent = min(100, round(done / target * 100)) if target else 0
    name = safe_html(st.session_state["username"])
    hero(
        "This week",
        f'Welcome back, <span class="fp-accent">{name}</span>.',
        "Every session counts. Keep your plans moving and your streak alive.",
        percent,
        f"{done} of {target} sessions",
    )

    history: list[api.WorkoutHistoryWeek] = []
    try:
        history = api.workout_progress_history(token)
    except api.BackendError as exc:
        st.warning(f"Could not load your progress summary. {exc}")
    stat_tiles(
        [
            ("Active plans", str(len(workouts)), "in your library"),
            ("This week", f"{done}<small> / {target}</small>", "sessions completed"),
            (
                "12-week total",
                str(sum(item["completed_sessions"] for item in history)),
                "sessions logged",
            ),
            ("Streak", f"{charts.streak(history)}<small> wk</small>", "weeks in a row"),
        ]
    )

    if not workouts:
        first_plan_prompt()
        return

    plans_col, activity_col = st.columns([1.75, 1], gap="large")
    with plans_col:
        heading, more = st.columns([3, 1], vertical_alignment="center")
        with heading:
            section("Your training plans")
        if more.button("All plans →", key="dashboard-view-plans", width="stretch"):
            go("plans")
        for workout in workouts[:3]:
            workout_card(workout, "Open")

    with activity_col:
        section("Recent activity")
        try:
            recent = api.recent_completions(token)
        except api.BackendError as exc:
            st.warning(f"Could not load recent activity. {exc}")
            recent = []
        with card():
            if recent:
                activity_timeline(recent)
            else:
                html_block(
                    '<p class="fp-exercise-note">Finish a workout and it shows up here.</p>'
                )
