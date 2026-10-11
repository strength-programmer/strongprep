"""Evidence staleness: a report goes stale when the athlete data it was built from changes."""
from datetime import date

from app.models import Assessment
from tests.conftest import auth
from tests.test_api import harbor, run_journey

REASON = "Your records, equipment or profile changed"
TODAY = date.today().isoformat()


def report(client, aid):
    return client.get(f"/assessments/{aid}").json()


def new_report(client):
    full, div = harbor(client)
    return client.post("/assessments", json={"competition_id": full["id"], "division_id": div["id"]}).json()


def test_fresh_report_is_not_stale_and_a_new_record_makes_it_stale(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    assert a["stale"] is False
    r = client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 185, "reps": 1, "record_date": TODAY})
    assert r.status_code == 201
    after = report(client, a["id"])
    assert after["stale"] is True and any(REASON in x for x in after["stale_reasons"])
    # the old report is preserved unchanged, and a fresh one is current again
    assert after["result"] == a["result"]
    assert new_report(client)["stale"] is False


def test_editing_and_deleting_a_record_make_reports_stale(demo_athlete):
    client, *_ = demo_athlete
    a = new_report(client)
    rec = client.get("/performance-records").json()[0]
    body = {"task_key": rec["task_key"], "load_kg": rec["load_kg"] + 5, "reps": rec["reps"], "record_date": rec["record_date"],
            "source_type": rec["source_type"]}
    assert client.put(f"/performance-records/{rec['id']}", json=body).status_code == 200
    assert report(client, a["id"])["stale"] is True
    b = new_report(client)
    assert b["stale"] is False
    assert client.delete(f"/performance-records/{rec['id']}").status_code == 204
    assert report(client, b["id"])["stale"] is True


def test_saving_unchanged_equipment_is_not_a_change_but_real_changes_are(demo_athlete):
    client, *_ = demo_athlete
    a = new_report(client)
    same = [{k: e[k] for k in ("implement", "access", "max_load_kg", "carry_space_m", "notes")} for e in client.get("/equipment").json()]
    assert client.put("/equipment", json=same).status_code == 200  # rows are replaced, content identical
    assert report(client, a["id"])["stale"] is False
    changed = [dict(e, max_load_kg=(e["max_load_kg"] or 0) + 10) if e["implement"] == "barbell" else e for e in same]
    client.put("/equipment", json=changed)
    assert report(client, a["id"])["stale"] is True
    b = new_report(client)
    client.put("/equipment", json=[e for e in changed if e["implement"] != "log"])
    assert report(client, b["id"])["stale"] is True


def test_eligibility_fields_matter_but_cosmetic_profile_fields_do_not(demo_athlete):
    client, *_ = demo_athlete
    base = {k: v for k, v in client.get("/athlete-profile").json()["profile"].items()
            if k in ("body_weight_kg", "age", "division_category", "experience_level", "competitions_entered", "city", "travel_radius_km",
                     "days_per_week", "session_minutes", "other_commitments", "avoid_exercises", "pain_flags", "goal", "display_name")}
    a = new_report(client)
    for cosmetic in ({"display_name": "Someone else"}, {"city": "Elsewhere"}, {"other_commitments": "night shifts"},
                     {"goal": "perform"}, {"travel_radius_km": 5}, {"experience_level": "intermediate"}):
        assert client.put("/athlete-profile", json={**base, **cosmetic}).status_code == 200
        assert report(client, a["id"])["stale"] is False, cosmetic
    for field, value in (("body_weight_kg", 104.0), ("age", 40), ("division_category", "women")):
        b = new_report(client)
        assert client.put("/athlete-profile", json={**base, field: value}).status_code == 200
        assert report(client, b["id"])["stale"] is True, field
        client.put("/athlete-profile", json=base)


def test_reports_made_before_fingerprints_are_unknown_not_stale(demo_athlete):
    client, Session, *_ = demo_athlete
    a = new_report(client)
    with Session() as db:
        db.get(Assessment, a["id"]).evidence_hash = None
        db.commit()
    client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 190, "reps": 1, "record_date": TODAY})
    out = report(client, a["id"])
    assert out["stale"] is False and out["stale_reasons"] == []


def test_stale_plan_cannot_be_saved_or_regenerated_until_reassessed(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    client.post("/performance-records", json={"task_key": "squat_barbell", "load_kg": 160, "reps": 5, "record_date": TODAY})
    p = client.get(f"/preparation-plans/{plan['id']}").json()
    assert p["stale"] is True and any(REASON in x for x in p["stale_reasons"])
    assert client.post(f"/preparation-plans/{plan['id']}/save").status_code == 409
    assert client.post("/preparation-plans", json={"assessment_id": a["id"]}).status_code == 409
    fresh = new_report(client)
    assert client.post("/preparation-plans", json={"assessment_id": fresh["id"]}).status_code == 201


def test_lists_and_dashboard_report_the_stale_state(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 186, "reps": 1, "record_date": TODAY})
    assert client.get("/assessments").json()[0]["stale"] is True
    assert client.get("/preparation-plans").json()[0]["stale"] is True
    d = client.get("/dashboard").json()
    assert d["assessment"]["stale"] is True and d["plan"]["stale"] is True
    assert any(REASON in x for x in d["assessment"]["stale_reasons"])


def test_another_accounts_changes_never_affect_my_reports(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    prof = {"body_weight_kg": 95, "age": 30, "division_category": "men", "days_per_week": 4, "session_minutes": 75}
    for h in (A, B):
        client.put("/athlete-profile", json=prof, headers=h)
    comp = next(c for c in client.get("/competitions", headers=A).json() if c["title"].startswith("Harbor"))
    a = client.post("/assessments", json={"competition_id": comp["id"], "division_id": comp["divisions"][0]["id"]}, headers=A).json()
    client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 200, "reps": 1, "record_date": TODAY}, headers=B)
    client.put("/equipment", json=[{"implement": "barbell", "access": "regular"}], headers=B)
    client.put("/athlete-profile", json={**prof, "body_weight_kg": 120}, headers=B)
    assert client.get(f"/assessments/{a['id']}", headers=A).json()["stale"] is False
    client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 150, "reps": 1, "record_date": TODAY}, headers=A)
    assert client.get(f"/assessments/{a['id']}", headers=A).json()["stale"] is True


# ---------------------------------------------------------------- plan inputs (step A3)
PLAN_REASON = "Your availability, exercise restrictions or equipment changed"


def profile_body(client, **over):
    p = client.get("/athlete-profile").json()["profile"]
    keys = ("body_weight_kg", "age", "division_category", "experience_level", "competitions_entered", "city", "travel_radius_km",
            "days_per_week", "session_minutes", "other_commitments", "avoid_exercises", "pain_flags", "goal", "display_name")
    return {**{k: p[k] for k in keys}, **over}


def test_availability_change_stales_the_plan_but_not_the_report(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    assert plan["stale"] is False
    for over in ({"days_per_week": 3}, {"session_minutes": 60}):
        client.put("/athlete-profile", json=profile_body(client, **over))
        p = client.get(f"/preparation-plans/{plan['id']}").json()
        assert p["stale"] is True and any(PLAN_REASON in x for x in p["stale_reasons"]), over
        assert report(client, a["id"])["stale"] is False, "availability does not affect the report"
        client.put("/athlete-profile", json=profile_body(client, days_per_week=4, session_minutes=75))
        assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is False  # changing back restores it


def test_restrictions_stale_the_plan_and_block_saving(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    client.put("/athlete-profile", json=profile_body(client, pain_flags=["shoulder"]))
    assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is True
    r = client.post(f"/preparation-plans/{plan['id']}/save")
    assert r.status_code == 409 and "Generate a new plan" in r.json()["detail"]["message"]
    assert any(PLAN_REASON in x for x in r.json()["detail"]["errors"])
    # the same (still fresh) report can produce a new plan that respects the new restriction
    new = client.post("/preparation-plans", json={"assessment_id": a["id"]})
    assert new.status_code == 201 and new.json()["stale"] is False
    used = {x["template_key"] for w in new.json()["content"]["weeks"] for s in w["sessions"] for x in s["exercises"]}
    assert not ({"strict_press", "push_press", "db_press", "log_clean_press_practice"} & used)
    assert client.post(f"/preparation-plans/{new.json()['id']}/save").status_code == 200
    # avoid list works the same way
    client.put("/athlete-profile", json=profile_body(client, pain_flags=["shoulder"], avoid_exercises=["back_squat"]))
    assert client.get(f"/preparation-plans/{new.json()['id']}").json()["stale"] is True


def test_cosmetic_profile_changes_do_not_stale_a_plan(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    for over in ({"display_name": "X"}, {"city": "Elsewhere"}, {"goal": "perform"}, {"other_commitments": "nights"}):
        client.put("/athlete-profile", json=profile_body(client, **over))
        assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is False, over


def test_equipment_access_change_stales_the_plan(demo_athlete):
    client, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    eq = [{k: e[k] for k in ("implement", "access", "max_load_kg", "carry_space_m", "notes")} for e in client.get("/equipment").json()]
    client.put("/equipment", json=eq)  # unchanged content
    assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is False
    client.put("/equipment", json=[dict(e, access="none") if e["implement"] == "log" else e for e in eq])
    p = client.get(f"/preparation-plans/{plan['id']}").json()
    assert p["stale"] is True and any(PLAN_REASON in x for x in p["stale_reasons"])


def test_plans_made_before_input_fingerprints_are_unknown_not_stale(demo_athlete):
    client, Session, *_ = demo_athlete
    full, div, a, plan = run_journey(client)
    from app.models import PreparationPlan
    with Session() as db:
        db.get(PreparationPlan, plan["id"]).inputs_hash = None
        db.commit()
    client.put("/athlete-profile", json=profile_body(client, days_per_week=2))
    assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is False


def test_plan_list_and_dashboard_show_input_staleness(demo_athlete):
    client, *_ = demo_athlete
    run_journey(client)
    client.put("/athlete-profile", json=profile_body(client, pain_flags=["knee"]))
    assert client.get("/preparation-plans").json()[0]["stale"] is True
    d = client.get("/dashboard").json()
    assert d["plan"]["stale"] is True and d["assessment"]["stale"] is False


def test_other_accounts_cannot_stale_my_plan(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    prof = {"body_weight_kg": 95, "age": 30, "division_category": "men", "days_per_week": 4, "session_minutes": 75}
    for h in (A, B):
        client.put("/athlete-profile", json=prof, headers=h)
        client.put("/equipment", json=[{"implement": "barbell", "access": "regular"}], headers=h)
    comp = next(c for c in client.get("/competitions", headers=A).json() if c["title"].startswith("Harbor"))
    a = client.post("/assessments", json={"competition_id": comp["id"], "division_id": comp["divisions"][0]["id"]}, headers=A).json()
    plan = client.post("/preparation-plans", json={"assessment_id": a["id"]}, headers=A).json()
    client.put("/athlete-profile", json={**prof, "days_per_week": 2, "pain_flags": ["knee"]}, headers=B)
    client.put("/equipment", json=[], headers=B)
    assert client.get(f"/preparation-plans/{plan['id']}", headers=A).json()["stale"] is False
