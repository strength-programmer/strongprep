"""Historical benchmarking. Percentiles only for compatible cohorts of >= MIN unique athletes."""
from dataclasses import dataclass
from datetime import date
from statistics import median

from app.config import MIN_PERCENTILE_COHORT


def percentile(value: float, sample: list[float], higher_is_better: bool = True) -> float:
    """100 * (n_worse + 0.5 * n_equal) / n. 'Worse' = lower when higher is better, else slower/higher."""
    n = len(sample)
    if n == 0:
        raise ValueError("empty sample")
    worse = sum(1 for s in sample if (s < value if higher_is_better else s > value))
    equal = sum(1 for s in sample if s == value)
    return 100.0 * (worse + 0.5 * equal) / n


@dataclass(frozen=True)
class CohortKey:
    task_key: str
    scoring_type: str
    division_category: str
    load_kg: float | None
    load_per_hand: bool
    time_limit_s: float | None
    distance_m: float | None


def dedupe_unique_athletes(rows: list, higher_is_better: bool) -> list:
    """Collapse duplicate result rows (same athlete+competition) then keep each athlete's best."""
    seen = {}
    for r in rows:
        seen[(r.athlete_key, r.competition_name, r.result_date)] = r
    best = {}
    for r in seen.values():
        cur = best.get(r.athlete_key)
        if cur is None or (r.result_value > cur.result_value if higher_is_better else r.result_value < cur.result_value):
            best[r.athlete_key] = r
    return list(best.values())


def _matches(r, key: CohortKey) -> bool:
    return (
        r.task_key == key.task_key
        and r.scoring_type == key.scoring_type
        and r.division_category == key.division_category
        and r.load_kg == key.load_kg
        and bool(r.load_per_hand) == key.load_per_hand
        and r.time_limit_s == key.time_limit_s
        and r.distance_m == key.distance_m
    )


UNITS = {"max_load": "kg", "reps": "reps", "time": "s", "distance": "m"}


def benchmark_for_event(all_results: list, key: CohortKey, athlete_value: float | None) -> dict:
    if key.scoring_type not in UNITS:
        return {"status": "unsupported", "reason": "Custom scoring cannot be benchmarked."}
    higher = key.scoring_type != "time"
    matched = [r for r in all_results if _matches(r, key)]
    unique = dedupe_unique_athletes(matched, higher)
    cohort = {
        "task": key.task_key,
        "scoring": key.scoring_type,
        "division_category": key.division_category,
        "load_kg": key.load_kg,
        "load_per_hand": key.load_per_hand,
        "time_limit_s": key.time_limit_s,
        "distance_m": key.distance_m,
        "performance_category": "novice (as labelled in source rows)",
        "criteria": "exact match on task/implement, scoring type, division category, load, per-hand flag, time limit and distance",
    }
    if not unique:
        return {"status": "no_cohort", "cohort": cohort, "sample_size": 0,
                "reason": "No compatible historical results. Broader cohorts are not substituted."}
    values = [r.result_value for r in unique]
    dates = [r.result_date for r in unique]
    info = {
        "cohort": cohort,
        "sample_size": len(unique),
        "unit": UNITS[key.scoring_type],
        "date_range": [min(dates).isoformat(), max(dates).isoformat()],
        "sources": sorted({r.provenance for r in unique}),
        "synthetic": all(r.is_synthetic for r in unique),
        "min": min(values), "median": median(values), "max": max(values),
        "tie_convention": "ties count half; each athlete counted once (best result); duplicates removed",
        "limitations": ["Percentile (if shown) is within the collected records only, not the whole sport."],
    }
    if athlete_value is None:
        info.update(status="no_athlete_value", reason="No comparable athlete record at these exact conditions.")
        info["results"] = _listing(unique)
        return info
    info["athlete_value"] = athlete_value
    if len(unique) < MIN_PERCENTILE_COHORT:
        info.update(
            status="limited_sample",
            reason=f"Fewer than {MIN_PERCENTILE_COHORT} unique matched athletes ({len(unique)}); percentile suppressed.",
            results=_listing(unique),
        )
        return info
    info.update(status="percentile", percentile=round(percentile(athlete_value, values, higher), 1))
    return info


def _listing(unique: list) -> list[dict]:
    return [
        {"athlete": r.athlete_key, "value": r.result_value, "date": r.result_date.isoformat(), "competition": r.competition_name}
        for r in sorted(unique, key=lambda r: r.result_date, reverse=True)[:10]
    ]
