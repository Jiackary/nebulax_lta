"""The status screen must survive a thin upstream, not 500 on it.

Typing the responses introduced a failure mode the untyped API did not have: a
`response_model` **validates**, so a field the model calls required and the
upstream leaves out is no longer a null in the payload — it is a
`ResponseValidationError`, which the client sees as a 500.

That trade is only acceptable where the field genuinely cannot be missing. These
are the places it can:

  * `PCDRealTime` rows are read with `.get()` and no defaults, so a row without
    `StartTime` or `Station` yields nulls;
  * `weather.area_for()` returns `(None, inf)` when the nowcast carries no
    `area_metadata`, which is what an outage looks like;
  * a taxi stand row may have no `Name`.

None of these should cost her the whole status call. She loses one badge or one
label; the plan, the lift alerts and the disruption advice are unaffected.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import crowd as crowd_service
from app.sources import datamall, weather


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


async def _empty_nowcast(*a, **k):
    """A nowcast that parses but carries no areas — `area_for` then finds none."""
    return type("Fetched", (), {"data": {}, "stale": True,
                                "observed_iso": "2026-09-21T09:00:00+08:00"})()


async def _raises(*a, **k):
    """The upstream down entirely. `build_status` nulls the whole block."""
    raise RuntimeError("weather upstream is down")


@pytest.fixture
def trip(client):
    return client.post("/api/trips",
                       json={"appointment_at": "2026-09-21T10:30:00"}).json()["trip_id"]


def test_a_crowd_row_missing_its_window_does_not_break_status(client, trip, monkeypatch):
    """`window` is `[row.get("StartTime"), row.get("EndTime")]` — both can be null."""
    monkeypatch.setattr(crowd_service, "for_stations",
                        lambda *a, **k: [{"station_code": None, "station_name": None,
                                          "level": "unknown", "label": "No crowd reading",
                                          "severity": "info", "window": [None, None],
                                          "source": "live", "stale": True,
                                          "observed_at": "2026-09-21T09:00:00+08:00"}])

    response = client.get(f"/api/trips/{trip}/status")

    assert response.status_code == 200
    assert response.json()["crowd"][0]["window"] == [None, None]


def test_a_sparse_crowd_row_survives_the_real_badge_builder(client, trip, monkeypatch):
    """The same case, one layer lower: the badge built from an empty row."""
    badge = crowd_service.badge({}, stale=True)

    assert badge["station_code"] is None
    assert badge["window"] == [None, None]


def test_an_empty_nowcast_does_not_break_status(client, trip, monkeypatch):
    """`area_for` returns `(None, inf)` when there is no `area_metadata`."""
    monkeypatch.setattr(weather.nowcast, "get", _empty_nowcast)

    response = client.get(f"/api/trips/{trip}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["weather"]["areas"][0]["name"] is None
    # An unbounded distance serialises as null, so the schema must not say float.
    assert body["weather"]["areas"][0]["distance_km"] is None
    # And it must not claim it is dry when it read nothing (unknown is not no).
    assert "None" not in body["weather"]["label"]
    assert body["weather"]["label"] == "We could not read the rain forecast for the next 2 hours."


def test_the_plan_is_unaffected_by_a_thin_status(client, trip, monkeypatch):
    """The point of not failing the call: everything else still arrives."""
    monkeypatch.setattr(weather.nowcast, "get", _raises)

    body = client.get(f"/api/trips/{trip}/status").json()
    assert body["weather"] is None

    assert body["overall"]["headline"]
    assert "lift_alerts" in body
    assert client.get(f"/api/trips/{trip}").status_code == 200


def test_a_lift_row_with_nothing_in_it_still_serialises(client, trip, monkeypatch):
    """`LiftDesc`, `LiftID` and `StationCode` are all read with `.get()`."""
    async def one_empty_row(*a, **k):
        return type("Fetched", (), {"data": [{}], "stale": True,
                                    "observed_iso": "2026-09-21T09:00:00+08:00"})()

    monkeypatch.setattr(datamall.lifts, "get", one_empty_row)

    response = client.get(f"/api/trips/{trip}/status")

    assert response.status_code == 200
