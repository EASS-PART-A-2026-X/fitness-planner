"""Create (pick a workout, then plan it) and edit pages share one plan form."""

import streamlit as st

import fitness_planner_api as api
from ui import analytics
from ui.catalog import (
    BACKUP_NOTICE,
    CUSTOM_ART,
    DEFAULT_MINUTES,
    EQUIPMENT_LABELS,
    MINUTE_CHOICES,
    TYPES_BY_ID,
    WORKOUT_TYPES,
    WorkoutType,
)
from ui.components import (
    art_svg,
    back_link,
    card,
    coach_note,
    html_block,
    icon_id_for_workout,
    page_header,
    plain,
    safe_html,
)
from ui.dialogs import ask_delete
from ui.forms import (
    exercise_editor,
    load_exercises,
    pick,
    plan_details,
    reset_editor,
    show_errors,
    validate_workout,
)
from ui.state import go, notify, set_page_state

DETAIL_FIELDS = ("title", "goal", "frequency", "experience")
GRID_COLUMNS = 4


def clear_form(prefix: str) -> None:
    reset_editor(prefix)
    for field in (*DETAIL_FIELDS, "coach-notes", "plan-source"):
        st.session_state.pop(f"{prefix}-{field}", None)
        st.session_state.pop(f"{prefix}-{field}--last", None)


def guess_type(name: str) -> str:
    """Pick a picture for a custom workout from words in its name."""
    words = name.lower()
    for item in WORKOUT_TYPES:
        if item.id in words or item.label.lower().split()[0] in words:
            return item.id
    return "fullbody"


# --- Step 1: choose a workout ------------------------------------------------


def _choose(prefix: str, type_id: str) -> None:
    st.session_state["create-type"] = type_id
    st.session_state.pop(f"{prefix}-title", None)
    analytics.capture("workout_type_selected", workout_type=type_id)


def type_grid(prefix: str) -> None:
    page_header(
        "New plan · step 1 of 2",
        "What are you training?",
        "Pick a workout to start from, or give your own one a name.",
    )
    for start in range(0, len(WORKOUT_TYPES), GRID_COLUMNS):
        columns = st.columns(GRID_COLUMNS)
        for column, item in zip(columns, WORKOUT_TYPES[start : start + GRID_COLUMNS]):
            with column, st.container(key=f"fp-type-{item.id}"):
                html_block(
                    f'<div class="fp-type tone-{item.tone}">'
                    f'<div class="fp-type-art">{art_svg(item.art)}</div>'
                    f'<div class="fp-type-label">{safe_html(item.label)}</div>'
                    f'<div class="fp-type-tagline">{safe_html(item.tagline)}</div></div>'
                )
                st.button(
                    f"Choose {item.label}",
                    key=f"type-{item.id}",
                    on_click=_choose,
                    args=(prefix, item.id),
                    width="stretch",
                )

    with card():
        art_col, form_col = st.columns([0.9, 5], vertical_alignment="center")
        art_col.markdown(
            f'<div class="fp-type-art is-custom">{art_svg(CUSTOM_ART)}</div>',
            unsafe_allow_html=True,
        )
        with form_col:
            st.markdown("#### Your own workout")
            name_col, go_col = st.columns([3, 1], vertical_alignment="bottom")
            name = name_col.text_input(
                "Name your workout",
                max_chars=200,
                placeholder="e.g. Climbing, Dance cardio, Tennis drills",
                key="create-custom-name",
            )
            if go_col.button(
                "Continue →", key="type-custom", type="primary", width="stretch"
            ):
                if not name.strip():
                    st.warning("Give your workout a name first.")
                else:
                    _choose(prefix, "custom")
                    st.rerun()


# --- Step 2: plan details, AI fill and exercises -----------------------------


def ai_fill(token: str, prefix: str, details: dict) -> None:
    with card():
        st.markdown("#### ✦ Let the AI coach fill in the exercises")
        st.caption(
            "Uses your name, goal, sessions and level from above. You can still "
            "edit, remove or add exercises afterwards."
        )
        minutes = pick(
            st,
            "Minutes per workout",
            MINUTE_CHOICES,
            f"{prefix}-minutes",
            DEFAULT_MINUTES,
            default=DEFAULT_MINUTES,
            format_func=lambda n: f"{n} min",
        )
        equipment_col, notes_col = st.columns(2)
        equipment = equipment_col.multiselect(
            "Equipment (bodyweight if empty)",
            api.EQUIPMENT,
            format_func=EQUIPMENT_LABELS.get,
            key=f"{prefix}-equipment",
        )
        notes = notes_col.text_input(
            "Anything the coach should know? (optional)",
            max_chars=200,
            placeholder="e.g. sore left knee, short on time",
            key=f"{prefix}-notes",
        )
        clicked = st.button(
            "✦ Generate exercises", key=f"{prefix}-ai", type="primary", width="stretch"
        )
    if not clicked:
        return
    goal = details["goal"].strip()
    if not goal or not details["experience_level"] or not details["frequency_per_week"]:
        st.warning(
            "Fill in the goal, sessions per week and level so the coach can plan."
        )
        return
    request: api.PlanRequest = {
        "goal": goal,
        "experience_level": details["experience_level"][:30],
        "frequency_per_week": details["frequency_per_week"],
        "minutes_per_session": minutes,
    }
    if title := details["title"].strip():
        request["plan_name"] = title[:60]
    if equipment:
        request["equipment"] = equipment
    if notes.strip():
        request["notes"] = notes.strip()
    workout_type = st.session_state.get("create-type")
    try:
        with st.spinner("Your coach is drafting exercises..."):
            draft = api.draft_plan(token, request)
    except api.BackendError as exc:
        st.error(str(exc))
        analytics.capture(
            "ai_draft_failed", workout_type=workout_type, error=type(exc).__name__
        )
        return
    analytics.capture(
        "ai_exercises_drafted",
        workout_type=workout_type,
        plan_source=draft.get("plan_source", "ai"),
        exercise_count=len(draft["exercises"]),
        minutes_per_session=minutes,
        equipment_count=len(equipment),
    )
    load_exercises(prefix, draft["exercises"])
    st.session_state[f"{prefix}-coach-notes"] = draft.get("coach_notes", "")
    st.session_state[f"{prefix}-plan-source"] = draft.get("plan_source", "ai")
    st.rerun()


def chosen_heading(kind: WorkoutType | None, name: str) -> None:
    art = kind.art if kind else CUSTOM_ART
    tone = kind.tone if kind else "custom"
    html_block(
        f'<div class="fp-chosen"><div class="fp-type-art tone-{tone}">{art_svg(art)}</div>'
        '<div><div class="fp-eyebrow">New plan · step 2 of 2</div>'
        f'<div class="fp-page-title" style="margin:.35rem 0 .2rem">Plan your '
        f'<span class="fp-accent">{safe_html(name)}</span></div>'
        '<p class="fp-page-subtitle" style="margin:0">Set the details, let the AI '
        "coach suggest exercises, and make them yours.</p></div></div>"
    )


def render_create(token: str) -> None:
    version = st.session_state.setdefault("create-version", 0)
    prefix = f"create-{version}"
    type_id = st.session_state.get("create-type")
    if type_id not in TYPES_BY_ID and type_id != "custom":
        type_grid(prefix)
        return

    custom_name = st.session_state.get("create-custom-name", "").strip()
    kind = TYPES_BY_ID.get(type_id)
    name = kind.label if kind else custom_name or "workout"
    if back_link("← Choose another workout", "create-change"):
        st.session_state.pop("create-type", None)
        st.rerun()
    chosen_heading(kind, name)

    details = plan_details(
        prefix,
        title_default=name,
        goal_hint=kind.goal_hint if kind else "e.g. Get better at it",
    )
    ai_fill(token, prefix, details)
    if st.session_state.get(f"{prefix}-plan-source") == "offline":
        st.info(BACKUP_NOTICE, icon="💡")
    coach_note(st.session_state.get(f"{prefix}-coach-notes", ""))
    exercises = exercise_editor(prefix, starters=kind.starters if kind else ())

    if st.button(
        "Create plan ✓", key=f"{prefix}-submit", type="primary", width="stretch"
    ):
        workout = details | {
            "emoji": kind.id if kind else guess_type(custom_name),
            "exercises": exercises,
        }
        if errors := validate_workout(workout):
            show_errors(errors)
            return
        try:
            created = api.create_workout(token, workout)
        except api.BackendError as exc:
            st.error(str(exc))
            return
        analytics.capture(
            "plan_created",
            workout_type=workout["emoji"],
            custom_name=kind is None,
            used_ai=f"{prefix}-plan-source" in st.session_state,
            exercise_count=len(exercises),
            sessions_per_week=workout["frequency_per_week"],
            experience_level=workout["experience_level"],
        )
        clear_form(prefix)
        for key in ("create-type", "create-custom-name"):
            st.session_state.pop(key, None)
        st.session_state["create-version"] += 1
        set_page_state("plans")
        notify(f"Created {plain(created['title'])}.")


# --- Edit ------------------------------------------------------------------------


def render_edit(token: str, workout_id: int) -> None:
    prefix = f"edit-{workout_id}"
    if back_link("← Back to plan", "edit-back"):
        clear_form(prefix)
        go("plan", workout_id=workout_id)
    try:
        workout = api.read_workout(token, workout_id)
    except api.BackendError as exc:
        st.error(str(exc))
        return

    page_header("Make it yours", "Edit plan", "Adjust your plan as you progress.")
    kind = TYPES_BY_ID.get(icon_id_for_workout(workout.get("emoji", ""), workout_id))
    details = plan_details(prefix, workout)
    exercises = exercise_editor(
        prefix, workout["exercises"], starters=kind.starters if kind else ()
    )
    changes = details | {"exercises": exercises}

    save_col, delete_col = st.columns([3, 1])
    if save_col.button(
        "Save changes", key=f"{prefix}-save", type="primary", width="stretch"
    ):
        if errors := validate_workout(changes):
            show_errors(errors)
        else:
            try:
                api.update_workout(token, workout_id, changes)
            except api.BackendError as exc:
                st.error(str(exc))
            else:
                analytics.capture(
                    "plan_updated",
                    workout_type=workout.get("emoji", ""),
                    exercise_count=len(exercises),
                )
                clear_form(prefix)
                st.session_state.pop(f"session-{workout_id}-exercise-index", None)
                set_page_state("plan", workout_id=workout_id)
                notify(f"Saved {plain(changes['title'])}.")
    delete_col.button(
        ":material/delete: Delete",
        key=f"{prefix}-delete",
        on_click=ask_delete,
        args=(workout, prefix),
        width="stretch",
    )
