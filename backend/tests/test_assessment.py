from datetime import date, timedelta
from types import SimpleNamespace as NS

import pytest

from app.services import assessment as A
from app.services.benchmarks import CohortKey, benchmark_for_event, dedupe_unique_athletes, percentile

TODAY = date(2026, 10, 11)


def ev(**kw):
    base = dict(id=1, name="E", task_key="deadlift_barbell", scoring_type="max_load", load_kg=160.0, load_per_hand=False,
                time_limit_s=None, distance_m=None, version=1, original_unit="kg", original_load_text="160 kg")
    base.update(kw)
    return NS(**base)


def rec(task="deadlift_barbell", load=None, reps=None, dist=None, t=None, days_ago=10, per_hand=False, rid=1, src="self_reported"):
    return NS(id=rid, task_key=task, load_kg=load, reps=reps, distance_m=dist, time_s=t, load_per_hand=per_hand,
              record_date=TODAY - timedelta(days=days_ago), source_type=src)


def eq(impl, access, mx=None):
    return NS(implement=impl, access=access, max_load_kg=mx)


def run(e, records, equipment=()):
    return A.assess_event(e, records, TODAY, {x.implement: x for x in equipment})


# ---- spec section 15 example
def test_heavier_single_does_not_establish_timed_reps():
    r = run(ev(scoring_type="reps", time_limit_s=60), [rec(load=180, reps=1)])
    assert r["status"] == "unknown"
    assert r["basis"] == "inferred"
    assert "no comparable timed set" in r["detail"]


def test_barbell_press_is_not_log_readiness():
    r = run(ev(task_key="log_clean_press", scoring_type="reps", load_kg=70, time_limit_s=75),
            [rec("press_barbell_strict", load=65, reps=1)], [eq("log", "none")])
    assert r["status"] == "implement_practice_gap"
    assert all(not x["comparable"] for x in r["evidence"])
    assert r["load_ratio"] is None


def test_carry_no_record_with_load_limit_below_event():
    r = run(ev(task_key="farmers_carry", scoring_type="time", load_kg=80, load_per_hand=True, distance_m=20, time_limit_s=45),
            [], [eq("farmers_handles", "regular", 40)])
    assert r["status"] == "implement_practice_gap"
    assert "load_limit_below_event" in r["equipment"]["flags"]


def test_no_access_no_record_is_gap_and_unrecorded_is_unknown():
    e = ev(task_key="sandbag_load", scoring_type="reps", load_kg=100, time_limit_s=60)
    assert run(e, [], [eq("sandbag", "none")])["status"] == "implement_practice_gap"
    unk = run(e, [], [])
    assert unk["status"] == "unknown" and "access_not_recorded" in unk["equipment"]["flags"]


# ---- comparisons
def test_max_load_demonstrated_and_gap_ratios():
    ok = run(ev(), [rec(load=180)])
    assert ok["status"] == "demonstrated" and ok["load_ratio"] == 1.125
    gap = run(ev(), [rec(load=140), rec(load=120, rid=2)])
    assert gap["status"] == "measured_gap" and gap["load_ratio"] == 0.875


def test_old_records_are_excluded():
    r = run(ev(), [rec(load=200, days_ago=400)])
    assert r["status"] == "unknown"
    assert any("older than" in x["note"] for x in r["evidence"])


def test_per_hand_vs_total_mismatch_not_comparable():
    e = ev(task_key="farmers_carry", scoring_type="time", load_kg=80, load_per_hand=True, distance_m=20, time_limit_s=45)
    r = run(e, [rec("farmers_carry", load=100, dist=20, t=20, per_hand=False)], [eq("farmers_handles", "regular", 120)])
    assert r["status"] == "unknown"
    assert any("per-hand" in x["note"] for x in r["evidence"])


def test_timed_set_at_load_demonstrates_reps_event():
    r = run(ev(scoring_type="reps", time_limit_s=60), [rec(load=160, reps=8, t=60)])
    assert r["status"] == "demonstrated"
    lighter = run(ev(scoring_type="reps", time_limit_s=60), [rec(load=140, reps=8, t=55)])
    assert lighter["status"] == "measured_gap" and lighter["load_ratio"] == 0.875
    over_time = run(ev(scoring_type="reps", time_limit_s=60), [rec(load=160, reps=8, t=90)])
    assert over_time["status"] == "unknown"


def test_carry_time_rules():
    e = ev(task_key="farmers_carry", scoring_type="time", load_kg=80, load_per_hand=True, distance_m=20, time_limit_s=45)
    good = run(e, [rec("farmers_carry", load=80, dist=20, t=30, per_hand=True)])
    assert good["status"] == "demonstrated"
    slow = run(e, [rec("farmers_carry", load=80, dist=20, t=60, per_hand=True)])
    assert slow["status"] == "measured_gap" and "time limit" in slow["detail"]
    short = run(e, [rec("farmers_carry", load=80, dist=10, t=10, per_hand=True)])
    assert short["status"] == "measured_gap" and "m vs" in short["detail"]


def test_missing_load_and_custom_scoring_are_unknown_not_invented():
    assert run(ev(load_kg=None), [rec(load=200)])["status"] == "unknown"
    assert run(ev(scoring_type="custom"), [rec(load=200)])["status"] == "unknown"


def test_yoke_not_inferred_from_squat():
    e = ev(task_key="yoke_carry", scoring_type="time", load_kg=140, distance_m=15, time_limit_s=40)
    r = run(e, [rec("squat_barbell", load=200, reps=5)], [eq("yoke", "none")])
    assert r["status"] == "implement_practice_gap" or r["status"] == "unknown"
    assert r["status"] != "demonstrated"


# ---- eligibility
def division(**kw):
    base = dict(category="men", weight_min_kg=None, weight_max_kg=105.0, age_min=None, age_max=None,
                eligibility_notes=None, needs_manual_confirmation=False)
    base.update(kw)
    return NS(**base)


def prof(**kw):
    base = dict(body_weight_kg=98.0, age=29, division_category="men")
    base.update(kw)
    return NS(**base)


COMP = NS(status="upcoming")


@pytest.mark.parametrize("bw,expected", [(105.0, "eligible"), (105.1, "ineligible"), (None, "needs_confirmation")])
def test_weight_boundary(bw, expected):
    assert A.check_eligibility(prof(body_weight_kg=bw), division(), COMP)["status"] == expected


def test_eligibility_other_cases():
    assert A.check_eligibility(prof(division_category="women"), division(), COMP)["status"] == "ineligible"
    assert A.check_eligibility(prof(division_category=None), division(), COMP)["status"] == "needs_confirmation"
    assert A.check_eligibility(prof(), division(needs_manual_confirmation=True), COMP)["status"] == "needs_confirmation"
    assert A.check_eligibility(prof(age=17), division(age_min=18), COMP)["status"] == "ineligible"
    assert A.check_eligibility(prof(), division(), NS(status="canceled"))["status"] == "ineligible"
    assert A.check_eligibility(None, division(category="open", weight_max_kg=None), COMP)["status"] == "eligible"


# ---- benchmarks
def test_percentile_conventions():
    assert percentile(5, [1, 2, 5, 5, 9]) == 100 * (2 + 1.0) / 5
    # timed: smaller is better, so slower results count as "below"
    assert percentile(30, [20, 30, 40, 50], higher_is_better=False) == 100 * (2 + 0.5) / 4
    with pytest.raises(ValueError):
        percentile(1, [])


def hist(n, athlete_prefix="a", load=150.0, value=lambda i: 100 + i, dups=0, task="deadlift_barbell", scoring="max_load", cat="men"):
    rows = [NS(task_key=task, scoring_type=scoring, division_category=cat, load_kg=load, load_per_hand=False, time_limit_s=None,
               distance_m=None, athlete_key=f"{athlete_prefix}{i}", competition_name="C", result_date=date(2026, 1, 1) + timedelta(days=i),
               result_value=float(value(i)), provenance="synthetic", is_synthetic=True) for i in range(n)]
    return rows + rows[:dups]


KEY = CohortKey("deadlift_barbell", "max_load", "men", 150.0, False, None, None)


def test_percentile_suppressed_below_20_but_shown_at_20_and_dedupes():
    small = benchmark_for_event(hist(19), KEY, 120.0)
    assert small["status"] == "limited_sample" and "percentile" not in small and small["sample_size"] == 19
    assert len(small["results"]) <= 10
    # 18 unique + 5 duplicates must not reach 20
    assert benchmark_for_event(hist(18, dups=5), KEY, 120.0)["status"] == "limited_sample"
    big = benchmark_for_event(hist(20), KEY, 110.0)
    assert big["status"] == "percentile" and big["percentile"] == 52.5  # (10 below + 0.5 * 1 tie) / 20
    assert big["sample_size"] == 20 and big["cohort"]["load_kg"] == 150.0


def test_cohort_not_broadened_when_conditions_differ():
    other_load = benchmark_for_event(hist(30, load=140.0), KEY, 120.0)
    assert other_load["status"] == "no_cohort"
    other_cat = benchmark_for_event(hist(30, cat="women"), KEY, 120.0)
    assert other_cat["status"] == "no_cohort"
    other_scoring = benchmark_for_event(hist(30, scoring="reps"), KEY, 120.0)
    assert other_scoring["status"] == "no_cohort"
    assert benchmark_for_event(hist(30), CohortKey("x", "custom", "men", 1, False, None, None), 1)["status"] == "unsupported"


def test_no_athlete_value_no_percentile_and_time_direction():
    r = benchmark_for_event(hist(25), KEY, None)
    assert r["status"] == "no_athlete_value" and "percentile" not in r
    tkey = CohortKey("farmers_carry", "time", "men", 80.0, False, None, 20.0)
    rows = [NS(task_key="farmers_carry", scoring_type="time", division_category="men", load_kg=80.0, load_per_hand=False,
               time_limit_s=None, distance_m=20.0, athlete_key=f"t{i}", competition_name="C", result_date=date(2026, 1, 1),
               result_value=20.0 + i, provenance="s", is_synthetic=True) for i in range(20)]
    fast = benchmark_for_event(rows, tkey, 10.0)
    assert fast["percentile"] == 100.0  # faster than everyone


def test_dedupe_keeps_best_per_athlete():
    a = NS(athlete_key="x", competition_name="c1", result_date=date(2026, 1, 1), result_value=100.0)
    b = NS(athlete_key="x", competition_name="c2", result_date=date(2026, 2, 1), result_value=120.0)
    assert [r.result_value for r in dedupe_unique_athletes([a, a, b], True)] == [120.0]
