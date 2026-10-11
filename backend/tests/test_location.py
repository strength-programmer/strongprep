from datetime import date, timedelta

import pytest

from app.data.fixtures import seed_competitions
from app.models import Competition
from app.services.geo import COORD_DECIMALS, distance_km, haversine_km, round_coord
from tests.conftest import auth

FUTURE = (date.today() + timedelta(days=40)).isoformat()


def by_title(client, **params):
    r = client.get("/competitions", params=params)
    assert r.status_code == 200, r.text
    return {c["title"].split(" (")[0]: c for c in r.json()}, r


def manual(client, **over):
    b = {"title": "My Show", "start_date": FUTURE, "divisions": [{"name": "Open", "category": "open", "events": []}]}
    b.update(over)
    r = client.post("/competitions", json=b)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- unit
def test_haversine_known_distances():
    assert haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.5, abs=1.0)  # London-Paris
    assert haversine_km(14.6, 121.0, 14.6, 121.0) == 0
    assert haversine_km(0, 0, 0, 180) == pytest.approx(20015, abs=5)  # half the equator
    assert haversine_km(10, 20, 30, 40) == pytest.approx(haversine_km(30, 40, 10, 20))  # symmetric


def test_coordinates_are_rounded_to_about_a_kilometre_and_missing_stays_missing():
    assert COORD_DECIMALS == 2 and round_coord(14.60491) == 14.6 and round_coord(121.0051) == 121.01 and round_coord(None) is None
    from types import SimpleNamespace as NS
    me, venue = NS(approx_lat=14.6, approx_lon=121.0), NS(latitude=14.6, longitude=120.98)
    assert distance_km(me, venue) == 2
    assert distance_km(None, venue) is None
    assert distance_km(NS(approx_lat=None, approx_lon=None), venue) is None
    assert distance_km(me, NS(latitude=None, longitude=None)) is None


# ---------------------------------------------------------------- API: distance and radius filter
def test_distances_are_returned_and_labelled_by_the_api_as_numbers_only(demo_athlete):
    client, *_ = demo_athlete
    by, _ = by_title(client)
    assert by["Harbor Strongman Open"]["approx_distance_km"] <= 4
    assert 150 < by["Ridge Iron Games"]["approx_distance_km"] < 260
    assert "approx_lat" not in str(by["Harbor Strongman Open"])  # the athlete's own coordinates are never echoed back


def test_within_km_filters_and_reports_competitions_it_cannot_judge(demo_athlete):
    client, *_ = demo_athlete
    nocoords = manual(client, title="Unlocated Show")
    far = manual(client, title="Far Show", latitude=35.0, longitude=139.0)
    near = manual(client, title="Near Show", latitude=14.61, longitude=121.01)
    assert nocoords["approx_distance_km"] is None and near["approx_distance_km"] <= 3
    by, r = by_title(client, within_km=60)
    assert {"Harbor Strongman Open", "Quarry Challenge", "Lakeside Open", "Old Quarter Throwdown", "Near Show"} == set(by)
    assert "Ridge Iron Games" not in by and "Far Show" not in by
    assert "Unlocated Show" not in by and r.headers["x-unknown-distance-count"] == "1"  # hidden, but counted and reported
    assert set(by_title(client, within_km=5)[0]) == {"Harbor Strongman Open", "Old Quarter Throwdown", "Near Show"}
    unfiltered, r2 = by_title(client)
    assert "Unlocated Show" in unfiltered and "x-unknown-distance-count" not in r2.headers  # never hidden without a radius


def test_filter_without_an_athlete_location_is_a_clear_error(demo):
    client, *_ = demo
    r = client.get("/competitions", params={"within_km": 50})
    assert r.status_code == 422 and "approximate location" in r.json()["detail"]
    assert all(c["approx_distance_km"] is None for c in client.get("/competitions").json())
    for bad in (0, -5, 99999):
        assert client.get("/competitions", params={"within_km": bad}).status_code == 422


def test_profile_location_is_rounded_and_validated(demo_athlete):
    client, *_ = demo_athlete
    base = {k: v for k, v in client.get("/athlete-profile").json()["profile"].items()
            if k in ("body_weight_kg", "age", "division_category", "days_per_week", "session_minutes")}
    ok = client.put("/athlete-profile", json={**base, "approx_lat": 14.60491, "approx_lon": 121.0051})
    assert ok.status_code == 200
    p = ok.json()["profile"]
    assert p["approx_lat"] == 14.6 and p["approx_lon"] == 121.01  # an exact position is never stored
    assert client.put("/athlete-profile", json={**base, "approx_lat": 14.6}).status_code == 422  # both or neither
    assert client.put("/athlete-profile", json={**base, "approx_lat": 91, "approx_lon": 0}).status_code == 422
    assert client.put("/athlete-profile", json={**base, "approx_lat": 0, "approx_lon": 181}).status_code == 422
    cleared = client.put("/athlete-profile", json=base).json()["profile"]
    assert cleared["approx_lat"] is None and cleared["approx_lon"] is None
    assert client.get("/competitions", params={"within_km": 50}).status_code == 422  # filter needs a location again


def test_manual_competition_location_must_be_a_pair_and_in_range(demo_athlete):
    client, *_ = demo_athlete
    body = {"title": "X", "start_date": FUTURE, "divisions": [{"name": "Open", "category": "open", "events": []}]}
    assert client.post("/competitions", json={**body, "latitude": 14.6}).status_code == 422
    assert client.post("/competitions", json={**body, "latitude": 95, "longitude": 0}).status_code == 422
    c = manual(client, latitude=14.6, longitude=121.0)
    assert c["latitude"] == 14.6 and client.get(f"/competitions/{c['id']}").json()["approx_distance_km"] == 0


def test_detail_page_includes_distance(demo_athlete):
    client, *_ = demo_athlete
    harbor = next(c for c in client.get("/competitions").json() if c["title"].startswith("Harbor"))
    assert client.get(f"/competitions/{harbor['id']}").json()["approx_distance_km"] <= 4


def test_backfill_adds_coordinates_to_old_fixtures_without_overwriting(demo):
    client, Session, *_ = demo
    with Session() as db:
        harbor = db.query(Competition).filter(Competition.title.like("Harbor%")).first()
        ridge = db.query(Competition).filter(Competition.title.like("Ridge%")).first()
        harbor.latitude = harbor.longitude = None
        ridge.latitude, ridge.longitude = 1.0, 2.0
        db.commit()
        seed_competitions(db)
        db.refresh(harbor); db.refresh(ridge)
        assert (harbor.latitude, harbor.longitude) == (14.6, 120.98)
        assert (ridge.latitude, ridge.longitude) == (1.0, 2.0)


def test_another_accounts_location_is_never_used(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    base = {"body_weight_kg": 95, "age": 30, "division_category": "men", "days_per_week": 4, "session_minutes": 75}
    client.put("/athlete-profile", json={**base, "approx_lat": 14.6, "approx_lon": 121.0}, headers=A)
    client.put("/athlete-profile", json=base, headers=B)
    assert client.get("/competitions", params={"within_km": 60}, headers=A).status_code == 200
    assert client.get("/competitions", params={"within_km": 60}, headers=B).status_code == 422
    assert all(c["approx_distance_km"] is None for c in client.get("/competitions", headers=B).json())
    assert client.get("/competitions", params={"within_km": 60}).status_code == 422  # anonymous: no location to use
    exp_b = client.get("/export", headers=B).json()["profile"]
    assert exp_b["approx_lat"] is None and exp_b["approx_lon"] is None  # B's data holds none of A's coordinates
    assert client.get("/export", headers=A).json()["profile"]["approx_lat"] == 14.6
