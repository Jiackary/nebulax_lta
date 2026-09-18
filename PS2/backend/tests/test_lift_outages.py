"""F01, F02, F07 — lift outages against the route she is actually given.

For this persona a false "your route is clear" is far worse than a false warning,
so every test here asserts the *route outcome*, not the parse. `score_rules.py`
scored 16/16 while all three of these bugs were live, because it never called
`assess()`, `affects_route` or `blocked_exits`.

Taken from `.claude/repro/verify/v.py` and `.claude/repro/r3/`.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import scenario
from app.main import app
from app.services import lifts
from app.sources import datamall

APPOINTMENT = {"appointment_at": "2026-09-21T10:30:00"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def lift_rows(monkeypatch):
    """Replace the live lift feed with rows the test controls."""
    rows: list[dict] = []
    original = datamall.lifts.get

    async def fake():
        fetched = await original()
        fetched.data = list(rows)
        return fetched

    monkeypatch.setattr(datamall.lifts, "get", fake)
    return rows


def _row(desc, station="EW16"):
    return {"Line": "EWL", "StationCode": station, "StationName": "Outram Park",
            "LiftID": "X", "LiftDesc": desc}


def _exits(plan):
    return [(leg.get(end) or {}).get("exit_code")
            for leg in plan["legs"] for end in ("from", "to")]


# --- F02: a lift serving more than one exit ---------------------------------

def test_multi_exit_lift_parses_every_exit():
    assert lifts.parse_exits("Exits 5/6 Street level - Concourse")[0] == ["5", "6"]
    assert lifts.parse_exits("Exits 6 & 7 Street level")[0] == ["6", "7"]
    assert lifts.parse_exits("Exits 6, 7 Street level")[0] == ["6", "7"]
    assert lifts.parse_exits("Exit6 Street level - Concourse")[0] == ["6"]
    assert lifts.parse_exits("EXIT NO. 6 STREET LEVEL")[0] == ["6"]


def test_widened_regex_does_not_invent_exits_from_words():
    """'Exit lobby' must not parse as exit 'LO'."""
    assert lifts.parse_exits("Lift at Exit lobby, concourse to platform")[0] == []


def test_multi_exit_lift_blocks_every_exit_it_serves():
    row = lifts.match_row(_row("Exits 5/6 Street level - Concourse"))
    blocked, _ = lifts.blocked_exits(lifts.annotate_for_route([row]))

    assert blocked["EW16"] == {"5", "6"}


def test_multi_exit_outage_moves_her_off_the_second_exit(client, lift_rows):
    """The P0 itself: her plan alights at Exit 6, and 'Exits 5/6' left it there."""
    plan = client.post("/api/trips", json=APPOINTMENT).json()
    trip_id = plan["trip_id"]
    assert "Exit 6" in _exits(plan)

    lift_rows.append(_row("Exits 5/6 Street level - Concourse"))
    body = client.get(f"/api/trips/{trip_id}/status").json()

    assert body["rerouted"] is True
    assert "We have moved you to another exit." in body["overall"]["detail"]
    assert "Exit 6" not in _exits(client.get(f"/api/trips/{trip_id}").json())


# --- F01: claims we cannot support ------------------------------------------

def test_station_only_outage_does_not_claim_the_route_is_clear(client, lift_rows):
    """A concourse lift at her three-line interchange may well be on her path."""
    lift_rows.append(_row("Lift between Concourse and Platform A"))
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    overall = client.get(f"/api/trips/{trip_id}/status").json()["overall"]

    assert "does not use it" not in overall["detail"]
    assert "may affect your route" in overall["detail"]
    assert "check before you go" in overall["detail"].lower()


def test_unmatched_outage_does_not_claim_the_route_is_clear(client, lift_rows):
    lift_rows.append(_row("Exit 99 Street level - Concourse"))
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    overall = client.get(f"/api/trips/{trip_id}/status").json()["overall"]

    assert "does not use it" not in overall["detail"]
    assert "may affect your route" in overall["detail"]


def test_matched_outage_the_plan_avoids_may_still_say_so(client, lift_rows):
    """The one case where "does not use it" is provable: a door she never uses."""
    lift_rows.append(_row("Exit 4 Street level - Concourse"))
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    overall = client.get(f"/api/trips/{trip_id}/status").json()["overall"]

    assert "Your route does not use it." in overall["detail"]
    assert overall["action"]["kind"] != "view_reroute"


def test_does_not_use_it_is_never_paired_with_see_the_new_route(client, lift_rows):
    lift_rows.append(_row("Exit 4 Street level - Concourse"))
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    overall = client.get(f"/api/trips/{trip_id}/status").json()["overall"]

    assert not ("does not use it" in overall["detail"]
                and overall["action"]["label"] == "See the new route")


# --- F07: a reroute must be reversible --------------------------------------

def test_reroute_is_undone_when_the_outage_clears(client):
    """Arm the Outram scenario, call /status, disarm it, call /status again."""
    plan = client.post("/api/trips", json=APPOINTMENT).json()
    trip_id = plan["trip_id"]
    original_exits = _exits(plan)
    original_leave_by = plan["summary"]["leave_by"]
    assert "Exit 6" in original_exits

    try:
        client.post("/api/scenario", json={"lift_outage_outram": True})
        armed = client.get(f"/api/trips/{trip_id}/status").json()
        assert armed["rerouted"] is True
        assert "Exit 6" not in _exits(client.get(f"/api/trips/{trip_id}").json())

        client.post("/api/scenario",
                    json={"enabled": False, "lift_outage_outram": False})
        cleared = client.get(f"/api/trips/{trip_id}/status").json()
    finally:
        scenario.set_state(enabled=False, lift_outage_outram=False, ewl_disruption=False)

    assert cleared["rerouted"] is False
    assert cleared["overall"]["headline"] == "Your usual route is clear."

    restored = client.get(f"/api/trips/{trip_id}").json()
    assert _exits(restored) == original_exits
    assert restored["summary"]["leave_by"] == original_leave_by


def test_original_plan_survives_a_reroute(client, lift_rows):
    from app import store

    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]
    lift_rows.append(_row("Exit 6 Street level - Concourse"))
    client.get(f"/api/trips/{trip_id}/status")

    trip = store.get_trip(trip_id)

    assert "Exit 6" in _exits(trip["plan_original"])
    assert "Exit 6" not in _exits(trip["plan"])


def test_rerouted_reflects_the_route_not_this_call(client, lift_rows):
    """Second /status call: the plan already avoids the exit, but she is still
    on a rerouted plan, so `rerouted` must stay true."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]
    lift_rows.append(_row("Exit 6 Street level - Concourse"))

    first = client.get(f"/api/trips/{trip_id}/status").json()
    second = client.get(f"/api/trips/{trip_id}/status").json()

    assert first["rerouted"] is True
    assert second["rerouted"] is True
    assert "does not use it" not in second["overall"]["detail"]
