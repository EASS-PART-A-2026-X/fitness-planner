"""Plans list, activity log and analytics: the read-mostly pages."""

import streamlit as st

import fitness_planner_api as api
from ui import charts
from ui.components import activity_timeline, card, empty_state, page_header, stat_tiles
from ui.pages.dashboard import first_plan_prompt, load_overview, workout_card
from ui.state import go


def render_plans(token: str) -> None:
    workouts = load_overview(token)
    if workouts is None:
        return
    title_col, create_col = st.columns([4, 1], vertical_alignment="bottom")
    with title_col:
        page_header(
            "Your routines",
            "Training plans",
            "Open a plan to review it, start a session, or let the AI refresh it.",
        )
    if create_col.button(
        "＋ Create plan", key="create-workout", type="primary", width="stretch"
    ):
        go("create")
    if not workouts:
        first_plan_prompt()
        return
    for workout in workouts:
        workout_card(workout, "View", token=token)


def render_activities(token: str) -> None:
    page_header(
        "Activity log",
        "Recent activity",
        "Your latest completed sessions and the reps you actually did.",
    )
    try:
        activities = api.recent_completions(token)
    except api.BackendError as exc:
        st.error(f"Could not load recent workout activity. {exc}")
        return
    with card():
        if activities:
            activity_timeline(activities)
            st.caption("Showing your three most recent workouts.")
        else:
            empty_state(
                "No sessions yet",
                "Completed workouts will show up here after your first session.",
                "timer",
            )


def render_analytics(token: str) -> None:
    page_header(
        "Consistency builds results",
        "Training analytics",
        "Completed sessions compared with the weekly targets of your plans.",
    )
    try:
        history = api.workout_progress_history(token)
    except api.BackendError as exc:
        st.error(f"Could not load your progress graph. {exc}")
        return
    if not history:
        with card():
            empty_state(
                "Nothing to chart yet",
                "Create a plan and complete a workout to see your training graph.",
                "chart",
            )
        return

    completed = sum(item["completed_sessions"] for item in history)
    planned = sum(item["weekly_target"] for item in history)
    best = max(history, key=lambda item: item["completed_sessions"])
    stat_tiles(
        [
            ("Completed", str(completed), f"sessions in {len(history)} weeks", "check"),
            ("Planned", str(planned), "target sessions", "calendar"),
            (
                "Completion",
                f"{round(completed / planned * 100) if planned else 0}%",
                "of planned sessions",
                "target",
            ),
            (
                "Streak",
                f"{charts.streak(history)}<small> wk</small>",
                "weeks in a row",
                "flame",
            ),
            (
                "Best week",
                str(best["completed_sessions"]),
                f"week of {best['week_start']}",
                "trophy",
            ),
        ]
    )
    with card():
        st.subheader("Training progress")
        charts.weekly_chart(history)
