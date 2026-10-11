"""Controlled vocabularies. A task key already encodes the implement, so two task keys are
never silently treated as equivalent, even within the same family."""

IMPLEMENTS = {
    "barbell": "Barbell + plates",
    "dumbbell": "Dumbbells",
    "kettlebell": "Kettlebells",
    "rack_bench": "Squat rack / bench",
    "log": "Log",
    "axle": "Axle bar",
    "yoke": "Yoke",
    "farmers_handles": "Farmer's handles",
    "stones": "Atlas stones",
    "sandbag": "Sandbag",
    "sled": "Sled / prowler",
}

# key -> label, family, implement, kind
TASKS = {
    "deadlift_barbell": {"label": "Deadlift (standard barbell)", "family": "deadlift", "implement": "barbell"},
    "deadlift_axle": {"label": "Deadlift (axle bar)", "family": "deadlift", "implement": "axle"},
    "press_barbell_strict": {"label": "Strict overhead press (barbell)", "family": "press", "implement": "barbell"},
    "log_clean_press": {"label": "Log clean and press", "family": "press", "implement": "log"},
    "axle_clean_press": {"label": "Axle clean and press", "family": "press", "implement": "axle"},
    "farmers_carry": {"label": "Farmer's carry", "family": "carry", "implement": "farmers_handles"},
    "yoke_carry": {"label": "Yoke carry", "family": "carry", "implement": "yoke"},
    "stone_load": {"label": "Stone loading", "family": "loading", "implement": "stones"},
    "sandbag_load": {"label": "Sandbag loading", "family": "loading", "implement": "sandbag"},
    "squat_barbell": {"label": "Back squat (barbell)", "family": "squat", "implement": "barbell"},
}

SCORING_TYPES = ["max_load", "reps", "time", "distance", "custom"]
SOURCE_TYPES = ["self_reported", "verified_training", "official_result"]
ACCESS_LEVELS = ["regular", "occasional", "none"]
DIVISION_CATEGORIES = ["men", "women", "open"]
BODY_AREAS = ["shoulder", "lower_back", "knee", "elbow", "wrist", "hip", "grip"]

LB_PER_KG = 2.20462262185
