"""Helpers that read both exercise shapes: legacy {exercise, count} and structured."""

import fitness_planner_api as api


def exercise_name(exercise: api.Exercise) -> str:
    return exercise.get("name", exercise.get("exercise", "Exercise"))


def exercise_set_count(exercise: api.Exercise) -> int:
    return int(exercise.get("sets", 1))


def planned_reps(exercise: api.Exercise, set_index: int) -> int:
    if "reps" in exercise:
        values = [value.strip() for value in exercise["reps"].split(",")]
        target = values[min(set_index, len(values) - 1)]
    else:
        target = str(exercise.get("count", 1))
    try:
        return int(target)
    except ValueError:
        return 0


def exercise_spec(exercise: api.Exercise) -> tuple[str, str]:
    """Headline and sub-line for an exercise row, e.g. ('3 × 10, 10, 8', '60 s rest')."""
    if "name" in exercise:
        return (
            f"{exercise['sets']} × {exercise['reps']}",
            f"{exercise.get('rest_seconds', 60)} s rest",
        )
    return f"{exercise.get('count', 1)} reps", "single set"


def structured_exercise(exercise: api.Exercise) -> api.Exercise:
    if "name" in exercise:
        return exercise
    return {
        "name": exercise["exercise"],
        "sets": 1,
        "reps": str(exercise["count"]),
        "rest_seconds": 60,
    }
