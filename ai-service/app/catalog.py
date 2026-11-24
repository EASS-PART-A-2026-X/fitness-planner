"""The exercise catalog the agent may choose from, plus pure helper functions."""

from dataclasses import dataclass
from typing import Literal

Focus = Literal["strength", "cardio", "mobility", "core"]


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    equipment: str
    focus: Focus
    seconds_per_rep: int = 3
    high_impact: bool = False


CATALOG: tuple[CatalogEntry, ...] = (
    # Bodyweight
    CatalogEntry("Push-ups", "bodyweight", "strength"),
    CatalogEntry("Bodyweight squats", "bodyweight", "strength"),
    CatalogEntry("Reverse lunges", "bodyweight", "strength"),
    CatalogEntry("Glute bridges", "bodyweight", "strength"),
    CatalogEntry("Plank hold (seconds)", "bodyweight", "core", seconds_per_rep=1),
    CatalogEntry("Dead bugs", "bodyweight", "core"),
    CatalogEntry("Bird dogs", "bodyweight", "core"),
    CatalogEntry("Mountain climbers", "bodyweight", "cardio", 1, high_impact=True),
    CatalogEntry("Burpees", "bodyweight", "cardio", 4, high_impact=True),
    CatalogEntry("Jumping jacks", "bodyweight", "cardio", 1, high_impact=True),
    CatalogEntry("Fast step-ups", "bodyweight", "cardio", 2),
    CatalogEntry("World's greatest stretch", "bodyweight", "mobility", 6),
    CatalogEntry("Cat-cow", "bodyweight", "mobility", 4),
    CatalogEntry("Downward dog to cobra", "bodyweight", "mobility", 5),
    CatalogEntry("Hip flexor stretch (seconds)", "bodyweight", "mobility", 1),
    # Dumbbells
    CatalogEntry("Dumbbell bench press", "dumbbells", "strength"),
    CatalogEntry("Goblet squat", "dumbbells", "strength"),
    CatalogEntry("One-arm dumbbell row", "dumbbells", "strength"),
    CatalogEntry("Dumbbell Romanian deadlift", "dumbbells", "strength"),
    CatalogEntry("Dumbbell shoulder press", "dumbbells", "strength"),
    CatalogEntry("Dumbbell thrusters", "dumbbells", "cardio"),
    # Barbell
    CatalogEntry("Barbell back squat", "barbell", "strength", 4),
    CatalogEntry("Barbell deadlift", "barbell", "strength", 4),
    CatalogEntry("Barbell bench press", "barbell", "strength", 4),
    CatalogEntry("Barbell overhead press", "barbell", "strength", 4),
    CatalogEntry("Barbell bent-over row", "barbell", "strength", 4),
    # Kettlebell
    CatalogEntry("Kettlebell swings", "kettlebell", "cardio", 2),
    CatalogEntry("Kettlebell clean and press", "kettlebell", "strength", 4),
    CatalogEntry("Turkish get-up", "kettlebell", "core", 20),
    # Bands
    CatalogEntry("Band pull-aparts", "bands", "mobility"),
    CatalogEntry("Banded rows", "bands", "strength"),
    CatalogEntry("Banded lateral walks", "bands", "strength", 2),
    CatalogEntry("Pallof press", "bands", "core"),
    # Machines
    CatalogEntry("Leg press", "machines", "strength"),
    CatalogEntry("Lat pulldown", "machines", "strength"),
    CatalogEntry("Seated cable row", "machines", "strength"),
    CatalogEntry("Chest press machine", "machines", "strength"),
    CatalogEntry("Rowing machine intervals (seconds)", "machines", "cardio", 1),
    # Bike and pool
    CatalogEntry("Bike sprint intervals (seconds)", "bike", "cardio", 1),
    CatalogEntry("Steady bike ride (minutes)", "bike", "cardio", 60),
    CatalogEntry("Freestyle laps", "pool", "cardio", 45),
    CatalogEntry("Kickboard laps", "pool", "cardio", 50),
)
CATALOG_BY_NAME = {entry.name.casefold(): entry for entry in CATALOG}
WARM_UP_MINUTES = 3


def available_exercises(equipment: frozenset[str]) -> list[CatalogEntry]:
    """Bodyweight moves are always available; the rest need the right gear."""
    return [
        entry
        for entry in CATALOG
        if entry.equipment == "bodyweight" or entry.equipment in equipment
    ]


def parse_reps(reps: str) -> list[int] | None:
    """Return the per-set targets, or None when the text is not a number list."""
    values = [value.strip() for value in reps.split(",")]
    if not values or not all(value.isdigit() for value in values):
        return None
    return [int(value) for value in values]


def estimate_minutes(
    sets: int,
    reps: list[int],
    rest_seconds: int,
    seconds_per_rep: int = 3,
) -> float:
    """Working time plus rest between sets for one exercise, in minutes."""
    work = sum(reps[:sets]) * seconds_per_rep
    rest = max(0, sets - 1) * rest_seconds
    return round((work + rest) / 60, 1)


def goal_focus(goal: str) -> Focus | None:
    text = goal.casefold()
    keywords: tuple[tuple[Focus, tuple[str, ...]], ...] = (
        ("mobility", ("mobil", "flexib", "yoga", "stretch", "posture", "back pain")),
        ("cardio", ("cardio", "endur", "run", "stamina", "fat", "weight loss", "lose")),
        ("core", ("core", "abs", "six pack")),
        ("strength", ("strength", "strong", "muscle", "hypertrophy", "power", "bulk")),
    )
    for focus, words in keywords:
        if any(word in text for word in words):
            return focus
    return None
