from datetime import date, timedelta

import pytest

from app.data.fixtures import seed_competitions
from app.models import Competition, SourceEvidence
from tests.conftest import auth

FUTURE = (date.today() + timedelta(days=40)).isoformat()


def make(client, headers=None, **over):
    body = {"title": "Source Test Show", "start_date": FUTURE, "source_url": "https://example.org/rules",
            "divisions": [{"name": "Open Men", "category": "men", "weight_max_kg": 105, "eligibility_notes": "Must be a club member",
                           "events": [
                               {"name": "Carry", "task_key": "farmers_carry", "scoring_type": "time", "load_kg": 80, "load_per_hand": True,
                                "original_load_text": "80 kg per hand", "original_unit": "kg", "time_limit_s": 45, "distance_m": 20,
                                "rules_text": "80 kg each hand, 20 m course, 45 s cap"},
                               {"name": "Deadlift", "task_key": "deadlift_barbell", "scoring_type": "max_load", "load_kg": 200,
                                "original_load_text": "200 kg", "original_unit": "kg"}]}]}
    body.update(over)
    r = client.post("/competitions", json=body, headers=headers or {})
    assert r.status_code == 201, r.text
    return r.json()


def all_evidence(c):
    out = list(c["evidence"])
    for div in c["divisions"]:
        out += div["evidence"]
        for e in div["events"]:
            out += e["evidence"]
    return out


def review(client, eid, status, headers=None):
    return client.patch(f"/source-evidence/{eid}", json={"review_status": status}, headers=headers or {})


def fresh(client, cid, headers=None):
    return client.get(f"/competitions/{cid}", headers=headers or {}).json()


# ---------------------------------------------------------------- evidence is attached per published field
def test_manual_entry_records_evidence_for_each_published_field_quoting_the_source(demo):
    client, *_ = demo
    c = make(client)
    carry = next(e for e in c["divisions"][0]["events"] if e["name"] == "Carry")
    assert {x["field_name"] for x in carry["evidence"]} == {"scoring_type", "load_kg", "load_per_hand", "time_limit_s", "distance_m"}
    assert all(x["excerpt"] == "80 kg each hand, 20 m course, 45 s cap" and x["url"] == "https://example.org/rules" for x in carry["evidence"])
    lift = next(e for e in c["divisions"][0]["events"] if e["name"] == "Deadlift")
    assert {x["field_name"] for x in lift["evidence"]} == {"scoring_type", "load_kg"}
    assert lift["evidence"][0]["excerpt"] == "200 kg"  # falls back to the text as published
    assert {x["field_name"] for x in c["divisions"][0]["evidence"]} == {"weight_range", "eligibility_notes"}
    assert all(x["review_status"] == "manual_unreviewed" for x in all_evidence(c))
    assert c["last_confirmed_at"] is None and c["verification_status"] == "unverified"


def test_seeded_fixtures_carry_field_level_evidence(demo):
    client, *_ = demo
    c = client.get(f"/competitions/{next(x for x in client.get('/competitions').json() if x['title'].startswith('Harbor'))['id']}").json()
    carry = next(e for e in c["divisions"][0]["events"] if e["name"].startswith("Farmer"))
    assert {"load_kg", "load_per_hand", "time_limit_s", "distance_m"} <= {x["field_name"] for x in carry["evidence"]}
    assert "weight_range" in {x["field_name"] for x in c["divisions"][0]["evidence"]}


# ---------------------------------------------------------------- review + roll-up
def test_confirming_everything_verifies_the_competition_and_sets_last_confirmed(demo):
    client, *_ = demo
    c = make(client)
    rows = all_evidence(c)
    first = review(client, rows[0]["id"], "confirmed")
    assert first.status_code == 200 and first.json()["evidence"]["review_status"] == "confirmed"
    mid = fresh(client, c["id"])
    assert mid["last_confirmed_at"] is not None and mid["verification_status"] == "unverified"  # others still unreviewed
    for x in rows[1:]:
        assert review(client, x["id"], "confirmed").status_code == 200
    done = fresh(client, c["id"])
    assert done["verification_status"] == "verified"
    assert all(e["verification_status"] == "verified" for dv in done["divisions"] for e in dv["events"])


def test_a_conflict_beats_confirmation_and_is_visible_in_the_gap_report(demo_athlete):
    client, *_ = demo_athlete
    c = make(client)
    rows = all_evidence(c)
    for x in rows:
        review(client, x["id"], "confirmed")
    assert fresh(client, c["id"])["verification_status"] == "verified"
    load_row = next(x for dv in c["divisions"] for e in dv["events"] if e["name"] == "Deadlift" for x in e["evidence"] if x["field_name"] == "load_kg")
    review(client, load_row["id"], "conflicting")
    after = fresh(client, c["id"])
    assert after["verification_status"] == "conflicting"
    lift = next(e for dv in after["divisions"] for e in dv["events"] if e["name"] == "Deadlift")
    carry = next(e for dv in after["divisions"] for e in dv["events"] if e["name"] == "Carry")
    assert lift["verification_status"] == "conflicting" and carry["verification_status"] == "verified"
    a = client.post("/assessments", json={"competition_id": c["id"], "division_id": c["divisions"][0]["id"]}).json()
    gaps = " ".join(a["result"]["data_gaps"])
    assert "'Deadlift'" in gaps and "conflicting" in gaps and "'Carry'" not in gaps
    # resolving the conflict restores verification
    review(client, load_row["id"], "confirmed")
    assert fresh(client, c["id"])["verification_status"] == "verified"


def test_reset_returns_to_unverified_but_keeps_the_last_confirmed_time(demo):
    client, *_ = demo
    c = make(client)
    x = all_evidence(c)[0]
    review(client, x["id"], "confirmed")
    stamp = fresh(client, c["id"])["last_confirmed_at"]
    out = review(client, x["id"], "unverified")
    assert out.json()["evidence"]["review_status"] == "unverified"
    after = fresh(client, c["id"])
    assert after["verification_status"] == "unverified" and after["last_confirmed_at"] == stamp


def test_reviewing_does_not_change_requirements_so_reports_stay_fresh(demo_athlete):
    client, *_ = demo_athlete
    c = make(client)
    a = client.post("/assessments", json={"competition_id": c["id"], "division_id": c["divisions"][0]["id"]}).json()
    review(client, all_evidence(c)[0]["id"], "conflicting")
    assert client.get(f"/assessments/{a['id']}").json()["stale"] is False


@pytest.mark.parametrize("status", ["verified", "fixture", "manual_unreviewed", "", "CONFIRMED"])
def test_only_the_three_reviewer_statuses_are_accepted(demo, status):
    client, *_ = demo
    c = make(client)
    assert review(client, all_evidence(c)[0]["id"], status).status_code == 422


# ---------------------------------------------------------------- permissions
def test_shared_catalog_evidence_is_read_only_and_unknown_ids_404(demo):
    client, Session, *_ = demo
    with Session() as db:
        shared = db.query(SourceEvidence).first().id
    assert review(client, shared, "confirmed").status_code == 403
    assert review(client, 999999, "confirmed").status_code == 404
    with Session() as db:
        assert db.get(SourceEvidence, shared).review_status == "fixture"


def test_other_accounts_cannot_review_my_evidence(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    c = make(client, headers=A)
    eid = all_evidence(c)[0]["id"]
    assert review(client, eid, "confirmed", headers=B).status_code == 404
    assert review(client, eid, "confirmed", headers={}).status_code == 401
    assert fresh(client, c["id"], headers=A)["last_confirmed_at"] is None
    assert review(client, eid, "confirmed", headers=A).status_code == 200
    assert client.get(f"/competitions/{c['id']}", headers=B).status_code == 404  # B cannot even see it


# ---------------------------------------------------------------- old databases
def test_backfill_adds_missing_fixture_evidence_without_duplicating_or_overwriting(demo):
    client, Session, *_ = demo
    with Session() as db:
        before = db.query(SourceEvidence).count()
        seed_competitions(db)                      # idempotent: nothing new
        assert db.query(SourceEvidence).count() == before
        carry_rows = db.query(SourceEvidence).filter_by(entity_type="event", field_name="distance_m").all()
        assert carry_rows
        db.query(SourceEvidence).filter(SourceEvidence.field_name.in_(["distance_m", "weight_range"])).delete(synchronize_session=False)
        edited = db.query(SourceEvidence).filter_by(entity_type="event", field_name="time_limit_s").first()
        edited.review_status = "confirmed"          # a reviewer's change must survive
        edited_id = edited.id
        db.commit()
        seed_competitions(db)
        assert db.query(SourceEvidence).filter_by(field_name="distance_m").count() == len(carry_rows)
        assert db.query(SourceEvidence).filter_by(field_name="weight_range").count() > 0
        assert db.get(SourceEvidence, edited_id).review_status == "confirmed"
