"""Live workout: pick an exercise, log each set, rest with a timer, finish."""

import time

import streamlit as st

import fitness_planner_api as api
from ui.components import card, html_block, plain, ring, safe_html, section
from ui.exercises import exercise_name, exercise_set_count, planned_reps
from ui.pages.plan import plan_heading
from ui.state import go, notify, set_page_state


def _timer_keys(prefix: str) -> tuple[str, str, str]:
    return (
        f"{prefix}-timer-mode",
        f"{prefix}-timer-started",
        f"{prefix}-timer-duration",
    )


def _clear_timer(prefix: str) -> None:
    for key in _timer_keys(prefix):
        st.session_state.pop(key, None)


@st.fragment(run_every="1s")
def rest_timer(prefix: str) -> None:
    mode_key, started_key, duration_key = _timer_keys(prefix)
    if st.session_state.get(mode_key) != "rest":
        return
    duration = st.session_state[duration_key]
    remaining = max(
        0, int(st.session_state[started_key] + duration - time.time() + 0.999)
    )
    if remaining == 0:
        _clear_timer(prefix)
        st.rerun(scope="app")

    minutes, seconds = divmod(remaining, 60)
    percent = round(remaining / duration * 100) if duration else 0
    html_block(
        '<div class="fp-timer">'
        f"{ring(percent, f'{minutes:02d}:{seconds:02d}', 'rest')}"
        '<div><div class="fp-eyebrow">Rest timer</div>'
        '<div class="fp-timer-title">Breathe. Next set is coming up.</div></div></div>'
    )
    if st.button("Skip rest", key=f"{mode_key}-skip-rest"):
        _clear_timer(prefix)
        st.rerun(scope="app")


def set_pills(
    exercise: api.Exercise, index: int, completed_sets: list[api.CompletedSet]
) -> None:
    done = {
        item["set_index"]: item["actual_reps"]
        for item in completed_sets
        if item["exercise_index"] == index
    }
    count = exercise_set_count(exercise)
    upcoming = next((i for i in range(count) if i not in done), None)
    pills = []
    for set_index in range(count):
        if set_index in done:
            state, value = "is-done", f"✓ {done[set_index]}"
        elif set_index == upcoming:
            state, value = "is-active", f"{planned_reps(exercise, set_index)} reps"
        else:
            state, value = "", f"{planned_reps(exercise, set_index)} reps"
        pills.append(
            f'<div class="fp-set {state}"><div class="fp-set-label">Set {set_index + 1}</div>'
            f'<div class="fp-set-value">{safe_html(value)}</div></div>'
        )
    html_block(
        f'<div class="fp-eyebrow">Sets · {len(done)} / {count} done</div>'
        f'<div class="fp-sets">{"".join(pills)}</div>'
    )


def render(token: str, workout_id: int) -> None:
    if st.button("← Back to plan", key="detail-back"):
        go("plan", workout_id=workout_id)
    try:
        with st.spinner("Loading workout..."):
            workout = api.read_workout(token, workout_id)
            saved = api.read_workout_session(token, workout_id)
    except api.BackendError as exc:
        st.error(str(exc))
        return

    exercises = workout["exercises"]
    if not exercises:
        st.info("This plan has no exercises yet. Edit the plan to add some.")
        return
    completed_sets: list[api.CompletedSet] = saved.get("completed_sets", [])
    done_keys = {(item["exercise_index"], item["set_index"]) for item in completed_sets}
    total_sets = sum(exercise_set_count(exercise) for exercise in exercises)
    prefix = f"session-{workout_id}"
    selected_key = f"{prefix}-exercise-index"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = next(
            (
                index
                for index, exercise in enumerate(exercises)
                if any(
                    (index, s) not in done_keys
                    for s in range(exercise_set_count(exercise))
                )
            ),
            0,
        )

    plan_heading(workout, "Live session")
    mode_key, started_key, duration_key = _timer_keys(prefix)
    resting = st.session_state.get(mode_key) == "rest"

    main_col, side_col = st.columns([1.7, 1], gap="large")
    with main_col, card():
        index = st.selectbox(
            "Exercise",
            range(len(exercises)),
            key=selected_key,
            format_func=lambda i: f"{i + 1:02d} · {exercise_name(exercises[i])}",
            disabled=resting,
        )
        exercise = exercises[index]
        if exercise.get("notes"):
            st.caption(exercise["notes"])
        set_pills(exercise, index, completed_sets)

        count = exercise_set_count(exercise)
        next_set = next((s for s in range(count) if (index, s) not in done_keys), None)
        if next_set is None:
            st.success(f"{exercise_name(exercise)} complete.")
        else:
            target = planned_reps(exercise, next_set)
            st.markdown(f"**Set {next_set + 1} of {count}** · target {target} reps")
            actual = st.number_input(
                "Actual reps completed",
                min_value=0,
                max_value=10000,
                value=target,
                key=f"{prefix}-actual-{index}-{next_set}",
                disabled=resting,
            )
            if resting:
                rest_timer(prefix)
            elif st.button(
                "Complete set ✓", key=f"{prefix}-complete-set", type="primary"
            ):
                updated = [
                    item
                    for item in completed_sets
                    if (item["exercise_index"], item["set_index"]) != (index, next_set)
                ] + [
                    {
                        "exercise_index": index,
                        "set_index": next_set,
                        "actual_reps": int(actual),
                    }
                ]
                try:
                    api.save_workout_session(token, workout_id, updated)
                except api.BackendError as exc:
                    st.error(f"Could not save your set. {exc}")
                else:
                    rest = int(exercise.get("rest_seconds", 60))
                    if next_set + 1 < count and rest:
                        st.session_state[mode_key] = "rest"
                        st.session_state[started_key] = time.time()
                        st.session_state[duration_key] = rest
                    else:
                        _clear_timer(prefix)
                    st.rerun()

    with side_col:
        section("Session")
        with card():
            percent = round(len(completed_sets) / total_sets * 100) if total_sets else 0
            html_block(
                '<div style="display:flex;justify-content:center;padding:.5rem 0 1rem">'
                f"{ring(percent, f'{len(completed_sets)}/{total_sets}', 'sets done')}</div>"
            )
            if st.button(
                "Finish workout ✓",
                key="finish-workout",
                type="primary",
                width="stretch",
            ):
                try:
                    api.complete_workout(token, workout_id, completed_sets)
                except api.BackendError as exc:
                    st.error(str(exc))
                else:
                    _clear_timer(prefix)
                    st.session_state.pop(selected_key, None)
                    st.session_state["celebrate"] = True
                    set_page_state("home")
                    notify(
                        f"Workout complete! {plain(workout['title'])} "
                        "added to this week's progress."
                    )
            _cancel(token, workout_id, prefix)


def _cancel(token: str, workout_id: int, prefix: str) -> None:
    confirm_key = f"cancel-workout-confirm-{workout_id}"
    if not st.session_state.get(confirm_key):
        if st.button("Cancel workout", key=f"{confirm_key}-open", width="stretch"):
            st.session_state[confirm_key] = True
            st.rerun()
        return
    st.warning("Discard this session's sets? It won't count as completed.")
    with st.container(key="fp-danger"):
        if st.button(
            "Yes, discard", key=f"{confirm_key}-yes", type="primary", width="stretch"
        ):
            try:
                api.cancel_workout_session(token, workout_id)
            except api.BackendError as exc:
                st.error(f"Could not cancel your workout. {exc}")
            else:
                st.session_state.pop(confirm_key, None)
                st.session_state.pop(f"{prefix}-exercise-index", None)
                _clear_timer(prefix)
                go("plan", workout_id=workout_id)
    if st.button("Keep training", key=f"{confirm_key}-no", width="stretch"):
        st.session_state.pop(confirm_key, None)
        st.rerun()
