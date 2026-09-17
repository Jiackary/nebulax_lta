"""F06, F08, F09, F10, F11, F12 — what the app claims versus what it knows.

These are the P1s that all point the same way: the app stated something it had
not checked. Ported from `.claude/repro/verify/v6.py`, `rev/`, `r3/` and
`srcrev/r_base.py`.
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import data, scenario
from app.config import HOME_DEFAULT, SGT
from app.main import app
from app.services import disruption, notify, planner
from app.sources import base, datamall

APPOINTMENT = {"appointment_at": "2026-09-21T10:30:00"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def lift_rows(monkeypatch):
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
            "LiftID": "X" + desc[-1], "LiftDesc": desc}


# --- F08: entrances must belong to the station they are offered for ---------

def test_outram_entrances_are_outram_park_s_own():
    """The bbox also holds Chinatown and Cantonment, and keying by the bare ref
    let their exits stand in for Outram Park's."""
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW16"]["station_id"]

    refs = wg.entrances_for("outram", station_id)

    assert sorted(refs) == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert all(e["name"] == "Outram Park" for e in refs.values())


def test_the_real_accessible_exit_2_is_not_overwritten():
    """Outram Exit 2 (16 m, wheelchair=yes) was replaced by Cantonment's Exit 2
    (888 m, untagged), so the tagged door could never be chosen."""
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW16"]["station_id"]

    exit_2 = wg.entrances_for("outram", station_id)["2"]

    assert exit_2["name"] == "Outram Park"
    assert exit_2["wheelchair"] == "yes"


def test_exit_6_survives_station_matching():
    """Her default door is 276 m from the centroid: a 250 m radius would drop it."""
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW16"]["station_id"]

    assert "6" in wg.entrances_for("outram", station_id)


def test_bedok_entrances_are_unaffected():
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW5"]["station_id"]

    assert sorted(wg.entrances_for("bedok", station_id)) == ["A", "B", "C"]


# --- F11: step_free is a claim ----------------------------------------------

def _plan(blocked=None):
    return planner.plan_trip(HOME_DEFAULT, datetime(2026, 9, 21, 10, 30, tzinfo=SGT),
                             blocked_exits=blocked or {}, prefer_sheltered=True)


def test_reroute_prefers_a_tagged_entrance_over_a_nearer_untagged_one():
    """With Exit 6 out she was sent to the untagged Exit 7 (555 m) rather than a
    tagged one, while still claiming step_free yes."""
    plan = _plan({"EW16": {"6"}})

    chosen = plan["legs"][2]["from"]["exit_code"].replace("Exit ", "")
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW16"]["station_id"]

    assert wg.entrances_for("outram", station_id)[chosen]["wheelchair"] == "yes"


def test_step_free_is_unknown_when_the_entrance_is_untagged(monkeypatch):
    wg = data.walk_graph()
    station_id = data.station_by_code()["EW16"]["station_id"]
    real = wg.entrances_for

    def untagged(area, sid=None):
        found = real(area, sid)
        if area != "outram":
            return found
        return {ref: {**e, "wheelchair": None} for ref, e in found.items()}

    monkeypatch.setattr(wg, "entrances_for", untagged)

    plan = _plan()

    assert plan["summary"]["step_free"] == "unknown"
    assert plan["legs"][2]["step_free"] == "unknown"
    assert plan["legs"][1]["step_free"] == "unknown"      # rail leg was hardcoded yes
    assert "could not confirm" in plan["legs"][2]["instruction"]
    assert plan["legs"][1]["access"]["alight_at"]["status"] == "unknown"


def test_step_free_is_yes_when_both_doors_are_tagged():
    plan = _plan()

    assert plan["summary"]["step_free"] == "yes"
    assert [leg["step_free"] for leg in plan["legs"]] == ["yes", "yes", "yes"]


# --- F06: a failed re-plan must not 500, and offline must not hide it -------

def _block_every_bedok_exit(rows):
    for ex in ("A", "B", "C"):
        rows.append({"Line": "EWL", "StationCode": "EW5", "StationName": "Bedok",
                     "LiftID": "X" + ex, "LiftDesc": f"Exit {ex} Street level - Concourse"})


def test_status_reports_instead_of_500_when_no_entrance_is_usable(client, lift_rows):
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]
    _block_every_bedok_exit(lift_rows)

    response = client.get(f"/api/trips/{trip_id}/status")

    assert response.status_code == 200
    assert response.json()["overall"]["severity"] == "critical"
    assert response.json()["replan_failed"] is True


def test_offline_never_serves_steps_through_a_blocked_door(client, lift_rows):
    """`steps_plain[0]` was "Walk … to Bedok MRT Exit B" — a door whose lift is
    out — with status_snapshot null and no warning at all."""
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]
    _block_every_bedok_exit(lift_rows)

    bundle = client.get(f"/api/trips/{trip_id}/offline").json()

    assert bundle["warnings"]
    assert "step-free" in bundle["steps_plain"][0]
    assert not bundle["steps_plain"][0].startswith("Walk")


def test_offline_warns_when_it_could_not_check_at_all(client, monkeypatch):
    trip_id = client.post("/api/trips", json=APPOINTMENT).json()["trip_id"]

    async def boom(_):
        raise RuntimeError("upstream down")

    monkeypatch.setattr("app.api.offline.build_status", boom)

    bundle = client.get(f"/api/trips/{trip_id}/offline").json()

    assert bundle["status_snapshot"] is None
    assert bundle["warnings"]
    assert "could not check" in bundle["warnings"][0]


# --- F09: the demo scenario must not reach real subscribers -----------------

def test_scheduled_checks_ignore_the_armed_scenario():
    try:
        scenario.set_state(ewl_disruption=True)
        scheduled = asyncio.run(notify.check_trip({"trip_id": "t_x"},
                                                  allow_simulated=False))
    finally:
        scenario.set_state(enabled=False, ewl_disruption=False,
                           lift_outage_outram=False)

    assert scheduled is None


def test_a_simulated_payload_says_so():
    try:
        scenario.set_state(ewl_disruption=True)
        payload = asyncio.run(notify.check_trip({"trip_id": "t_x"}))
    finally:
        scenario.set_state(enabled=False, ewl_disruption=False,
                           lift_outage_outram=False)

    assert payload["source"] == "simulated"
    assert payload["simulated_note"]


# --- F10: the delay figure must be her line's -------------------------------

BUNDLED_EASTBOUND = ("1820hrs : NSL - Additional travelling time of 30 minutes towards "
                     "Jurong East. EWL - Additional travelling time of 10 minutes "
                     "towards Pasir Ris.")
BUNDLED_HERS = ("1820hrs : NSL - Additional travelling time of 30 minutes towards "
                "Jurong East. EWL - Additional travelling time of 10 minutes "
                "towards Tuas Link.")
NEL_ONLY = ("1657hrs : NEL - Additional travelling time of 20 minutes between Boon Keng "
            "and Dhoby Ghaut towards HarbourFront.")


def test_another_line_s_delay_is_not_used_for_her_trip():
    assert disruption.delay_for_line(NEL_ONLY, "EWL") == (None, None)


def test_bundled_message_takes_her_line_not_the_first_figure():
    assert disruption.delay_for_line(BUNDLED_HERS, "EWL")[0] == 10
    assert disruption.parse_delay(BUNDLED_HERS)[0] == 30   # unchanged, as held


def test_a_clause_for_the_other_direction_is_not_hers():
    assert disruption.delay_for_line(BUNDLED_EASTBOUND, "EWL") == (None, None)


def test_the_scenario_replay_still_parses():
    content = ("0812hrs : EWL - Additional travelling time of 20 minutes between Bedok "
               "and Outram Park towards Tuas Link. Free bus rides available at "
               "designated bus stops.")

    assert disruption.delay_for_line(content, "EWL")[0] == 20


# --- F12: fixtures must not be rewritten from a live run --------------------

@pytest.fixture
def fixture_dir(monkeypatch, recording_enabled):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr(base, "FIXTURES", tmp)
    # These tests are about the *live* fetch path. Leaving fixtures mode on
    # would short-circuit `get()` before any recording could happen, so the
    # assertions would hold without exercising anything.
    monkeypatch.setattr(base, "USE_FIXTURES", False)
    good = [{"ServiceNo": "84"}] * 10
    (tmp / "bus.json").write_text(json.dumps(
        {"recorded_at": "2026-09-18T00:09:00+08:00", "source": "bus", "payload": good}))
    return tmp


def _services(tmp):
    return len(json.loads((tmp / "bus.json").read_text())["payload"])


def _fetch_once(payload, recording, name="bus"):
    source = base.Source(name, 0, lambda c: asyncio.sleep(0, payload))
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda r: httpx.Response(200)))
    return asyncio.run(source.get(client))


def test_recording_is_off_by_default(fixture_dir, monkeypatch):
    """Fixtures were rewritten into the git tree on every successful fetch."""
    monkeypatch.setattr(base, "RECORD_FIXTURES", False)

    _fetch_once([{"ServiceNo": "84"}], recording=False)

    assert _services(fixture_dir) == 10


def test_an_empty_out_of_hours_reply_never_overwrites_a_good_fixture(
        fixture_dir, monkeypatch):
    """BusArrival returns [] outside service hours (T17); one run after midnight
    turned a 10-service fixture into [] and the demo said 'Not running now'."""
    monkeypatch.setattr(base, "RECORD_FIXTURES", True)

    _fetch_once([], recording=True)

    assert _services(fixture_dir) == 10


def test_an_error_body_with_a_200_never_overwrites(fixture_dir, monkeypatch):
    monkeypatch.setattr(base, "RECORD_FIXTURES", True)

    _fetch_once({"code": 24, "data": None}, recording=True)

    assert _services(fixture_dir) == 10


def test_a_good_payload_is_recorded_when_recording_is_on(fixture_dir, monkeypatch):
    monkeypatch.setattr(base, "RECORD_FIXTURES", True)

    _fetch_once([{"ServiceNo": "84"}] * 3, recording=True)

    assert _services(fixture_dir) == 3


def test_a_write_failure_does_not_downgrade_a_good_fetch(fixture_dir, monkeypatch):
    """`_record` was inside the try, so a read-only filesystem turned a good 200
    into origin: 'stale'."""
    monkeypatch.setattr(base, "RECORD_FIXTURES", True)
    os.chmod(fixture_dir, 0o555)
    try:
        fetched = _fetch_once([{"ServiceNo": "84"}], recording=True, name="other")
    finally:
        os.chmod(fixture_dir, 0o755)

    assert fetched.origin == "live"
    assert fetched.stale is False


def test_a_truncated_fixture_does_not_become_a_500(fixture_dir, monkeypatch):
    monkeypatch.setattr(base, "RECORD_FIXTURES", False)
    (fixture_dir / "torn.json").write_text('{"recorded_at": "2026')

    def explode(_):
        raise RuntimeError("upstream down")

    source = base.Source("torn", 999, explode)
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda r: httpx.Response(200)))

    with pytest.raises(RuntimeError, match="upstream down"):
        asyncio.run(source.get(client))
