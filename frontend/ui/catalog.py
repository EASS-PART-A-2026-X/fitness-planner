"""Workout types for the Create flow: picture, words and starter exercises.

Each type id is at most 8 characters, because it is stored in the plan's icon
field (the backend allows 8). The pictures are line-art people in a 64×64 box,
drawn in the same stroke style as the app's other icons.
"""

from typing import NamedTuple


class WorkoutType(NamedTuple):
    id: str
    label: str
    tagline: str
    goal_hint: str
    tone: str  # "cardio" | "strength" | "mind"
    art: str
    starters: tuple[tuple[str, int, int, int], ...]  # (name, sets, reps, rest s)


_ART = {
    "running": (
        '<circle cx="40" cy="11" r="5"/><path d="M37 18 30 34"/>'
        '<path d="m36 22 8 6 5-5"/><path d="m35 21-8 3-5 6"/>'
        '<path d="m30 34 10 8-2 12"/><path d="m30 34-6 10-10 2"/>'
        '<path d="M4 28h9M2 36h8M6 44h6" opacity=".55"/>'
    ),
    "yoga": (
        '<circle cx="32" cy="12" r="5"/><path d="M32 18v18"/>'
        '<path d="M32 22 22 8M32 22 42 8"/><path d="M32 36v20"/>'
        '<path d="m32 38-10 7 9 3"/><path d="M16 60h32" opacity=".55"/>'
    ),
    "pilates": (
        '<circle cx="12" cy="43" r="5"/><path d="m17 45 19 3"/>'
        '<path d="M36 48 52 25"/><path d="m36 48 20 2"/><path d="m21 47 9 6"/>'
        '<path d="M4 58h56" opacity=".55"/>'
    ),
    "upper": (
        '<circle cx="32" cy="23" r="5"/><path d="M32 29v17"/>'
        '<path d="m32 33-11-4V15M32 33l11-4V15"/>'
        '<path d="M14 15h14M36 15h14"/><path d="M14 11v8M28 11v8M36 11v8M50 11v8"/>'
        '<path d="m32 46-6 13M32 46l6 13"/>'
    ),
    "lower": (
        '<circle cx="28" cy="13" r="5"/><path d="m28 19-3 16"/>'
        '<path d="m27 23 18 2"/><path d="m25 35 14 3-2 15"/>'
        '<path d="m25 35 8 6-1 12"/><path d="M12 56h40" opacity=".55"/>'
    ),
    "fullbody": (
        '<circle cx="32" cy="10" r="5"/><path d="M32 16v19"/>'
        '<path d="M32 21 18 8M32 21 46 8"/><path d="M32 35 20 56M32 35l12 21"/>'
        '<path d="M8 20l4 2M56 20l-4 2M10 32h5M54 32h-5" opacity=".55"/>'
    ),
    "core": (
        '<circle cx="12" cy="31" r="4.5"/><path d="m17 34 33 7"/>'
        '<path d="M18 35v10h8"/><path d="m50 41 4 8"/>'
        '<path d="M4 51h56" opacity=".55"/>'
    ),
    "hiit": (
        '<circle cx="30" cy="11" r="5"/><path d="M30 17v16"/>'
        '<path d="M30 21 20 9M30 21l10-12"/><path d="m30 33-8 6 6 9M30 33l8 6-5 9"/>'
        '<path d="m52 18-5 9h7l-5 9"/><path d="M20 58h20" opacity=".55"/>'
    ),
    "cycling": (
        '<circle cx="15" cy="47" r="10"/><circle cx="49" cy="47" r="10"/>'
        '<path d="m15 47 11-17h15l8 17M26 30l10 17 5-17"/>'
        '<circle cx="38" cy="11" r="4.5"/><path d="m36 16-9 13M35 18l8 10M27 29l8 9 1 9"/>'
    ),
    "swimming": (
        '<circle cx="47" cy="25" r="5"/><path d="m42 28-26 6"/>'
        '<path d="M41 28c3-10 13-13 18-6"/><path d="M16 34 7 29M16 34 5 37"/>'
        '<path d="M3 47c4-3 8-3 12 0s8 3 12 0 8-3 12 0 8 3 12 0 8-3 12 0" opacity=".55"/>'
        '<path d="M9 56c4-3 8-3 12 0s8 3 12 0 8-3 12 0 8 3 12 0" opacity=".35"/>'
    ),
    "boxing": (
        '<circle cx="26" cy="13" r="5"/><path d="m26 19 3 19"/>'
        '<path d="M27 24h12l8-2"/><circle cx="51" cy="21" r="4"/>'
        '<path d="m27 25-6 5 3-10"/><circle cx="25" cy="17" r="3.5"/>'
        '<path d="m29 38-8 18M29 38l10 18"/>'
    ),
    "stretch": (
        '<circle cx="33" cy="11" r="5"/><path d="M32 17q-3 10 0 21"/>'
        '<path d="M32 20q6-14 18-8"/><path d="m32 24-10 8"/>'
        '<path d="M32 38 21 58M32 38l12 20"/>'
    ),
    "custom": (
        '<circle cx="32" cy="32" r="20" stroke-dasharray="4 5"/>'
        '<path d="M32 24v16M24 32h16"/>'
    ),
}

WORKOUT_TYPES: tuple[WorkoutType, ...] = (
    WorkoutType(
        "running",
        "Running",
        "Build pace and endurance",
        "e.g. Run a 10k",
        "cardio",
        _ART["running"],
        (
            ("Easy run (minutes)", 1, 25, 0),
            ("Intervals 400 m", 6, 1, 90),
            ("Hill sprints", 6, 1, 60),
            ("Strides", 4, 1, 45),
        ),
    ),
    WorkoutType(
        "yoga",
        "Yoga",
        "Flow, balance and breath",
        "e.g. More flexibility",
        "mind",
        _ART["yoga"],
        (
            ("Sun salutation", 3, 5, 30),
            ("Warrior II (breaths)", 2, 8, 15),
            ("Tree pose (breaths)", 2, 6, 15),
            ("Downward dog (breaths)", 3, 5, 15),
        ),
    ),
    WorkoutType(
        "pilates",
        "Pilates",
        "Control, posture and core",
        "e.g. Better posture",
        "mind",
        _ART["pilates"],
        (
            ("The hundred", 1, 100, 30),
            ("Single leg stretch", 2, 10, 30),
            ("Roll up", 2, 8, 30),
            ("Side leg lifts", 2, 12, 30),
        ),
    ),
    WorkoutType(
        "upper",
        "Upper body",
        "Chest, back, shoulders, arms",
        "e.g. Stronger upper body",
        "strength",
        _ART["upper"],
        (
            ("Push-ups", 3, 12, 60),
            ("Dumbbell rows", 3, 10, 60),
            ("Shoulder press", 3, 10, 75),
            ("Bicep curls", 3, 12, 45),
        ),
    ),
    WorkoutType(
        "lower",
        "Lower body",
        "Legs and glutes",
        "e.g. Stronger legs",
        "strength",
        _ART["lower"],
        (
            ("Squats", 3, 12, 75),
            ("Lunges", 3, 10, 60),
            ("Glute bridges", 3, 15, 45),
            ("Calf raises", 3, 15, 45),
        ),
    ),
    WorkoutType(
        "fullbody",
        "Full body",
        "Everything in one session",
        "e.g. Get fit overall",
        "strength",
        _ART["fullbody"],
        (
            ("Burpees", 3, 10, 60),
            ("Squats", 3, 12, 60),
            ("Push-ups", 3, 10, 60),
            ("Plank (seconds)", 3, 40, 45),
        ),
    ),
    WorkoutType(
        "core",
        "Core",
        "Abs and stability",
        "e.g. A stronger core",
        "strength",
        _ART["core"],
        (
            ("Plank (seconds)", 3, 45, 45),
            ("Dead bug", 3, 10, 45),
            ("Bicycle crunches", 3, 20, 45),
            ("Side plank (seconds)", 2, 30, 30),
        ),
    ),
    WorkoutType(
        "hiit",
        "HIIT",
        "Short, sweaty intervals",
        "e.g. Burn fat fast",
        "cardio",
        _ART["hiit"],
        (
            ("Jumping jacks", 4, 30, 20),
            ("Mountain climbers", 4, 20, 20),
            ("Jump squats", 4, 12, 30),
            ("High knees", 4, 30, 20),
        ),
    ),
    WorkoutType(
        "cycling",
        "Cycling",
        "Ride longer and stronger",
        "e.g. Ride 50 km",
        "cardio",
        _ART["cycling"],
        (
            ("Endurance ride (minutes)", 1, 40, 0),
            ("Hill repeats", 5, 1, 120),
            ("Cadence drills (minutes)", 4, 2, 60),
        ),
    ),
    WorkoutType(
        "swimming",
        "Swimming",
        "Laps, technique, lungs",
        "e.g. Swim 1 km nonstop",
        "cardio",
        _ART["swimming"],
        (
            ("Freestyle 100 m", 4, 1, 45),
            ("Kick drill 50 m", 4, 1, 30),
            ("Backstroke 50 m", 4, 1, 30),
        ),
    ),
    WorkoutType(
        "boxing",
        "Boxing",
        "Power, speed, footwork",
        "e.g. Faster hands",
        "strength",
        _ART["boxing"],
        (
            ("Shadow boxing rounds", 3, 1, 60),
            ("Jab-cross combos", 4, 20, 45),
            ("Skipping (minutes)", 3, 2, 45),
        ),
    ),
    WorkoutType(
        "stretch",
        "Stretching",
        "Mobility and recovery",
        "e.g. Touch my toes",
        "mind",
        _ART["stretch"],
        (
            ("Hamstring stretch (breaths)", 2, 8, 10),
            ("Hip opener (breaths)", 2, 8, 10),
            ("Side bend (breaths)", 2, 6, 10),
            ("Cat-cow", 2, 10, 10),
        ),
    ),
)
TYPES_BY_ID = {item.id: item for item in WORKOUT_TYPES}
CUSTOM_ART = _ART["custom"]
TONES = {item.id: item.tone for item in WORKOUT_TYPES}

LEVELS = ("beginner", "intermediate", "advanced")
EQUIPMENT_LABELS = {
    "bodyweight": "Bodyweight",
    "dumbbells": "Dumbbells",
    "barbell": "Barbell",
    "kettlebell": "Kettlebell",
    "bands": "Resistance bands",
    "machines": "Gym machines",
    "bike": "Bike",
    "pool": "Pool",
}
BACKUP_NOTICE = (
    "The AI coach is busy right now, so your backup coach drafted these exercises "
    "from your goal, schedule, time and notes. Try again in a minute for an "
    "AI-written version."
)
