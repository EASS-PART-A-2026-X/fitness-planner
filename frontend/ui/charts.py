"""Weekly consistency chart, styled to match the dark navy theme."""

from datetime import date

import altair as alt
import streamlit as st

import fitness_planner_api as api

EMERALD = "#10B981"
CORAL = "#F97362"
MUTED = "#94A3B8"
GRID = "rgba(255, 255, 255, 0.08)"
TRACK = "rgba(255, 255, 255, 0.06)"


def weekly_chart(history: list[api.WorkoutHistoryWeek], height: int = 260) -> None:
    rows = [
        {
            "week": date.fromisoformat(item["week_start"]).strftime("%b %d"),
            "Completed": item["completed_sessions"],
            "Target": item["weekly_target"],
        }
        for item in history
    ]
    top = max([1, *(max(row["Completed"], row["Target"]) for row in rows)])
    y_scale = alt.Scale(domain=[0, top + 1], nice=False)
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X(
            "week:N",
            sort=None,
            title=None,
            axis=alt.Axis(labelAngle=0, labelPadding=10, ticks=False, domain=False),
        ),
    )
    track = base.mark_bar(color=TRACK, cornerRadius=8, size=26).encode(
        y=alt.Y("Target:Q", scale=y_scale, title="Sessions")
    )
    bars = base.mark_bar(
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="#14B8A6", offset=0),
                alt.GradientStop(color=EMERALD, offset=1),
            ],
            x1=1,
            x2=1,
            y1=1,
            y2=0,
        ),
        cornerRadius=8,
        size=26,
    ).encode(
        y=alt.Y("Completed:Q", scale=y_scale),
        tooltip=["week:N", "Completed:Q", "Target:Q"],
    )
    target = base.mark_line(
        color=CORAL,
        strokeDash=[4, 5],
        strokeWidth=2,
        opacity=0.85,
        interpolate="monotone",
        point=alt.OverlayMarkDef(color="#0B1220", stroke=CORAL, strokeWidth=2, size=36),
    ).encode(y=alt.Y("Target:Q", scale=y_scale))
    chart = (
        (track + bars + target)
        .properties(height=height, background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=MUTED,
            titleColor=MUTED,
            labelFont="Inter",
            titleFont="Inter",
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight=500,
            gridColor=GRID,
            gridDash=[3, 4],
            domain=False,
            ticks=False,
        )
        .configure_axisY(labelPadding=8, tickCount=5)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "Green bars: completed sessions · grey track & dashed coral line: weekly target"
    )


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
