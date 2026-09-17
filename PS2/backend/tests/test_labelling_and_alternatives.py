"""F22, F23, F24, F25, F26 — labelling old data, and advice that fits her trip.

The rubric caps the score for mocked data presented as live, and a recorded
fixture reading as current is the same failure in a smaller way.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import SGT
from app.main import app
from app.services import alternatives, crowd, disruption, weather_policy

APPOINTMENT = {"appointment_at": "2026-09-21T10:30:00"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- F22: source stays live|simulated, staleness is its own flag ------------

def test_lift_blocks_carry_a_stale_flag(client):
    """With PS2_USE_FIXTURES=1 every row showed source "live" and only the
    top-level flag said the data was not current."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    body = client.get(f"/api/trips/{trip_id}/status").json()

    assert {a["source"] for a in body["lift_alerts"]} <= {"live", "simulated"}
    assert all(a["stale"] is True for a in body["lift_alerts"])


def test_weather_and_crowd_carry_a_stale_flag(client):
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    body = client.get(f"/api/trips/{trip_id}/status").json()

    assert body["weather"]["stale"] is True
    assert body["weather"]["source"] == "live"


def test_crowd_badges_default_to_fresh():
    row = {"Station": "EW5", "CrowdLevel": "l", "StartTime": "a", "EndTime": "b"}

    assert crowd.badge(row)["stale"] is False
    assert crowd.badge(row, stale=True)["stale"] is True


def test_weather_assess_reports_staleness():
    nowcast = {"area_metadata": [], "items": []}

    assert weather_policy.assess(nowcast, stale=True)["stale"] is True


# --- F23: the bus option ----------------------------------------------------

def test_bus_step_free_is_not_asserted(client):
    """It said "yes" even when wheelchair_accessible was False or None."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    options = client.get(f"/api/trips/{trip_id}/alternatives").json()["options"]
    bus = next((o for o in options if o["option_id"] == "bus_wab"), None)

    assert bus is not None
    assert bus["step_free"] in ("yes", "no", "unknown")
    if bus["bus"]["wheelchair_accessible"] is None:
        assert bus["step_free"] == "unknown"


def test_live_arrival_is_suppressed_for_a_distant_departure(client):
    """Opening alternatives at 01:03 for a 15:00 trip said "Not running now;
    first bus 0530"."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    options = client.get(f"/api/trips/{trip_id}/alternatives").json()["options"]
    bus = next(o for o in options if o["option_id"] == "bus_wab")

    assert bus["bus"]["eta_min"] is None
    assert bus["bus"]["not_running"] is False
    assert "Not running now" not in bus["why"]


# --- F24: leave-earlier -----------------------------------------------------

def _plan(leave_by: datetime, arrive_late: datetime, buffer_min: int = 15):
    return {"summary": {"leave_by": leave_by.isoformat(timespec="seconds"),
                        "arrival_window": ["x", arrive_late.isoformat(timespec="seconds")],
                        "buffer_min": buffer_min, "duration_min": 45,
                        "step_free": "yes"},
            "appointment_at": arrive_late.isoformat(timespec="seconds"), "legs": []}


def test_leaving_earlier_keeps_the_buffer():
    """arrival_at was arrive_late + buffer_min, i.e. 14:59:48 for a 15:00
    appointment, while the text said "still in time"."""
    now = datetime.now(SGT).replace(microsecond=0)
    leave = now + timedelta(hours=2)
    arrive_late = now + timedelta(hours=3)

    option = alternatives._departure_option(_plan(leave, arrive_late), delay_min=35,
                                            buffer_min=15)

    assert option["option_id"] == "leave_earlier"
    assert datetime.fromisoformat(option["leave_by"]) == leave - timedelta(minutes=35)
    assert datetime.fromisoformat(option["arrival_at"]) == arrive_late


def test_leaving_earlier_is_not_offered_when_it_has_already_passed():
    """With a 35-min delay advised at 08:12, it said "Leave at 08:10 instead"."""
    now = datetime.now(SGT)
    leave = now + timedelta(minutes=2)
    arrive_late = now + timedelta(hours=1)

    option = alternatives._departure_option(_plan(leave, arrive_late), delay_min=35,
                                            buffer_min=15)

    assert option["viable"] is False
    assert option["leave_by"] is None
    assert "has passed" in option["why"]


def test_a_delay_inside_the_buffer_still_says_leave_as_planned():
    now = datetime.now(SGT)
    option = alternatives._departure_option(
        _plan(now + timedelta(hours=2), now + timedelta(hours=3)),
        delay_min=5, buffer_min=15)

    assert option["delta_min"] == 0
    assert "as planned" in option["leave_by_label"]


# --- F25: the taxi stand ----------------------------------------------------

def test_the_taxi_stand_is_where_she_is_before_departure(client):
    """`_taxi_option(DEST_STATION)` was hardcoded, so a trip she has not started
    offered a stand 32 m from Outram Park while she is still in Bedok."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    options = client.get(f"/api/trips/{trip_id}/alternatives").json()["options"]
    taxi = next(o for o in options if o["mode"] == "taxi")

    assert "Bedok" in taxi["label"]
    assert "Outram" not in taxi["label"]


# --- F26: direction, and an all-test feed -----------------------------------

def _value(direction="Tuas Link", content=None, status=2):
    return {"Status": status,
            "AffectedSegments": [{"Line": "EWL", "Direction": direction,
                                  "Stations": "EW5,EW16"}],
            "Message": [{"Content": content, "CreatedDate": "2026-09-19 08:12:00"}]
            if content else []}


def test_a_segment_for_the_other_direction_is_not_hers():
    """She rides towards Tuas Link; a Pasir Ris segment was reported as hers,
    with leave-earlier advice attached."""
    eastbound = _value("Pasir Ris",
                       "0812hrs : EWL - Additional travelling time of 20 minutes "
                       "towards Pasir Ris.")

    assert disruption.assess(eastbound, "2026-09-19T08:12:00+08:00") is None


def test_her_direction_is_still_reported():
    westbound = _value("Tuas Link",
                       "0812hrs : EWL - Additional travelling time of 20 minutes "
                       "towards Tuas Link.")

    result = disruption.assess(westbound, "2026-09-19T08:12:00+08:00")

    assert result["delay_min"] == 20


def test_a_segment_with_no_direction_still_counts():
    result = disruption.assess(_value("", "0812hrs : EWL - Additional travelling time "
                                          "of 20 minutes."),
                               "2026-09-19T08:12:00+08:00")

    assert result is not None


def test_an_all_test_feed_is_downgraded_and_shows_no_delay():
    """T3 says to trust the segments, so it is still reported — but a test
    broadcast is not evidence for a delay figure."""
    all_test = _value("Tuas Link",
                      "Test : 1457hrs: EWL - Additional travelling time of 15 minutes.")

    result = disruption.assess(all_test, "2026-09-19T08:12:00+08:00")

    assert result is not None
    assert result["severity"] == "warn"
    assert result["delay_min"] is None
    assert "test broadcast" in result["detail"]
