"""Plan form shared by the create and edit pages, plus client-side validation."""

import streamlit as st

import fitness_planner_api as api
from ui.components import card, html_block, safe_html, workout_icon
from ui.exercises import structured_exercise

MAX_EXERCISES = 100
EXERCISE_FIELDS = ("exercise", "count", "name", "sets", "reps", "rest")


def add_exercise_row(state_key: str) -> None:
    st.session_state[state_key] = min(
        st.session_state.get(state_key, 1) + 1, MAX_EXERCISES
    )


def remove_exercise_row(state_key: str, prefix: str) -> None:
    count = st.session_state.get(state_key, 1)
    if count <= 1:
        return
    for field in EXERCISE_FIELDS:
        st.session_state.pop(f"{prefix}-{field}-{count - 1}", None)
    st.session_state[state_key] = count - 1


def plan_details(
    prefix: str, initial: api.WorkoutPlan | None, icon_id: str, icon_note: str
) -> dict:
    """Title, goal, sessions per week and level. Keys are stable per plan."""
    initial = initial or {}
    with card():
        st.markdown("#### Plan details")
        title_col, goal_col = st.columns(2)
        title = title_col.text_input(
            "Workout name",
            value=initial.get("title", ""),
            max_chars=200,
            key=f"{prefix}-title",
        )
        goal = goal_col.text_input(
            "Goal", value=initial.get("goal", ""), max_chars=100, key=f"{prefix}-goal"
        )
        frequency_col, experience_col = st.columns(2)
        frequency = frequency_col.number_input(
            "Sessions per week",
            min_value=1,
            max_value=7,
            value=initial.get("frequency_per_week", 3),
            key=f"{prefix}-frequency",
        )
        experience = experience_col.text_input(
            "Experience level",
            value=initial.get("experience_level", ""),
            max_chars=50,
            key=f"{prefix}-experience",
        )
        html_block(
            '<div class="fp-workout">'
            f"{workout_icon(icon_id)}"
            f'<span class="fp-exercise-note">{safe_html(icon_note)}</span></div>'
        )
    return {
        "emoji": icon_id,
        "title": title,
        "goal": goal,
        "frequency_per_week": frequency,
        "experience_level": experience,
    }


def exercise_editor(
    prefix: str, existing: list[api.Exercise] | None = None
) -> list[api.Exercise]:
    state_key = f"{prefix}-exercise-rows"
    if state_key not in st.session_state:
        st.session_state[state_key] = max(1, len(existing or []))

    structured = [structured_exercise(item) for item in existing or []]
    exercises: list[api.Exercise] = []
    with card():
        st.markdown("#### Exercise lineup")
        st.caption("One target per set, separated by commas, e.g. 10, 10, 8.")
        for index in range(st.session_state[state_key]):
            initial = structured[index] if index < len(structured) else {}
            html_block(
                '<div class="fp-workout" style="margin-top:.6rem">'
                f'<span class="fp-index">{index + 1:02d}</span>'
                f'<span class="fp-exercise-name">Exercise {index + 1}</span></div>'
            )
            name_col, sets_col, reps_col, rest_col = st.columns([3, 1, 2, 1.2])
            exercise: api.Exercise = {
                "name": name_col.text_input(
                    "Exercise name",
                    value=initial.get("name", ""),
                    max_chars=200,
                    key=f"{prefix}-name-{index}",
                ),
                "sets": sets_col.number_input(
                    "Sets",
                    min_value=1,
                    max_value=100,
                    value=int(initial.get("sets", 3)),
                    key=f"{prefix}-sets-{index}",
                ),
                "reps": reps_col.text_input(
                    "Reps per set",
                    value=initial.get("reps", "10, 10, 10"),
                    max_chars=1000,
                    key=f"{prefix}-reps-{index}",
                ),
                "rest_seconds": rest_col.number_input(
                    "Rest (seconds)",
                    min_value=0,
                    max_value=3600,
                    value=int(initial.get("rest_seconds", 60)),
                    key=f"{prefix}-rest-{index}",
                ),
            }
            if initial.get("notes"):
                exercise["notes"] = initial["notes"]
            exercises.append(exercise)

        add_col, remove_col = st.columns(2)
        add_col.button(
            "＋ Add exercise",
            key=f"{prefix}-add-exercise",
            on_click=add_exercise_row,
            args=(state_key,),
            disabled=st.session_state[state_key] >= MAX_EXERCISES,
            width="stretch",
        )
        remove_col.button(
            "Remove last",
            key=f"{prefix}-remove-exercise",
            on_click=remove_exercise_row,
            args=(state_key, prefix),
            disabled=st.session_state[state_key] <= 1,
            width="stretch",
        )
    return exercises


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
