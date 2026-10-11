"""FICTIONAL fixtures. Nothing here is a real competition, a real athlete, real research or reviewed coaching content."""
import random
from datetime import date, datetime, time, timedelta, timezone

DEMO_LABEL = "FICTIONAL competition: demo data, not a real event"

# key, name, category, equipment, demand_tags, body_areas, task_key, sets, reps, intensity, limitation
TEMPLATES = [
    ("deadlift_heavy", "Conventional deadlift, heavy sets", "strength", ["barbell"], ["deadlift", "loading"], ["lower_back", "hip", "grip"], "deadlift_barbell", 4, "3-5", "RPE 7-8", "Barbell deadlift only; not equivalent to axle or stone work."),
    ("deadlift_timed_sets", "Timed deadlift rep sets (event-style)", "event_practice", ["barbell"], ["deadlift"], ["lower_back", "hip", "grip"], "deadlift_barbell", 3, "6-10 in the event time window", "RPE 7", "Match the event's bar, load and time rules before treating results as comparable."),
    ("romanian_deadlift", "Romanian deadlift", "accessory", ["barbell"], ["deadlift", "loading"], ["lower_back", "hip"], None, 3, "8", "RPE 6-7", "General posterior-chain work."),
    ("strict_press", "Strict overhead press", "strength", ["barbell", "rack_bench"], ["press"], ["shoulder", "elbow"], "press_barbell_strict", 4, "4-6", "RPE 7", "Barbell press does not demonstrate log or axle clean-and-press readiness."),
    ("push_press", "Barbell push press", "strength", ["barbell", "rack_bench"], ["press"], ["shoulder", "lower_back"], None, 4, "3-5", "RPE 7", "General overhead power; different from log technique."),
    ("db_press", "Dumbbell overhead press", "strength", ["dumbbell"], ["press"], ["shoulder", "elbow"], None, 3, "8-10", "RPE 7", "General pressing work."),
    ("log_clean_press_practice", "Log clean and press practice", "event_practice", ["log"], ["press"], ["shoulder", "lower_back"], "log_clean_press", 4, "2-3", "RPE 6-7", "Needs log access; technique review recommended."),
    ("axle_clean_press_practice", "Axle clean and press practice", "event_practice", ["axle"], ["press"], ["shoulder", "lower_back", "wrist"], "axle_clean_press", 4, "2-3", "RPE 6-7", "Needs an axle bar."),
    ("barbell_row", "Barbell row", "accessory", ["barbell"], ["deadlift", "press", "carry"], ["lower_back"], None, 3, "8", "RPE 7", "Upper-back support work."),
    ("back_squat", "Back squat", "strength", ["barbell", "rack_bench"], ["squat", "loading", "carry"], ["knee", "lower_back", "hip"], "squat_barbell", 4, "5", "RPE 7", "General leg strength; does not prove yoke or stone ability."),
    ("hip_thrust", "Barbell hip thrust", "accessory", ["barbell", "rack_bench"], ["loading", "deadlift"], ["hip"], None, 3, "8-10", "RPE 7", "General hip extension."),
    ("barbell_hang_clean", "Barbell hang clean", "strength", ["barbell"], ["loading", "press"], ["lower_back", "wrist"], None, 4, "3", "RPE 6-7", "General power for loading/pressing; not stone technique."),
    ("farmers_handles_practice", "Farmer's handles carry practice", "event_practice", ["farmers_handles"], ["carry"], ["grip"], "farmers_carry", 4, "20 m", "RPE 7", "Needs farmer's handles."),
    ("db_farmers_carry", "Heavy dumbbell carry", "strength", ["dumbbell"], ["carry"], ["grip"], None, 4, "20-30 m", "RPE 7", "Handle height, loading and grip differ from event handles; limited by dumbbell weight."),
    ("kb_suitcase_carry", "Kettlebell suitcase carry", "accessory", ["kettlebell"], ["carry"], ["grip"], None, 3, "20 m per side", "RPE 6", "Trunk and grip work only."),
    ("yoke_walk_practice", "Yoke walk practice", "event_practice", ["yoke"], ["carry"], ["knee", "lower_back"], "yoke_carry", 4, "15-20 m", "RPE 7", "Needs a yoke; no gym substitute proves yoke competence."),
    ("stone_load_practice", "Stone loading practice", "event_practice", ["stones"], ["loading"], ["lower_back", "hip", "grip"], "stone_load", 4, "3-5 loads", "RPE 7", "Needs stones and a platform."),
    ("sandbag_load_practice", "Sandbag loading practice", "event_practice", ["sandbag"], ["loading"], ["lower_back", "hip", "grip"], "sandbag_load", 4, "3-5 loads", "RPE 7", "Needs a sandbag; event height matters."),
    ("sled_drag", "Sled drag", "conditioning", ["sled"], ["carry", "conditioning"], ["knee"], None, 4, "20 m", "RPE 6-7", "General conditioning."),
    ("bodyweight_circuit", "Bodyweight conditioning circuit", "conditioning", [], ["conditioning", "carry", "loading"], [], None, 3, "5 min rounds", "RPE 6", "General conditioning only."),
    ("pullups", "Pull-ups", "accessory", [], ["press", "loading", "deadlift"], ["elbow", "shoulder"], None, 3, "6-10", "RPE 7", "General pulling strength."),
    ("trunk_bracing", "Trunk bracing (planks / dead bugs)", "accessory", [], ["carry", "loading", "deadlift", "squat"], [], None, 3, "30 s", "RPE 5-6", "General trunk work."),
]

# name, status, day offset, city, divisions
COMPETITIONS = [
    {"title": "Harbor Strongman Open", "organizer": "Harborview Strength Club (fictional)", "city": "Harborview", "country": "Nowhere", "days": 56, "time": time(9, 0), "tz": "Asia/Manila", "status": "upcoming", "fee": 40.0,
     "divisions": [
         {"name": "Novice Men -105 kg", "category": "men", "wmax": 105.0, "events": [
             ("Deadlift for reps (60 s)", "deadlift_barbell", "reps", 160, False, 60, None, "160 kg", "kg", "Max reps in 60 seconds, standard barbell, touch-and-go permitted."),
             ("Log clean and press", "log_clean_press", "reps", 70, False, 75, None, "70 kg", "kg", "Max reps in 75 seconds, log, clean to shoulders then press overhead."),
             ("Farmer's carry (20 m)", "farmers_carry", "time", 80, True, 45, 20, "80 kg per hand", "kg", "Load is PER HAND (160 kg total). 20 m course, fastest time, 45 s cap."),
             ("Sandbag loading", "sandbag_load", "reps", 100, False, 60, None, "100 kg", "kg", "Max sandbag loads over the bar in 60 s. Bar height 1.2 m."),
         ]},
         {"name": "Novice Women -75 kg", "category": "women", "wmax": 75.0, "events": [
             ("Deadlift for reps (60 s)", "deadlift_barbell", "reps", 100, False, 60, None, "100 kg", "kg", "Max reps in 60 seconds."),
             ("Log clean and press", "log_clean_press", "reps", 40, False, 75, None, "40 kg", "kg", "Max reps in 75 seconds."),
         ]},
     ]},
    {"title": "Ridge Iron Games", "organizer": "Ridge Iron Collective (fictional)", "city": "Ridgeton", "country": "Nowhere", "days": 120, "time": time(8, 30), "tz": "Asia/Manila", "status": "upcoming", "fee": 55.0,
     "divisions": [
         {"name": "Open Novice", "category": "open", "events": [
             ("Max deadlift", "deadlift_barbell", "max_load", None, False, None, None, None, "unknown", "Heaviest successful single, standard barbell. Weight ladder not yet published."),
             ("Axle clean and press", "axle_clean_press", "max_load", 80, False, None, None, "80 kg", "kg", "Max load, three attempts."),
             ("Yoke carry (15 m)", "yoke_carry", "time", 140, False, 40, 15, "140 kg", "kg", "Fastest 15 m with a turn at 7.5 m."),
             ("Stone loading", "stone_load", "reps", 90, False, 60, None, "90 kg", "kg", "Max stone loads in 60 s."),
         ]},
         {"name": "Intermediate Men -105 kg", "category": "men", "wmax": 105.0, "wmin": 80.0, "confirm": True, "notes": "Requires a qualifying result from a sanctioned event; confirm with the organizer.", "events": [
             ("Max deadlift", "deadlift_barbell", "max_load", 200, False, None, None, "200 kg", "kg", "Heaviest successful single."),
         ]},
     ]},
    {"title": "Quarry Challenge", "organizer": "Quarry Lifters (fictional)", "city": "Quarryfield", "country": "Nowhere", "days": 21, "time": time(10, 0), "tz": "Asia/Manila", "status": "upcoming", "fee": 25.0,
     "divisions": [
         {"name": "Novice Men -105 kg", "category": "men", "wmax": 105.0, "events": [
             ("Max deadlift", "deadlift_barbell", "max_load", 150, False, None, None, "150 kg", "kg", "Bar loaded to 150 kg; successful single scores."),
             ("Strict barbell press", "press_barbell_strict", "max_load", 70, False, None, None, "70 kg", "kg", "Strict press, no leg drive."),
         ]},
     ]},
    {"title": "Lakeside Open", "organizer": "Lakeside Gym (fictional)", "city": "Lakeside", "country": "Nowhere", "days": 30, "status": "canceled", "fee": None,
     "divisions": [{"name": "Open", "category": "open", "events": [("Max deadlift", "deadlift_barbell", "max_load", 160, False, None, None, "160 kg", "kg", "Cancelled by organizer.")]}]},
    {"title": "Old Quarter Throwdown", "organizer": "Old Quarter Strongman (fictional)", "city": "Old Quarter", "country": "Nowhere", "days": -40, "status": "completed", "fee": 30.0,
     "divisions": [{"name": "Novice Men", "category": "men", "events": [("Max deadlift", "deadlift_barbell", "max_load", 140, False, None, None, "140 kg", "kg", "Completed event.")]}]},
]

# (competition division, task, scoring, load, per_hand, T, D, category) -> synthetic cohort sizes
COHORTS = [
    # Harbor men deadlift reps: 24 unique athletes (+ duplicates to exercise de-duplication)
    {"task": "deadlift_barbell", "scoring": "reps", "cat": "men", "load": 160.0, "T": 60.0, "D": None, "per_hand": False, "n": 24, "dups": 3, "lo": 4, "hi": 14},
    # Ridge: small cohort -> percentile suppressed
    {"task": "deadlift_barbell", "scoring": "max_load", "cat": "men", "load": 200.0, "T": None, "D": None, "per_hand": False, "n": 8, "dups": 0, "lo": 190, "hi": 260},
    # Quarry deadlift max load 150 kg men: 22 athletes -> percentile shown if athlete has a comparable record
    {"task": "deadlift_barbell", "scoring": "max_load", "cat": "men", "load": 150.0, "T": None, "D": None, "per_hand": False, "n": 22, "dups": 2, "lo": 120, "hi": 230},
    # Strict press 70 kg, only 12
    {"task": "press_barbell_strict", "scoring": "max_load", "cat": "men", "load": 70.0, "T": None, "D": None, "per_hand": False, "n": 12, "dups": 0, "lo": 55, "hi": 95},
]


def seed_templates(db):
    from app.models import ExerciseTemplate
    existing = {t.key for t in db.query(ExerciseTemplate).all()}
    for key, name, cat, eq, tags, areas, task, sets, reps, inten, lim in TEMPLATES:
        if key in existing:
            continue
        db.add(ExerciseTemplate(key=key, name=name, category=cat, equipment=eq, demand_tags=tags, body_areas=areas,
                                task_key=task, sets=sets, reps=reps, intensity=inten, limitation=lim,
                                review_status="unreviewed_demo", template_version="demo-0.1"))
    db.commit()


def _backfill_times(db):
    """Fixtures seeded before venue times existed: fill start_time/timezone where still unset (never overwrites)."""
    from app.models import Competition
    for c in COMPETITIONS:
        if not c.get("time"):
            continue
        row = db.query(Competition).filter(Competition.owner_id.is_(None), Competition.title == f"{c['title']} (fictional)").first()
        if row and row.start_time is None and row.timezone is None:
            row.start_time, row.timezone = c["time"], c["tz"]
    db.commit()


def seed_competitions(db, today: date | None = None):
    from app.models import (Competition, CompetitionDivision, EventSpecification, HistoricalResult, SourceEvidence)
    today = today or date.today()
    if db.query(Competition).filter(Competition.owner_id.is_(None)).count():
        _backfill_times(db)
        return False
    now = datetime.now(timezone.utc)
    for c in COMPETITIONS:
        comp = Competition(
            owner_id=None, title=f"{c['title']} (fictional)", organizer=c["organizer"], venue="Fictional Arena", city=c["city"],
            country=c["country"], start_date=today + timedelta(days=c["days"]), start_time=c.get("time"), timezone=c.get("tz"),
            registration_deadline=today + timedelta(days=c["days"] - 14) if c["status"] == "upcoming" else None,
            source_url="fixture://" + c["title"].lower().replace(" ", "-"), registration_url=None,
            entry_fee=c["fee"], fee_currency="USD" if c["fee"] else None, last_checked_at=now, last_confirmed_at=None,
            status=c["status"], verification_status="fixture", is_demo=True, demo_label=DEMO_LABEL,
        )
        db.add(comp)
        db.flush()
        db.add(SourceEvidence(entity_type="competition", entity_id=comp.id, field_name="start_date", url=comp.source_url,
                              retrieved_at=now, excerpt="Fictional fixture text, not from any real source.", review_status="fixture"))
        for d in c["divisions"]:
            div = CompetitionDivision(competition_id=comp.id, name=d["name"], category=d["category"],
                                      weight_min_kg=d.get("wmin"), weight_max_kg=d.get("wmax"),
                                      eligibility_notes=d.get("notes"), needs_manual_confirmation=d.get("confirm", False))
            db.add(div)
            db.flush()
            for i, e in enumerate(d["events"]):
                name, task, scoring, load, per_hand, T, D, text, unit, rules = e
                ev = EventSpecification(division_id=div.id, position=i, name=name, task_key=task, scoring_type=scoring,
                                        load_kg=float(load) if load else None, load_per_hand=per_hand,
                                        original_load_text=text, original_unit=unit, time_limit_s=float(T) if T else None,
                                        distance_m=float(D) if D else None, rules_text=rules, verification_status="fixture")
                db.add(ev)
                db.flush()
                db.add(SourceEvidence(entity_type="event", entity_id=ev.id, field_name="load_kg", url=comp.source_url,
                                      retrieved_at=now, excerpt=f"Fictional rule text: {text or 'load not yet published'}. {rules}",
                                      review_status="fixture"))
    rng = random.Random(20261011)
    for c in COHORTS:
        base_date = today - timedelta(days=200)
        rows = []
        for i in range(c["n"]):
            v = rng.randint(int(c["lo"]), int(c["hi"]))
            rows.append((f"synthetic-{c['task']}-{i:02d}", v, base_date + timedelta(days=rng.randint(0, 150))))
        for j in range(c["dups"]):
            rows.append(rows[j])  # exact duplicate rows
        for key, v, d in rows:
            db.add(HistoricalResult(task_key=c["task"], scoring_type=c["scoring"], division_category=c["cat"], load_kg=c["load"],
                                    load_per_hand=c["per_hand"], time_limit_s=c["T"], distance_m=c["D"], athlete_key=key,
                                    competition_name="Synthetic Regional Series (fictional)", result_date=d, result_value=float(v),
                                    provenance="SYNTHETIC benchmark data generated for the demo", is_synthetic=True))
    db.commit()
    return True


def seed_demo_athlete(db, owner_id: str, today: date | None = None):
    from app.models import AthleteProfile, EquipmentAccess, PerformanceRecord
    today = today or date.today()
    if db.query(AthleteProfile).filter_by(owner_id=owner_id).first():
        return False
    db.add(AthleteProfile(owner_id=owner_id, display_name="Demo Athlete (fictional)", body_weight_kg=98.0, age=29,
                          division_category="men", experience_level="novice", competitions_entered=1, city="Harborview",
                          travel_radius_km=60, days_per_week=4, session_minutes=75, goal="participate",
                          avoid_exercises=[], pain_flags=[]))
    for impl, acc, mx, note in [("barbell", "regular", 220, "Commercial gym"), ("dumbbell", "regular", 50, "Up to 50 kg each"),
                                ("rack_bench", "regular", None, None), ("kettlebell", "regular", 32, None),
                                ("log", "occasional", 80, "Specialist gym about once a month"),
                                ("farmers_handles", "none", None, None), ("sandbag", "none", None, None)]:
        db.add(EquipmentAccess(owner_id=owner_id, implement=impl, access=acc, max_load_kg=mx, notes=note,
                               limit_is_per_hand=impl in ("dumbbell", "kettlebell")))
    db.add(PerformanceRecord(owner_id=owner_id, task_key="deadlift_barbell", load_kg=180, reps=1, record_date=today - timedelta(days=20), effort_rpe=9, source_type="self_reported", conditions="Conventional, standard barbell"))
    db.add(PerformanceRecord(owner_id=owner_id, task_key="press_barbell_strict", load_kg=65, reps=1, record_date=today - timedelta(days=14), effort_rpe=9, source_type="verified_training"))
    db.add(PerformanceRecord(owner_id=owner_id, task_key="squat_barbell", load_kg=150, reps=5, record_date=today - timedelta(days=10), effort_rpe=8, source_type="self_reported"))
    db.commit()
    return True
