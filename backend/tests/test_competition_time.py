from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.data.fixtures import seed_competitions
from app.models import Competition
from app.services.times import to_utc, valid_timezone

FUTURE = (date.today() + timedelta(days=40)).isoformat()


def body(**over):
    b = {"title": "Timed Show", "start_date": FUTURE, "divisions": [{"name": "Open", "category": "open", "events": []}]}
    b.update(over)
    return b


# ---------------------------------------------------------------- unit
def test_to_utc_uses_the_venue_zone_including_daylight_saving():
    assert to_utc(date(2026, 12, 6), time(9, 0), "Asia/Manila") == datetime(2026, 12, 6, 1, 0, tzinfo=timezone.utc)
    assert to_utc(date(2026, 7, 1), time(9, 0), "America/New_York") == datetime(2026, 7, 1, 13, 0, tzinfo=timezone.utc)  # EDT
    assert to_utc(date(2026, 12, 1), time(9, 0), "America/New_York") == datetime(2026, 12, 1, 14, 0, tzinfo=timezone.utc)  # EST
    assert to_utc(date(2026, 1, 1), time(0, 30), "UTC") == datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize("t,tz", [(None, "Asia/Manila"), (time(9, 0), None), (time(9, 0), ""), (time(9, 0), "Mars/Olympus")])
def test_to_utc_never_guesses(t, tz):
    assert to_utc(date(2026, 12, 6), t, tz) is None


def test_valid_timezone():
    assert valid_timezone("Asia/Manila") and valid_timezone("UTC") and valid_timezone("Europe/London")
    assert not valid_timezone("Mars/Olympus") and not valid_timezone("../etc/passwd") and not valid_timezone("")


# ---------------------------------------------------------------- API
def test_time_and_zone_round_trip_with_derived_utc(demo):
    client, *_ = demo
    r = client.post("/competitions", json=body(start_time="09:00:00", timezone="Asia/Manila"))
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["start_time"] == "09:00:00" and c["timezone"] == "Asia/Manila"
    expect = datetime.combine(date.fromisoformat(FUTURE), time(1, 0), tzinfo=timezone.utc).isoformat()
    assert c["start_at_utc"] == expect
    listed = next(x for x in client.get("/competitions").json() if x["id"] == c["id"])
    assert listed["start_at_utc"] == expect and listed["start_time"] == "09:00:00"


def test_a_bare_time_or_an_unknown_zone_is_rejected(demo):
    client, *_ = demo
    r = client.post("/competitions", json=body(start_time="09:00:00"))
    assert r.status_code == 422 and "time zone" in str(r.json()["detail"])
    r = client.post("/competitions", json=body(start_time="09:00:00", timezone="Mars/Olympus"))
    assert r.status_code == 422 and "unknown time zone" in str(r.json()["detail"])
    assert client.post("/competitions", json=body(timezone="Nowhere/Land")).status_code == 422


def test_unknown_time_stays_unknown(demo):
    client, *_ = demo
    c = client.post("/competitions", json=body()).json()
    assert c["start_time"] is None and c["timezone"] is None and c["start_at_utc"] is None
    z = client.post("/competitions", json=body(timezone="Asia/Manila")).json()  # zone known, time not published
    assert z["start_time"] is None and z["start_at_utc"] is None and z["timezone"] == "Asia/Manila"


def test_seeded_fixtures_have_times_and_one_is_left_unpublished(demo):
    client, *_ = demo
    by = {c["title"].split(" (")[0]: c for c in client.get("/competitions").json()}
    assert by["Harbor Strongman Open"]["timezone"] == "Asia/Manila" and by["Harbor Strongman Open"]["start_at_utc"]
    assert by["Lakeside Open"]["start_time"] is None and by["Lakeside Open"]["start_at_utc"] is None


def test_backfill_fills_old_fixtures_but_never_overwrites_edits(demo):
    client, Session, *_ = demo
    with Session() as db:
        harbor = db.query(Competition).filter(Competition.title.like("Harbor%")).first()
        ridge = db.query(Competition).filter(Competition.title.like("Ridge%")).first()
        harbor.start_time = harbor.timezone = None      # seeded before this feature existed
        ridge.start_time, ridge.timezone = time(5, 0), "UTC"  # deliberately set to something else
        db.commit()
        assert seed_competitions(db) is False           # already seeded: only the backfill runs
        db.refresh(harbor); db.refresh(ridge)
        assert harbor.start_time == time(9, 0) and harbor.timezone == "Asia/Manila"
        assert ridge.start_time == time(5, 0) and ridge.timezone == "UTC"
