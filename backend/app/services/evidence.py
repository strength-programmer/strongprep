"""Fingerprints of the athlete data that feed a report or plan, used to detect staleness.

A report is built from: eligibility fields (body weight, age, category), equipment access, and performance
records. Only fields the calculations actually read are included, so cosmetic edits (display name, city, notes,
effort, conditions) never mark a report stale. Equipment row ids are excluded because saving the equipment form
replaces rows; saving unchanged content must not change the fingerprint.
"""
import hashlib
import json


def _digest(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def evidence_fingerprint(profile, equipment: list, records: list) -> str:
    return _digest({
        "eligibility": [profile.body_weight_kg, profile.age, profile.division_category] if profile else None,
        "equipment": sorted([e.implement, e.access, e.max_load_kg, e.carry_space_m] for e in equipment),
        "records": sorted(
            [r.id, r.task_key, r.load_kg, bool(r.load_per_hand), r.reps, r.distance_m, r.time_s,
             r.record_date.isoformat(), r.source_type]
            for r in records
        ),
    }, )
