"""Small HTML building blocks. Every user-provided string goes through safe_html()."""

import html
import string
from datetime import date

import streamlit as st

import fitness_planner_api as api
from ui.catalog import WORKOUT_TYPES
from ui.exercises import exercise_name, exercise_spec
from ui.mascot import mascot_html

MARKDOWN_ESCAPES = str.maketrans({c: "\\" + c for c in string.punctuation})
WORKOUT_ICONS = {
    "weights": '<path d="M6 5v14M18 5v14M3 8v8M21 8v8M6 12h12"/>',
    "running": '<circle cx="15" cy="5" r="2"/><path d="m12 22 3-7-4-3 2-5 4 3 4 1M9 10l-4 3-2 4M14 15l-5 2-2 5"/>',
    "cycling": '<circle cx="6" cy="17" r="3"/><circle cx="18" cy="17" r="3"/><path d="m6 17 4-7 4 7H6l3-5h6l3 5M13 7h3"/>',
    "yoga": '<circle cx="12" cy="5" r="2"/><path d="M12 8v5m0-3-6 3m6-3 6 3M12 13l-5 6m5-6 5 6"/>',
    "swimming": '<circle cx="16" cy="7" r="2"/><path d="m14 10-4 4 5 2 3-3 3 1M3 19c2-2 4 2 6 0s4 2 6 0 4 2 6 0"/>',
    "boxing": '<path d="M7 12V8a2 2 0 0 1 4 0v2-3a2 2 0 0 1 4 0v3-2a2 2 0 0 1 4 0v5l-3 6h-8l-3-4v-3a2 2 0 0 1 2-2Z"/><path d="M8 14h4"/>',
}
UI_ICONS = {
    "sparkles": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "timer": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "flame": '<path d="M12 22c4 0 7-2.7 7-6.8 0-3.9-2.7-6.4-4.4-8.6-.5 2.3-1.7 3.6-3 4.2C11.8 7.4 10.4 4.3 8 2c.3 3.6-3 6.5-3 11.2C5 19.3 8 22 12 22Z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "trophy": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0Z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 13 9 5 9-5"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
}
STAT_TONES = {
    "flame": "amber",
    "trophy": "amber",
    "target": "coral",
    "calendar": "blue",
    "chart": "blue",
    "layers": "violet",
}
CARDIO_ICONS = {"running", "cycling", "swimming", "timer", "hiit"}
STRENGTH_ICONS = {"weights", "boxing", "chart", "upper", "lower", "fullbody", "core"}
MIND_ICONS = {"yoga", "pilates", "stretch"}
# Workout types from the Create flow use the bigger line-art people.
ART_ICONS = {item.id: item.art for item in WORKOUT_TYPES}


def plain(text: str) -> str:
    """Escape Markdown so user text is shown literally."""
    return str(text).translate(MARKDOWN_ESCAPES)


def safe_html(text: object) -> str:
    return html.escape(str(text), quote=True)


_card_count = 0


def reset_cards() -> None:
    """Called once per script run so card keys are stable between reruns."""
    global _card_count
    _card_count = 0


def card():
    """A bordered container with an `fp-card-N` key, so CSS can style it as a card."""
    global _card_count
    _card_count += 1
    return st.container(border=True, key=f"fp-card-{_card_count}")


def html_block(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def icon_id_for_workout(value: str, workout_id: int | None = None) -> str:
    if value in WORKOUT_ICONS or value in ART_ICONS:
        return value
    return tuple(WORKOUT_ICONS)[(workout_id or 0) % len(WORKOUT_ICONS)]


def tone_class(name: str) -> str:
    if name in CARDIO_ICONS:
        return " is-cardio"
    if name in STRENGTH_ICONS:
        return " is-strength"
    if name in MIND_ICONS:
        return " is-mind"
    return ""


def art_svg(paths: str, stroke: float = 2.6) -> str:
    return (
        '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f"{paths}</svg>"
    )


def icon(name: str) -> str:
    if name in ART_ICONS:
        svg = art_svg(ART_ICONS[name], 4)
    else:
        paths = WORKOUT_ICONS.get(name) or UI_ICONS[name]
        svg = (
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            f"{paths}</svg>"
        )
    return f'<span class="fp-icon{tone_class(name)}" aria-hidden="true">{svg}</span>'


def workout_icon(value: str, workout_id: int | None = None) -> str:
    return icon(icon_id_for_workout(value, workout_id))


def brand(section: str = "dashboard", previous: str | None = None) -> None:
    html_block(
        f'<div class="fp-brand">{mascot_html(section, previous)}'
        '<span class="fp-brand-name">Fitness Planner</span></div>'
    )


def back_link(label: str, key: str) -> bool:
    """A small, quiet 'back' button that does not push the page down."""
    with st.container(key=f"fp-back-{key}"):
        return st.button(label, key=key)


def page_header(eyebrow: str, title: str, subtitle: str = "") -> None:
    html_block(
        f'<div class="fp-eyebrow">{safe_html(eyebrow)}</div>'
        f'<div class="fp-page-title">{safe_html(title)}</div>'
        + (f'<p class="fp-page-subtitle">{safe_html(subtitle)}</p>' if subtitle else "")
    )


def ring(percent: int, number: str, caption: str) -> str:
    radius = 52
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - max(0, min(percent, 100)) / 100)
    return (
        f'<div class="fp-ring" role="progressbar" aria-valuenow="{percent}" '
        'aria-valuemin="0" aria-valuemax="100">'
        '<svg viewBox="0 0 120 120" aria-hidden="true">'
        '<defs><linearGradient id="fp-ring-grad" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#34D399"/><stop offset="1" stop-color="#14B8A6"/>'
        "</linearGradient></defs>"
        f'<circle class="fp-ring-track" cx="60" cy="60" r="{radius}" fill="none" stroke-width="10"/>'
        f'<circle class="fp-ring-value" cx="60" cy="60" r="{radius}" fill="none" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{circumference:.1f}" '
        f'stroke-dashoffset="{offset:.1f}"/></svg>'
        f'<div class="fp-ring-label"><div class="fp-ring-number">{safe_html(number)}</div>'
        f'<div class="fp-ring-caption">{safe_html(caption)}</div></div></div>'
    )


def hero(
    eyebrow: str, title: str, subtitle: str, percent: int, ring_caption: str
) -> None:
    html_block(
        '<section class="fp-hero"><div>'
        f'<div class="fp-eyebrow">{safe_html(eyebrow)}</div>'
        f'<div class="fp-page-title">{title}</div>'
        f'<p class="fp-page-subtitle">{safe_html(subtitle)}</p></div>'
        f"{ring(percent, f'{percent}%', ring_caption)}</section>"
    )


def stat_icon(name: str) -> str:
    tone = STAT_TONES.get(name)
    return (
        f'<span class="fp-stat-icon{f" tone-{tone}" if tone else ""}" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
        f'stroke-linecap="round" stroke-linejoin="round">{UI_ICONS[name]}</svg></span>'
    )


def stat_tiles(tiles: list[tuple[str, ...]]) -> None:
    """tiles: (label, value_html, sub[, icon]). value_html may hold a trusted <small>."""
    cells = []
    for label, value, sub, *rest in tiles:
        badge = stat_icon(rest[0]) if rest else ""
        cells.append(
            f'<div class="fp-stat">{badge}<div class="fp-stat-label">{safe_html(label)}</div>'
            f'<div class="fp-stat-value">{value}</div>'
            f'<div class="fp-stat-sub">{safe_html(sub)}</div></div>'
        )
    html_block(f'<div class="fp-stats">{"".join(cells)}</div>')


def section(title: str) -> None:
    html_block(f'<div class="fp-section">{safe_html(title)}</div>')


def chip(text: str, live: bool = False) -> str:
    return f'<span class="fp-chip{" is-live" if live else ""}">{safe_html(text)}</span>'


def segments(done: int, total: int) -> str:
    total = max(total, 1)
    cells = "".join(
        f'<span class="fp-segment{" is-done" if index < done else ""}"></span>'
        for index in range(total)
    )
    percent = min(100, round(done / total * 100))
    return (
        f'<div class="fp-segments" role="progressbar" aria-valuenow="{percent}" '
        f'aria-valuemin="0" aria-valuemax="100">{cells}</div>'
        f'<div class="fp-progress-label"><span>{done} of {total} sessions this week</span>'
        f"<span>{percent}%</span></div>"
    )


def bar(percent: int) -> str:
    return (
        f'<div class="fp-bar" role="progressbar" aria-valuenow="{percent}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<div class="fp-bar-fill" style="width:{percent}%"></div></div>'
    )


def exercise_list(exercises: list[api.Exercise]) -> None:
    rows = []
    for index, exercise in enumerate(exercises, start=1):
        spec, sub = exercise_spec(exercise)
        note = exercise.get("notes", "")
        rows.append(
            '<div class="fp-exercise">'
            f'<span class="fp-index">{index:02d}</span>'
            f'<div><div class="fp-exercise-name">{safe_html(exercise_name(exercise))}</div>'
            + (f'<div class="fp-exercise-note">{safe_html(note)}</div>' if note else "")
            + f'</div><div class="fp-exercise-spec">{safe_html(spec)}'
            f"<small>{safe_html(sub)}</small></div></div>"
        )
    html_block("".join(rows))


def coach_note(text: str) -> None:
    if text:
        html_block(
            f'<div class="fp-coach"><b>Coach</b><span>{safe_html(text)}</span></div>'
        )


def empty_state(title: str, text: str, icon_name: str = "plus") -> None:
    html_block(
        f'<div class="fp-empty">{icon(icon_name)}'
        f'<div class="fp-empty-title">{safe_html(title)}</div>'
        f"<p>{safe_html(text)}</p></div>"
    )


def activity_timeline(activities: list[api.RecentWorkout]) -> None:
    events = []
    for activity in activities:
        chips = []
        for exercise in activity["checked_exercises"][:4]:
            reps = exercise.get("reps", exercise.get("count"))
            label = exercise_name(exercise) + (f" · {reps}" if reps is not None else "")
            chips.append(chip(label))
        extra = len(activity["checked_exercises"]) - 4
        if extra > 0:
            chips.append(chip(f"+{extra} more"))
        day = date.fromisoformat(activity["completed_on"]).strftime("%a, %b %d")
        events.append(
            '<div class="fp-event"><div class="fp-event-head">'
            f'<span class="fp-event-title">{safe_html(activity["workout_name"])}</span>'
            f'<span class="fp-event-date">{safe_html(day)}</span></div>'
            f'<div class="fp-meta">{"".join(chips) or chip("Workout completed")}</div></div>'
        )
    html_block(f'<div class="fp-timeline">{"".join(events)}</div>')
