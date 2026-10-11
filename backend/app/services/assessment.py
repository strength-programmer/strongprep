"""Deterministic eligibility and event-level preparation-gap rules. No model calls here.

Rules (product rules to be reviewed by a qualified coach; not validated readiness categories):
  * A performance record is comparable to an event only if the task key (implement included) matches
    and the per-hand flag matches. Same-family records on other implements are only "related".
  * Missing data stays missing; there is no overall readiness score.
"""
from datetime import date, timedelta

from app.config import CALCULATION_VERSION, RECENT_RECORD_DAYS
from app.data.reference import TASKS
from app.services.benchmarks import CohortKey, benchmark_for_event

STATUS_LABELS = {
    "demonstrated": "Demonstrated under recorded conditions",
    "measured_gap": "Measured performance gap",
    "implement_practice_gap": "Implement-practice gap",
    "unknown": "Unknown",
}
STATUS_RANK = {"measured_gap": 1, "implement_practice_gap": 2, "unknown": 3, "demonstrated": 4}


# ---------------------------------------------------------------- eligibility
def check_eligibility(profile, division, competition) -> dict:
    checks: list[dict] = []

    def add(name, result, detail):
        checks.append({"check": name, "result": result, "detail": detail})  # pass | fail | unknown

    if competition.status == "canceled":
        add("competition_status", "fail", "Competition is listed as canceled.")
    elif competition.status == "completed":
        add("competition_status", "fail", "Competition is listed as completed.")

    if division.category != "open":
        if not profile or not profile.division_category:
            add("category", "unknown", f"Division is '{division.category}'; your category is not recorded.")
        elif profile.division_category != division.category:
            add("category", "fail", f"Division is '{division.category}'; your profile says '{profile.division_category}'.")
        else:
            add("category", "pass", f"Category '{division.category}' matches.")

    bw = profile.body_weight_kg if profile else None
    if division.weight_min_kg is not None or division.weight_max_kg is not None:
        lo, hi = division.weight_min_kg, division.weight_max_kg
        rng = f"{'≥' + str(lo) if lo is not None else ''}{' and ' if lo is not None and hi is not None else ''}{'≤' + str(hi) if hi is not None else ''} kg (bounds inclusive)"
        if bw is None:
            add("body_weight", "unknown", f"Division requires {rng}; your body weight is not recorded.")
        elif (lo is not None and bw < lo) or (hi is not None and bw > hi):
            add("body_weight", "fail", f"Division requires {rng}; you recorded {bw} kg.")
        else:
            add("body_weight", "pass", f"{bw} kg is within {rng}.")

    age = profile.age if profile else None
    if division.age_min is not None or division.age_max is not None:
        lo, hi = division.age_min, division.age_max
        if age is None:
            add("age", "unknown", "Division has an age rule; your age is not recorded.")
        elif (lo is not None and age < lo) or (hi is not None and age > hi):
            add("age", "fail", f"Age {age} is outside the division's range ({lo}–{hi}).")
        else:
            add("age", "pass", f"Age {age} is within range.")

    if division.needs_manual_confirmation or division.eligibility_notes:
        add("organizer_rules", "unknown",
            "Organizer entry rules cannot be checked automatically: " + (division.eligibility_notes or "confirm with the organizer."))

    results = {c["result"] for c in checks}
    status = "ineligible" if "fail" in results else "needs_confirmation" if "unknown" in results else "eligible"
    return {
        "status": status,
        "checks": checks,
        "note": "Eligibility does not establish safety, expected placing, or event competence.",
    }


# ---------------------------------------------------------------- helpers
def _rec_view(r, comparable: bool, note: str = "") -> dict:
    return {
        "record_id": r.id, "date": r.record_date.isoformat(), "source_type": r.source_type,
        "task_key": r.task_key, "load_kg": r.load_kg, "load_per_hand": r.load_per_hand, "reps": r.reps,
        "distance_m": r.distance_m, "time_s": r.time_s, "comparable": comparable, "note": note,
    }


def _equipment_flags(ev, equipment_by_impl: dict) -> tuple[list[str], str]:
    impl = TASKS.get(ev.task_key, {}).get("implement")
    eq = equipment_by_impl.get(impl)
    flags = []
    if eq is None:
        flags.append("access_not_recorded")
        return flags, "unrecorded"
    if eq.access == "none":
        flags.append("no_access")
    elif eq.access == "occasional":
        flags.append("occasional_access")
    if eq.access != "none" and eq.max_load_kg is not None and ev.load_kg is not None and eq.max_load_kg < ev.load_kg:
        flags.append("load_limit_below_event")
    return flags, eq.access


def _ratio(num, den):
    return round(num / den, 3) if num is not None and den else None


# ---------------------------------------------------------------- per-event
def assess_event(ev, records: list, today: date, equipment_by_impl: dict) -> dict:
    task = TASKS.get(ev.task_key)
    cutoff = today - timedelta(days=RECENT_RECORD_DAYS)
    evidence: list[dict] = []
    comparable = []
    related = []
    for r in records:
        if r.task_key == ev.task_key:
            if r.record_date < cutoff:
                evidence.append(_rec_view(r, False, f"Excluded: older than {RECENT_RECORD_DAYS} days."))
            elif ev.load_per_hand != r.load_per_hand:
                evidence.append(_rec_view(r, False, "Excluded: per-hand vs total load do not match the event."))
            else:
                comparable.append(r)
        elif task and TASKS.get(r.task_key, {}).get("family") == task["family"] and r.record_date >= cutoff:
            related.append(r)
            evidence.append(_rec_view(r, False, "Related general strength only; different implement/task. Not equivalent."))

    flags, access = _equipment_flags(ev, equipment_by_impl)
    out = {
        "event_id": ev.id, "event_name": ev.name, "task_key": ev.task_key, "scoring_type": ev.scoring_type,
        "spec_version": ev.version,
        "requirement": {"load_kg": ev.load_kg, "load_per_hand": ev.load_per_hand, "time_limit_s": ev.time_limit_s,
                        "distance_m": ev.distance_m, "original_load_text": ev.original_load_text,
                        "original_unit": ev.original_unit},
        "equipment": {"access": access, "flags": flags},
        "load_ratio": None, "basis": "unavailable", "status": None, "detail": "", "next_step": "",
    }
    status, detail, basis, ratio = _evaluate(ev, comparable, related, evidence, flags)
    out.update(status=status, detail=detail, basis=basis, load_ratio=ratio, evidence=evidence)
    out["status_label"] = STATUS_LABELS[status]
    out["next_step"] = _next_step(ev, status, flags, bool(related), task)
    return out


def _evaluate(ev, comparable, related, evidence, flags):
    """Returns (status, detail, basis, load_ratio). basis: observed | inferred | unavailable."""
    if ev.scoring_type == "custom":
        return "unknown", "Custom scoring is not supported by the automatic rules; review the event rules manually.", "unavailable", None
    if ev.scoring_type not in ("max_load", "reps", "time", "distance"):
        return "unknown", f"Unrecognised scoring type '{ev.scoring_type}'.", "unavailable", None
    if ev.load_kg is None:
        return "unknown", "The event load is missing from the specification, so no comparison is possible.", "unavailable", None

    L, T, D = ev.load_kg, ev.time_limit_s, ev.distance_m
    for r in comparable:
        evidence.append(_rec_view(r, True))

    with_load = [r for r in comparable if r.load_kg is not None]

    if ev.scoring_type == "max_load":
        if with_load:
            best = max(with_load, key=lambda r: r.load_kg)
            ratio = _ratio(best.load_kg, L)
            if best.load_kg >= L:
                return "demonstrated", f"Recorded {best.load_kg:g} kg on the same task vs {L:g} kg required.", "observed", ratio
            return "measured_gap", f"Best comparable record is {best.load_kg:g} kg vs {L:g} kg required.", "observed", ratio

    elif ev.scoring_type in ("reps", "distance"):
        def in_rules(r):
            if r.load_kg is None:
                return False
            if ev.scoring_type == "reps" and not (r.reps and r.reps >= 2):
                return False
            if ev.scoring_type == "distance" and r.distance_m is None:
                return False
            return r.time_s is not None and (T is None or r.time_s <= T)

        timed = [r for r in with_load if in_rules(r)]
        at_load = [r for r in timed if r.load_kg >= L]
        if at_load:
            b = max(at_load, key=lambda r: (r.reps or 0) if ev.scoring_type == "reps" else (r.distance_m or 0))
            what = f"{b.reps} reps" if ev.scoring_type == "reps" else f"{b.distance_m:g} m"
            return "demonstrated", f"A timed set at {b.load_kg:g} kg ({what} in {b.time_s:g}s) meets the event load and time limit.", "observed", _ratio(b.load_kg, L)
        if timed:
            b = max(timed, key=lambda r: r.load_kg)
            return "measured_gap", f"Best comparable timed set used {b.load_kg:g} kg vs {L:g} kg required.", "observed", _ratio(b.load_kg, L)
        if with_load:
            b = max(with_load, key=lambda r: r.load_kg)
            return ("unknown",
                    f"A {b.load_kg:g} kg record exists on this task (load ratio {_ratio(b.load_kg, L)}), but no comparable timed set "
                    f"within the event's time limit, so performance under event rules is unknown.", "inferred", None)

    else:  # time
        enough = [r for r in with_load if r.distance_m is not None and r.time_s is not None]
        if enough:
            meets = [r for r in enough if r.load_kg >= L and (D is None or r.distance_m >= D) and (T is None or r.time_s <= T)]
            if meets:
                b = min(meets, key=lambda r: r.time_s)
                return "demonstrated", f"{b.load_kg:g} kg over {b.distance_m:g} m in {b.time_s:g}s meets the event load, distance and time limit.", "observed", _ratio(b.load_kg, L)
            far = [r for r in enough if D is None or r.distance_m >= D]
            if far:
                b = max(far, key=lambda r: r.load_kg)
                if b.load_kg >= L:
                    return "measured_gap", f"Load met ({b.load_kg:g} kg) but the time limit of {T:g}s was not.", "observed", _ratio(b.load_kg, L)
                return "measured_gap", f"Best comparable carry used {b.load_kg:g} kg vs {L:g} kg required.", "observed", _ratio(b.load_kg, L)
            b = max(enough, key=lambda r: r.distance_m)
            return "measured_gap", f"Best comparable record covers {b.distance_m:g} m vs {D:g} m required.", "observed", None

    # No usable comparable evidence
    if related:
        return ("implement_practice_gap",
                "General strength evidence exists on other implements, but no record on this event's implement/task. "
                "Related records do not establish readiness for this event.", "inferred", None)
    if "no_access" in flags or "load_limit_below_event" in flags:
        why = "no access to the implement" if "no_access" in flags else "your equipment load limit is below the event load"
        return "implement_practice_gap", f"No comparable record, and {why}.", "unavailable", None
    return "unknown", "No comparable record and no related evidence is available.", "unavailable", None


def _next_step(ev, status, flags, has_related, task) -> str:
    impl = task["label"] if task else ev.task_key
    steps = []
    if status == "measured_gap":
        steps.append(f"Build toward the event requirement on {impl}; re-record a comparable set to update the report.")
    elif status == "implement_practice_gap":
        steps.append(f"Arrange practice access for {impl}" + (" and keep general strength work going." if has_related else "."))
    elif status == "unknown":
        steps.append(f"Record a comparable set on {impl} under the event rules (or complete the missing event details).")
    else:
        steps.append("Maintain; re-test closer to the event under the same rules.")
    if "no_access" in flags:
        steps.append("You have no recorded access: confirm a place to practise before relying on this event.")
    if "occasional_access" in flags:
        steps.append("Access is occasional: schedule it deliberately.")
    if "load_limit_below_event" in flags:
        steps.append("Your recorded load limit is below the event load.")
    if "access_not_recorded" in flags:
        steps.append("Record your access to this implement in your profile.")
    return " ".join(steps)


# ---------------------------------------------------------------- benchmark value
def athlete_value_for_benchmark(ev, records: list, today: date):
    cutoff = today - timedelta(days=RECENT_RECORD_DAYS)
    rs = [r for r in records if r.task_key == ev.task_key and r.record_date >= cutoff and r.load_per_hand == ev.load_per_hand]
    if ev.scoring_type == "max_load":
        v = [r.load_kg for r in rs if r.load_kg is not None]
        return max(v) if v else None
    if ev.scoring_type == "reps":
        v = [r.reps for r in rs if r.load_kg == ev.load_kg and r.reps and r.time_s == ev.time_limit_s]
        return max(v) if v else None
    if ev.scoring_type == "distance":
        v = [r.distance_m for r in rs if r.load_kg == ev.load_kg and r.distance_m is not None and r.time_s == ev.time_limit_s]
        return max(v) if v else None
    if ev.scoring_type == "time":
        v = [r.time_s for r in rs if r.load_kg == ev.load_kg and r.distance_m == ev.distance_m and r.time_s is not None]
        return min(v) if v else None
    return None


# ---------------------------------------------------------------- whole report
def build_assessment(profile, equipment: list, records: list, competition, division, history: list, today: date | None = None) -> dict:
    today = today or date.today()
    by_impl = {e.implement: e for e in equipment}
    events = []
    data_gaps = []
    for ev in division.events:
        a = assess_event(ev, records, today, by_impl)
        if ev.load_kg is None and ev.scoring_type != "custom":
            data_gaps.append(f"'{ev.name}': load missing")
        if ev.original_unit in (None, "unknown") and ev.load_kg is not None:
            data_gaps.append(f"'{ev.name}': original unit not confirmed")
        key = CohortKey(ev.task_key, ev.scoring_type, division.category, ev.load_kg, bool(ev.load_per_hand), ev.time_limit_s, ev.distance_m)
        a["benchmark"] = benchmark_for_event(history, key, athlete_value_for_benchmark(ev, records, today))
        events.append(a)
    ranked = sorted(events, key=lambda e: (STATUS_RANK[e["status"]], (e["load_ratio"] if e["load_ratio"] is not None else 99)))
    for i, e in enumerate(ranked, 1):
        e["priority"] = i
    summary = {s: sum(1 for e in events if e["status"] == s) for s in STATUS_LABELS}
    if competition.verification_status != "verified":
        data_gaps.append("Competition details are not verified by an organizer or reviewer.")
    return {
        "calculation_version": CALCULATION_VERSION,
        "competition": {"id": competition.id, "title": competition.title, "date": competition.start_date.isoformat(),
                        "status": competition.status, "is_demo": competition.is_demo, "demo_label": competition.demo_label},
        "division": {"id": division.id, "name": division.name, "category": division.category, "spec_version": division.spec_version},
        "eligibility": check_eligibility(profile, division, competition),
        "events": events,
        "priority_order": [e["event_id"] for e in ranked],
        "summary_counts": summary,
        "data_gaps": data_gaps,
        "disclaimer": "Event-level table only. No overall readiness score or placing prediction is produced.",
    }
