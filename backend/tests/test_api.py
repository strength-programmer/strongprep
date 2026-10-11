import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.integrations.ai import ClaudePlanProvider, MockPlanProvider, ProviderUnavailable
from app.main import check_startup
from app.models import ExerciseTemplate
from app.services import planning
from tests.conftest import auth, make_client


def harbor(client):
    comps = client.get("/competitions").json()
    c = next(c for c in comps if c["title"].startswith("Harbor"))
    full = client.get(f"/competitions/{c['id']}").json()
    div = next(d for d in full["divisions"] if d["name"].startswith("Novice Men"))
    return full, div


def run_journey(client):
    full, div = harbor(client)
    assert client.put("/athlete-profile/target", json={"competition_id": full["id"], "division_id": div["id"]}).status_code == 200
    a = client.post("/assessments", json={"competition_id": full["id"], "division_id": div["id"]})
    assert a.status_code == 201, a.text
    p = client.post("/preparation-plans", json={"assessment_id": a.json()["id"]})
    assert p.status_code == 201, p.text
    return full, div, a.json(), p.json()


# ------------------------------------------------------------------ journey + persistence
def test_full_journey_and_persistence_across_restart(demo_athlete):
    client, Session, path, settings = demo_athlete
    full, div, a, plan = run_journey(client)

    ev = {e["event_name"]: e for e in a["result"]["events"]}
    assert ev["Deadlift for reps (60 s)"]["status"] == "unknown"
    assert ev["Log clean and press"]["status"] == "implement_practice_gap"
    assert ev["Farmer's carry (20 m)"]["status"] == "implement_practice_gap"
    assert ev["Sandbag loading"]["status"] == "implement_practice_gap"
    assert a["result"]["eligibility"]["status"] == "eligible"
    assert "readiness" not in json.dumps(a["result"]["summary_counts"]).lower()

    assert client.post(f"/preparation-plans/{plan['id']}/save").json()["review_state"] == "saved"
    log = client.post("/training-logs", json={
        "plan_id": plan["id"], "planned_session": "w1s1", "session_date": date.today().isoformat(), "effort_rpe": 8,
        "exercises": [{"name": "Deadlift", "sets": 4, "reps": 5, "load_kg": 140}], "notes": "felt ok",
        "new_performance": [{"task_key": "deadlift_barbell", "load_kg": 160, "reps": 9, "time_s": 60,
                             "record_date": date.today().isoformat(), "source_type": "self_reported"}]})
    assert log.status_code == 201, log.text

    # "restart": brand-new app/engine on the same SQLite file
    client2, _, engine2 = make_client(path, settings)
    assert client2.get("/athlete-profile").json()["profile"]["body_weight_kg"] == 98.0
    assert client2.get(f"/preparation-plans/{plan['id']}").json()["review_state"] == "saved"
    assert len(client2.get("/training-logs").json()) == 1
    assert len(client2.get("/performance-records").json()) == 4  # 3 seeded + 1 from the log
    # the new timed record updates the report: reps event is now demonstrated
    a2 = client2.post("/assessments", json={"competition_id": full["id"], "division_id": div["id"]}).json()
    ev2 = {e["event_name"]: e for e in a2["result"]["events"]}
    assert ev2["Deadlift for reps (60 s)"]["status"] == "demonstrated"
    assert ev2["Deadlift for reps (60 s)"]["benchmark"]["status"] == "percentile"  # 24 unique synthetic athletes
    engine2.dispose()


def test_dashboard_and_completeness(demo_athlete):
    client, *_ = demo_athlete
    d0 = client.get("/dashboard").json()
    assert d0["target"] is None and "target_competition" in d0["completeness"]["missing"]
    run_journey(client)
    d1 = client.get("/dashboard").json()
    assert d1["completeness"]["percent"] == 100
    assert d1["target"]["is_demo"] is True and d1["assessment"]["top_priorities"] and d1["plan"]["review_state"] == "draft"


def test_empty_profile_states(demo):
    client, *_ = demo
    r = client.get("/athlete-profile").json()
    assert r["profile"] is None and r["completeness"]["percent"] == 0
    full, div = harbor(client)
    a = client.post("/assessments", json={"competition_id": full["id"], "division_id": div["id"]}).json()
    assert a["result"]["eligibility"]["status"] == "needs_confirmation"
    assert all(e["status"] in ("unknown", "implement_practice_gap") for e in a["result"]["events"])
    r = client.post("/preparation-plans", json={"assessment_id": a["id"]})
    assert r.status_code == 422 and "availability" in r.json()["detail"]["message"].lower()


# ------------------------------------------------------------------ validation
def test_input_validation(demo):
    client, *_ = demo
    assert client.put("/athlete-profile", json={"body_weight_kg": -5}).status_code == 422
    assert client.put("/athlete-profile", json={"pain_flags": ["toe"]}).status_code == 422
    assert client.post("/performance-records", json={"task_key": "nope", "load_kg": 5, "record_date": "2026-01-01"}).status_code == 422
    assert client.post("/performance-records", json={"task_key": "deadlift_barbell", "record_date": "2026-01-01"}).status_code == 422
    future = (date.today() + timedelta(days=3)).isoformat()
    assert client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 100, "record_date": future}).status_code == 422
    assert client.put("/equipment", json=[{"implement": "barbell", "access": "regular"}, {"implement": "barbell", "access": "none"}]).status_code == 422


# ------------------------------------------------------------------ plan constraints
def test_plan_respects_equipment_schedule_and_access(demo_athlete):
    client, Session, *_ = demo_athlete
    *_, plan = run_journey(client)
    c = plan["content"]
    with Session() as db:
        T = {t.key: t for t in db.query(ExerciseTemplate)}
    regular = {"barbell", "dumbbell", "rack_bench", "kettlebell"}
    prof = client.get("/athlete-profile").json()["profile"]
    assert c["ai_label"].startswith("Mock AI") and "unreviewed" in c["template_notice"]
    for w in c["weeks"]:
        assert len(w["sessions"]) <= prof["days_per_week"]
        assert sum(1 for s in w["sessions"] if s["access_session"]) <= 1
        for s in w["sessions"]:
            assert s["estimated_minutes"] <= prof["session_minutes"]
            for x in s["exercises"]:
                need = set(T[x["template_key"]].equipment)
                assert need <= regular or (s["access_session"] and need <= regular | {"log"})
                assert x["template_key"] not in ("farmers_handles_practice", "sandbag_load_practice", "yoke_walk_practice")
    # occasional log access is scheduled deliberately, and unresolved needs are reported
    assert any(s["access_session"] for w in c["weeks"] for s in w["sessions"]) or len(c["weeks"]) < 2
    needs = {n["event_name"]: n for n in c["practice_needs"]}
    assert "Farmer's carry (20 m)" in needs and needs["Farmer's carry (20 m)"]["status"] == "unresolved"
    assert c["weeks"][-1]["phase"] == "taper"


def test_avoid_list_and_pain_flags_pause_templates(demo_athlete):
    client, *_ = demo_athlete
    body = {"body_weight_kg": 98, "age": 29, "division_category": "men", "experience_level": "novice", "days_per_week": 4,
            "session_minutes": 75, "avoid_exercises": ["back_squat"], "pain_flags": ["shoulder"], "goal": "participate"}
    assert client.put("/athlete-profile", json=body).status_code == 200
    *_, plan = run_journey(client)
    used = {x["template_key"] for w in plan["content"]["weeks"] for s in w["sessions"] for x in s["exercises"]}
    assert "back_squat" not in used and not ({"strict_press", "push_press", "db_press"} & used)
    reasons = {p["item"]: p["reason"] for p in plan["content"]["paused"]}
    assert "professional review" in reasons["Strict overhead press"]
    assert reasons["Back squat"] == "On your avoid list."


def test_validator_rejects_bad_plans(demo_athlete):
    client, Session, *_ = demo_athlete
    *_, plan = run_journey(client)
    with Session() as db:
        from app.models import Assessment, Competition, AthleteProfile, EquipmentAccess
        a = db.get(Assessment, plan["assessment_id"])
        ctx = planning.build_context(db.query(AthleteProfile).first(), db.query(EquipmentAccess).all(),
                                     db.query(ExerciseTemplate).all(), a.result, db.get(Competition, a.competition_id), date.today())
    good = MockPlanProvider().generate_plan(ctx)
    assert planning.validate_plan(good, ctx) == []

    import copy
    def broken(mut):
        p = copy.deepcopy(good); mut(p); return planning.validate_plan(p, ctx)

    assert any("not an allowed template" in e for e in broken(lambda p: p["weeks"][0]["sessions"][0]["exercises"].append(
        {"template_key": "yoke_walk_practice", "name": "Yoke", "sets": 3, "reps": "1", "intensity": "x"})))
    assert any("available days" in e for e in broken(lambda p: p["weeks"][0]["sessions"].extend(copy.deepcopy(p["weeks"][0]["sessions"]))))
    def overload(p):
        for x in p["weeks"][0]["sessions"][0]["exercises"]:
            x["sets"] = 10
    assert any("you have" in e for e in broken(overload))
    assert any("Missing explanation" in e for e in broken(lambda p: p.update(explanations=[])))
    assert any("Unsupported statement" in e for e in broken(lambda p: p["explanations"][0].update(text="This will guarantee a win")))
    assert any("exactly" in e for e in broken(lambda p: p["weeks"].pop()))
    assert any("not marked as an access session" in e for e in broken(lambda p: p["weeks"][0]["sessions"][0]["exercises"].append(
        {"template_key": "log_clean_press_practice", "name": "Log", "sets": 1, "reps": "1", "intensity": "x"})))


def test_session_too_short_is_rejected_not_fabricated(demo_athlete):
    client, Session, *_ = demo_athlete
    *_, plan = run_journey(client)
    with Session() as db:
        from app.models import Assessment, Competition, AthleteProfile, EquipmentAccess
        a = db.get(Assessment, plan["assessment_id"])
        ctx = planning.build_context(db.query(AthleteProfile).first(), db.query(EquipmentAccess).all(),
                                     db.query(ExerciseTemplate).all(), a.result, db.get(Competition, a.competition_id), date.today())
    ctx["session_minutes"] = 10  # cannot fit warm-up + one 3-set exercise
    with pytest.raises(planning.PlanError) as ei:
        planning.generate_validated_plan(ctx, Settings(ai_provider="mock"))
    assert ei.value.status == 422 and "too short" in str(ei.value)


# ------------------------------------------------------------------ versioning / stale
def manual_comp(client, load=100):
    body = {"title": "My Local Show", "start_date": (date.today() + timedelta(days=40)).isoformat(), "city": "Home",
            "divisions": [{"name": "Open", "category": "open", "events": [
                {"name": "Deadlift", "task_key": "deadlift_barbell", "scoring_type": "max_load", "load_kg": load,
                 "original_load_text": f"{load} kg", "original_unit": "kg"}]}]}
    r = client.post("/competitions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_changed_requirements_mark_reports_and_plans_stale(demo_athlete):
    client, *_ = demo_athlete
    comp = manual_comp(client, 100)
    div = comp["divisions"][0]
    a = client.post("/assessments", json={"competition_id": comp["id"], "division_id": div["id"]}).json()
    plan = client.post("/preparation-plans", json={"assessment_id": a["id"]}).json()
    assert a["stale"] is False and plan["stale"] is False
    ev = div["events"][0]
    upd = {k: ev[k] for k in ("name", "task_key", "scoring_type", "load_per_hand", "original_unit", "time_limit_s", "distance_m", "rules_text", "original_load_text")}
    r = client.put(f"/events/{ev['id']}", json={**upd, "load_kg": 190.0})
    assert r.status_code == 200 and r.json()["version"] == 2
    a_after = client.get(f"/assessments/{a['id']}").json()
    assert a_after["stale"] is True and a_after["result"]["events"][0]["requirement"]["load_kg"] == 100  # old report preserved
    assert client.get(f"/preparation-plans/{plan['id']}").json()["stale"] is True
    assert client.post("/preparation-plans", json={"assessment_id": a["id"]}).status_code == 409
    assert client.post(f"/preparation-plans/{plan['id']}/save").status_code == 409
    fresh = client.post("/assessments", json={"competition_id": comp["id"], "division_id": div["id"]}).json()
    ev0 = fresh["result"]["events"][0]
    assert fresh["stale"] is False and ev0["status"] == "measured_gap" and ev0["load_ratio"] == 0.947  # 180 / 190


def test_shared_catalog_is_read_only(demo):
    client, *_ = demo
    full, div = harbor(client)
    ev = div["events"][0]
    body = {k: ev[k] for k in ("name", "task_key", "scoring_type", "load_kg", "load_per_hand", "original_unit", "time_limit_s", "distance_m", "rules_text", "original_load_text")}
    assert client.put(f"/events/{ev['id']}", json=body).status_code == 403


# ------------------------------------------------------------------ AI providers
def test_claude_selected_without_key_is_unavailable_not_fake(demo_athlete):
    client, Session, path, s = demo_athlete
    s2 = Settings(app_mode="demo", database_url="sqlite:///x.db", ai_provider="claude")
    client.app.dependency_overrides.__setitem__(__import__("app.config", fromlist=["get_settings"]).get_settings, lambda: s2)
    st = client.get("/status").json()
    assert st["ai"]["available"] is False and "ANTHROPIC_API_KEY" in st["ai"]["detail"]
    full, div = harbor(client)
    a = client.post("/assessments", json={"competition_id": full["id"], "division_id": div["id"]}).json()
    r = client.post("/preparation-plans", json={"assessment_id": a["id"]})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]["message"]
    with pytest.raises(ProviderUnavailable):
        ClaudePlanProvider(Settings(ai_provider="claude", anthropic_api_key="k", claude_model=""))


class _FakeStream:
    def __init__(self, text): self.text = text
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        from types import SimpleNamespace as NS
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.text)])


class _FakeClient:
    def __init__(self, text): self.messages = type("M", (), {"stream": lambda _s, **kw: _FakeStream(text)})()


def test_claude_adapter_output_is_still_hard_validated(demo_athlete):
    client, Session, *_ = demo_athlete
    *_, plan = run_journey(client)
    with Session() as db:
        from app.models import Assessment, Competition, AthleteProfile, EquipmentAccess
        a = db.get(Assessment, plan["assessment_id"])
        ctx = planning.build_context(db.query(AthleteProfile).first(), db.query(EquipmentAccess).all(),
                                     db.query(ExerciseTemplate).all(), a.result, db.get(Competition, a.competition_id), date.today())
    s = Settings(ai_provider="claude", anthropic_api_key="k", claude_model="some-model")
    good = MockPlanProvider().generate_plan(ctx)
    p, name = planning.generate_validated_plan(ctx, s, provider=ClaudePlanProvider(s, client=_FakeClient("Here:\n" + json.dumps(good))))
    assert name == "claude" and "Claude" in p["ai_label"]
    bad = dict(good, weeks=good["weeks"][:-1])
    with pytest.raises(planning.PlanError) as ei:
        planning.generate_validated_plan(ctx, s, provider=ClaudePlanProvider(s, client=_FakeClient(json.dumps(bad))))
    assert ei.value.status == 422
    with pytest.raises(planning.PlanError) as ei:
        planning.generate_validated_plan(ctx, s, provider=ClaudePlanProvider(s, client=_FakeClient("no json here")))
    assert ei.value.status == 502


# ------------------------------------------------------------------ demo/live boundaries
def test_demo_rejects_non_local_clients_and_non_sqlite(tmp_path):
    s = Settings(app_mode="demo", database_url="sqlite:///x.db")
    client, *_ = make_client(tmp_path / "d.db", s, client_addr=("203.0.113.9", 4000))
    assert client.get("/athlete-profile").status_code == 403
    with pytest.raises(RuntimeError):
        check_startup(Settings(app_mode="demo", database_url="postgresql+psycopg://u:p@h/db"))
    with pytest.raises(RuntimeError):
        check_startup(Settings(app_mode="live", database_url="sqlite:///x.db", supabase_url=""))
    check_startup(s)


def test_live_requires_valid_token_and_never_falls_back_to_demo(live):
    client, Session, s = live
    for headers in ({}, {"Authorization": "Bearer garbage"}, {"Authorization": "Basic abc"},
                    auth(exp_delta=-10), auth(aud="other"), auth(iss="https://evil.example/auth/v1"), auth(secret="x" * 40)):
        r = client.get("/athlete-profile", headers=headers)
        assert r.status_code == 401, headers
        assert client.put("/athlete-profile", json={"age": 30}, headers=headers).status_code == 401
        assert client.post("/assessments", json={"competition_id": 1, "division_id": 1}, headers=headers).status_code == 401
    # invalid token on a public route is an error, not a silent anonymous/demo identity
    assert client.get("/competitions", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/competitions").status_code == 200  # anonymous public catalog read


def test_live_private_data_is_isolated_between_accounts(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    client.put("/athlete-profile", json={"body_weight_kg": 90, "age": 30, "division_category": "men", "days_per_week": 4, "session_minutes": 75}, headers=A)
    client.put("/equipment", json=[{"implement": "barbell", "access": "regular"}], headers=A)
    rec = client.post("/performance-records", json={"task_key": "deadlift_barbell", "load_kg": 150, "record_date": "2026-09-01"}, headers=A).json()
    comps = client.get("/competitions", headers=A).json()
    c = next(c for c in comps if c["title"].startswith("Harbor"))
    div = c["divisions"][0]
    a = client.post("/assessments", json={"competition_id": c["id"], "division_id": div["id"]}, headers=A).json()
    plan = client.post("/preparation-plans", json={"assessment_id": a["id"]}, headers=A)
    assert plan.status_code == 201, plan.text
    pid = plan.json()["id"]
    log = client.post("/training-logs", json={"session_date": "2026-10-01", "exercises": []}, headers=A).json()

    assert client.get("/athlete-profile", headers=B).json()["profile"] is None
    assert client.get("/performance-records", headers=B).json() == []
    assert client.get("/equipment", headers=B).json() == []
    assert client.get(f"/assessments/{a['id']}", headers=B).status_code == 404
    assert client.get(f"/preparation-plans/{pid}", headers=B).status_code == 404
    assert client.post(f"/preparation-plans/{pid}/save", headers=B).status_code == 404
    assert client.post("/preparation-plans", json={"assessment_id": a["id"]}, headers=B).status_code == 404
    assert client.put(f"/performance-records/{rec['id']}", json={"task_key": "deadlift_barbell", "load_kg": 1, "record_date": "2026-09-01"}, headers=B).status_code == 404
    assert client.delete(f"/performance-records/{rec['id']}", headers=B).status_code == 404
    assert client.delete(f"/training-logs/{log['id']}", headers=B).status_code == 404
    assert client.get("/training-logs", headers=B).json() == []
    assert client.get("/assessments", headers=B).json() == []
    assert client.post("/training-logs", json={"session_date": "2026-10-01", "plan_id": pid}, headers=B).status_code == 404
    # client-supplied owner is rejected by schema, never trusted
    assert client.put("/athlete-profile", json={"owner_id": "user-a", "age": 30}, headers=B).status_code == 422
    # private manual competitions are invisible to other accounts
    mine = manual_comp_auth(client, A)
    assert client.get(f"/competitions/{mine['id']}", headers=B).status_code == 404
    assert all(x["id"] != mine["id"] for x in client.get("/competitions", headers=B).json())
    assert client.get(f"/competitions/{mine['id']}", headers=A).status_code == 200
    # export/delete only touch the caller's data
    assert client.get("/export", headers=B).json()["performance_records"] == []
    assert client.delete("/my-data", headers=B).status_code == 204
    assert len(client.get("/performance-records", headers=A).json()) == 1
    assert client.delete("/my-data", headers=A).status_code == 204
    assert client.get("/performance-records", headers=A).json() == []


def manual_comp_auth(client, headers):
    body = {"title": "Private Show", "start_date": (date.today() + timedelta(days=30)).isoformat(),
            "divisions": [{"name": "Open", "category": "open", "events": []}]}
    r = client.post("/competitions", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_export_and_delete_in_demo(demo_athlete):
    client, *_ = demo_athlete
    run_journey(client)
    ex = client.get("/export").json()
    assert ex["profile"] and ex["assessments"] and ex["plans"] and len(ex["performance_records"]) == 3
    assert client.delete("/my-data").status_code == 204
    assert client.get("/athlete-profile").json()["profile"] is None


def test_status_is_clear_about_demo(demo):
    client, *_ = demo
    st = client.get("/status").json()
    assert st["mode"] == "demo" and st["ai"]["provider"] == "mock" and "fictional" in st["demo_notice"].lower()
    assert st["integrations"]["tavily"]["live_adapter"] is False
