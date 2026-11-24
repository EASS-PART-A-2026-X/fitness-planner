"""Plan form shared by the create and edit pages, plus client-side validation.

The exercise editor keeps a list of stable row ids in session state, so any row
can be removed, and rows can be filled from AI drafts or quick-add starters by
writing their widget keys before the widgets are drawn.
"""

import streamlit as st

import fitness_planner_api as api
from ui.catalog import LEVELS
from ui.components import card, html_block
from ui.exercises import structured_exercise

MAX_EXERCISES = 100
REST_CHOICES = (0, 30, 45, 60, 90, 120, 180)
ROW_FIELDS = ("name", "sets", "reps", "vary", "replist", "rest", "notes")


# --- Row state ---------------------------------------------------------------


def _rows_key(prefix: str) -> str:
    return f"{prefix}-rows"


def _seed_row(prefix: str, row: int, exercise: api.Exercise | None) -> None:
    """Write a row's widget values into session state (before it is drawn)."""
    item = structured_exercise(exercise) if exercise else {}
    sets = int(item.get("sets", 3))
    reps = [value.strip() for value in str(item.get("reps", "10")).split(",")]
    numeric = [int(value) for value in reps if value.isdigit()]
    same = len(set(reps)) == 1 and len(numeric) == len(reps)
    state = st.session_state
    state[f"{prefix}-name-{row}"] = item.get("name", "")
    state[f"{prefix}-sets-{row}"] = max(1, min(sets, 100))
    state[f"{prefix}-reps-{row}"] = numeric[0] if same and numeric else 10
    state[f"{prefix}-vary-{row}"] = not same
    state[f"{prefix}-replist-{row}"] = ", ".join(reps)
    state[f"{prefix}-rest-{row}"] = int(item.get("rest_seconds", 60))
    state[f"{prefix}-notes-{row}"] = item.get("notes", "")


def _forget_row(prefix: str, row: int) -> None:
    for field in ROW_FIELDS:
        st.session_state.pop(f"{prefix}-{field}-{row}", None)


def load_exercises(prefix: str, exercises: list[api.Exercise]) -> None:
    """Replace every row with these exercises (used by the AI fill)."""
    for row in st.session_state.get(_rows_key(prefix), []):
        _forget_row(prefix, row)
    rows = list(range(len(exercises))) or [0]
    st.session_state[_rows_key(prefix)] = rows
    st.session_state[f"{prefix}-next-row"] = len(rows)
    for row, exercise in zip(rows, exercises or [None]):
        _seed_row(prefix, row, exercise)


def reset_editor(prefix: str) -> None:
    for row in st.session_state.pop(_rows_key(prefix), []):
        _forget_row(prefix, row)
    st.session_state.pop(f"{prefix}-next-row", None)


def add_row(prefix: str, exercise: api.Exercise | None = None) -> None:
    rows = st.session_state[_rows_key(prefix)]
    if len(rows) >= MAX_EXERCISES:
        return
    row = st.session_state.get(f"{prefix}-next-row", len(rows))
    st.session_state[f"{prefix}-next-row"] = row + 1
    _seed_row(prefix, row, exercise)
    # A lone blank row is replaced by the first quick-add instead of kept.
    if exercise and len(rows) == 1 and not st.session_state[f"{prefix}-name-{rows[0]}"]:
        _forget_row(prefix, rows[0])
        rows.clear()
    rows.append(row)


def _sync_reps(prefix: str, row: int) -> None:
    """Carry the reps over when switching between 'same' and 'per set'."""
    state = st.session_state
    sets = int(state.get(f"{prefix}-sets-{row}", 1))
    if state.get(f"{prefix}-vary-{row}"):
        same = int(state.get(f"{prefix}-reps-{row}", 10))
        state[f"{prefix}-replist-{row}"] = ", ".join([str(same)] * sets)
    else:
        first = str(state.get(f"{prefix}-replist-{row}", "10")).split(",")[0].strip()
        state[f"{prefix}-reps-{row}"] = int(first) if first.isdigit() else 10


def remove_row(prefix: str, row: int) -> None:
    rows = st.session_state[_rows_key(prefix)]
    if len(rows) > 1 and row in rows:
        rows.remove(row)
        _forget_row(prefix, row)


# --- Plan details --------------------------------------------------------------


def plan_details(
    prefix: str,
    initial: api.WorkoutPlan | None = None,
    *,
    title_default: str = "",
    goal_hint: str = "e.g. Build strength",
) -> dict:
    """Name, goal, sessions per week and level. Keys are stable per plan."""
    initial = initial or {}
    state = st.session_state
    state.setdefault(f"{prefix}-title", initial.get("title", title_default))
    state.setdefault(f"{prefix}-goal", initial.get("goal", ""))
    state.setdefault(f"{prefix}-frequency", initial.get("frequency_per_week", 3))
    level = initial.get("experience_level", "beginner")
    levels = LEVELS if level in LEVELS else (*LEVELS, level)
    state.setdefault(f"{prefix}-experience", level)

    with card():
        st.markdown("#### Plan details")
        title_col, goal_col = st.columns(2)
        title = title_col.text_input(
            "Workout name",
            max_chars=200,
            placeholder="e.g. Morning run",
            key=f"{prefix}-title",
        )
        goal = goal_col.text_input(
            "Goal", max_chars=100, placeholder=goal_hint, key=f"{prefix}-goal"
        )
        frequency_col, level_col = st.columns(2)
        frequency = frequency_col.segmented_control(
            "Sessions per week",
            options=range(1, 8),
            format_func=lambda n: f"{n}×",
            required=True,
            key=f"{prefix}-frequency",
        )
        experience = level_col.segmented_control(
            "Experience level",
            options=levels,
            format_func=str.capitalize,
            required=True,
            key=f"{prefix}-experience",
        )
    return {
        "title": title,
        "goal": goal,
        "frequency_per_week": frequency or 0,
        "experience_level": experience or "",
    }


# --- Exercise editor -------------------------------------------------------------


def _rest_label(seconds: int) -> str:
    """Short pill labels: None, 30s, 1m, 1m30, 2m…"""
    if seconds == 0:
        return "None"
    minutes, rest = divmod(seconds, 60)
    if minutes and rest:
        return f"{minutes}m{rest:02d}"
    return f"{minutes}m" if minutes else f"{seconds}s"


def _exercise_row(
    prefix: str, position: int, row: int, removable: bool
) -> api.Exercise:
    with st.container(key=f"fp-row-{prefix}-{row}"):
        badge_col, name_col, trash_col = st.columns(
            [0.45, 6, 0.55], vertical_alignment="center"
        )
        badge_col.markdown(
            f'<span class="fp-index">{position:02d}</span>', unsafe_allow_html=True
        )
        name = name_col.text_input(
            "Exercise name",
            max_chars=200,
            placeholder="Exercise name, e.g. Push-ups",
            label_visibility="collapsed",
            key=f"{prefix}-name-{row}",
        )
        with trash_col, st.container(key=f"fp-trash-row-{prefix}-{row}"):
            st.button(
                ":material/close:",
                key=f"{prefix}-remove-{row}",
                help="Remove exercise",
                on_click=remove_row,
                args=(prefix, row),
                disabled=not removable,
                width="stretch",
            )

        sets_col, reps_col, rest_col = st.columns([1, 1.2, 3.2])
        sets = sets_col.number_input(
            "Sets", min_value=1, max_value=100, step=1, key=f"{prefix}-sets-{row}"
        )
        vary = st.session_state.get(f"{prefix}-vary-{row}", False)
        if vary:
            reps = reps_col.text_input(
                "Reps per set",
                max_chars=1000,
                placeholder="10, 10, 8",
                help="One number per set, separated by commas.",
                key=f"{prefix}-replist-{row}",
            )
        else:
            same = reps_col.number_input(
                "Reps",
                min_value=1,
                max_value=10000,
                step=1,
                help="The same target for every set.",
                key=f"{prefix}-reps-{row}",
            )
            reps = ", ".join([str(int(same))] * int(sets))
        rest_key = f"{prefix}-rest-{row}"
        choices = sorted({*REST_CHOICES, int(st.session_state.get(rest_key, 60))})
        # Tap-to-pick instead of a slider: Streamlit's slider draws its handle
        # mirrored in right-to-left browser languages (e.g. Hebrew).
        rest = rest_col.segmented_control(
            "Rest between sets",
            options=choices,
            format_func=_rest_label,
            required=True,
            key=rest_key,
        )
        st.toggle(
            "Different reps per set",
            key=f"{prefix}-vary-{row}",
            on_change=_sync_reps,
            args=(prefix, row),
        )

    exercise: api.Exercise = {
        "name": name,
        "sets": int(sets),
        "reps": reps,
        "rest_seconds": int(rest),
    }
    if notes := st.session_state.get(f"{prefix}-notes-{row}"):
        exercise["notes"] = notes
    return exercise


def exercise_editor(
    prefix: str,
    existing: list[api.Exercise] | None = None,
    starters: tuple[tuple[str, int, int, int], ...] = (),
) -> list[api.Exercise]:
    if _rows_key(prefix) not in st.session_state:
        load_exercises(prefix, existing or [])
    rows = st.session_state[_rows_key(prefix)]

    exercises: list[api.Exercise] = []
    with card():
        st.markdown("#### Exercises")
        st.caption(
            "Name it, set the sets and reps, pick a rest. Add as many as you like."
        )
        for position, row in enumerate(list(rows), start=1):
            exercises.append(_exercise_row(prefix, position, row, len(rows) > 1))

        st.button(
            "＋ Add exercise",
            key=f"{prefix}-add-exercise",
            on_click=add_row,
            args=(prefix,),
            disabled=len(rows) >= MAX_EXERCISES,
            width="stretch",
        )
        if starters:
            html_block(
                '<div class="fp-eyebrow" style="margin-top:.9rem">Quick add</div>'
            )
            with st.container(horizontal=True, key=f"fp-chips-{prefix}"):
                for index, (name, sets, reps, rest) in enumerate(starters):
                    st.button(
                        f"＋ {name}",
                        key=f"{prefix}-starter-{index}",
                        on_click=add_row,
                        args=(
                            prefix,
                            {
                                "name": name,
                                "sets": sets,
                                "reps": ", ".join([str(reps)] * sets),
                                "rest_seconds": rest,
                            },
                        ),
                    )
    return exercises


# --- Validation ------------------------------------------------------------------


def validate_workout(workout: dict) -> list[str]:
    errors = []
    for field, maximum in (("title", 200), ("goal", 100), ("experience_level", 50)):
        value = str(workout.get(field, "")).strip()
        label = field.replace("_", " ").capitalize()
        if not value:
            errors.append(f"{label} is required.")
        elif len(value) > maximum:
            errors.append(f"{label} must be at most {maximum} characters.")

    if not 1 <= int(workout.get("frequency_per_week", 0)) <= 7:
        errors.append("Workouts per week must be between 1 and 7.")
    exercises = workout.get("exercises", [])
    if not exercises:
        errors.append("Add at least one exercise.")
    for index, exercise in enumerate(exercises, start=1):
        name = str(exercise.get("name", exercise.get("exercise", ""))).strip()
        if not name:
            errors.append(f"Exercise {index} needs a name.")
        elif len(name) > 200:
            errors.append(f"Exercise {index} must be at most 200 characters.")
        if "name" in exercise:
            sets = int(exercise.get("sets", 0))
            if not 1 <= sets <= 100:
                errors.append(f"Exercise {index} sets must be between 1 and 100.")
            reps = [value.strip() for value in str(exercise.get("reps", "")).split(",")]
            if len(reps) != sets or any(
                not value.isdigit() or not 1 <= int(value) <= 10000 for value in reps
            ):
                errors.append(f"Exercise {index} needs one rep target for each set.")
            if not 0 <= int(exercise.get("rest_seconds", -1)) <= 3600:
                errors.append(
                    f"Exercise {index} rest must be between 0 and 3600 seconds."
                )
        elif not 1 <= int(exercise.get("count", 0)) <= 10000:
            errors.append(f"Exercise {index} count must be between 1 and 10000.")
    return errors


def show_errors(errors: list[str]) -> None:
    st.warning("Please fix: " + " ".join(errors))
