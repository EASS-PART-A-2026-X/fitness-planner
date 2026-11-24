"""Weekly consistency chart, styled to match the dark theme."""

from datetime import date

import altair as alt
import streamlit as st

import fitness_planner_api as api

EMERALD = "#10B981"
CORAL = "#F97362"
MUTED = "#64748B"
GRID = "#E2E8F0"


def weekly_chart(history: list[api.WorkoutHistoryWeek], height: int = 260) -> None:
    rows = [
        {
            "week": date.fromisoformat(item["week_start"]).strftime("%b %d"),
            "Completed": item["completed_sessions"],
            "Target": item["weekly_target"],
        }
        for item in history
    ]
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X("week:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
    )
    bars = base.mark_bar(
        color=EMERALD, cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=22
    ).encode(
        y=alt.Y("Completed:Q", title="Sessions"),
        tooltip=["week:N", "Completed:Q", "Target:Q"],
    )
    target = base.mark_line(
        color=CORAL,
        strokeDash=[6, 4],
        strokeWidth=2,
        point=alt.OverlayMarkDef(color=CORAL, size=40),
    ).encode(y="Target:Q")
    chart = (
        (bars + target)
        .properties(height=height, background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=MUTED,
            titleColor=MUTED,
            gridColor=GRID,
            domainColor=GRID,
            tickColor=GRID,
        )
    )
    st.altair_chart(chart, width="stretch")
    st.caption("Green bars: completed sessions · dashed coral line: weekly target")


def streak(history: list[api.WorkoutHistoryWeek]) -> int:
    """Consecutive weeks with at least one session, counting back from this week."""
    count = 0
    for item in reversed(history):
        if item["completed_sessions"] == 0:
            # The current week may still be in progress; don't break the streak on it.
            if count == 0 and item is history[-1]:
                continue
            break
        count += 1
    return count
