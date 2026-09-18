"""The demo switches of contract §8, as a screen drives them.

Two failures, both of the worst available kind — the caller is told it worked:

  * the body §8 documents (nested under `scenarios`) returned `200` and changed
    nothing, because `ScenarioRequest` had no such field and Pydantic dropped it;
  * `{"enabled": false}` could not switch the demo off, because `set_state`
    re-enabled it whenever any sub-scenario was still true.

A frontend built from the contract would have shipped toggles that do nothing
and an off switch that does not turn off.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import scenario
from app.main import app


@pytest.fixture(autouse=True)
def reset_scenario():
    """The state is a module-level global, so it leaks between tests."""
    scenario.set_state(enabled=False, lift_outage_outram=False, ewl_disruption=False)
    yield
    scenario.set_state(enabled=False, lift_outage_outram=False, ewl_disruption=False)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def flags(response) -> dict:
    return response.json()["scenarios"]


# --- both shapes have to work ----------------------------------------------

def test_the_nested_body_the_contract_documents_works(client):
    """§8 shows the state nested under `scenarios`; posting it back did nothing."""
    body = {"scenarios": {"lift_outage_outram": True}}

    response = client.post("/api/scenario", json=body)

    assert flags(response)["lift_outage_outram"] is True
    assert response.json()["enabled"] is True


def test_the_flat_body_still_works(client):
    response = client.post("/api/scenario", json={"lift_outage_outram": True})

    assert flags(response)["lift_outage_outram"] is True


def test_the_get_response_can_be_posted_back_unchanged(client):
    """The obvious way to drive this from a screen: read it, flip a bit, send it."""
    state = client.get("/api/scenario").json()
    state["scenarios"]["ewl_disruption"] = True

    response = client.post("/api/scenario", json=state)

    assert flags(response)["ewl_disruption"] is True


def test_nested_and_flat_agree(client):
    client.post("/api/scenario", json={"lift_outage_outram": True})
    nested = client.get("/api/scenario").json()

    client.post("/api/scenario", json={"lift_outage_outram": False})
    client.post("/api/scenario", json={"scenarios": {"lift_outage_outram": True}})

    assert client.get("/api/scenario").json() == nested


# --- a wrong key must not look like success --------------------------------

@pytest.mark.parametrize("body", [
    {"lift_outage": True},                       # the real key is lift_outage_outram
    {"scenarios": {"lift_outage": True}},
    {"ewl_disrupton": True},                     # typo
    {"enabled": True, "nonsense": 1},
])
def test_an_unknown_switch_is_rejected_not_ignored(client, body):
    """It used to return 200 and change nothing, which is indistinguishable from
    a working call until someone notices the demo never arms."""
    assert client.post("/api/scenario", json=body).status_code == 422


def test_the_rejection_names_the_field(client):
    response = client.post("/api/scenario", json={"lift_outage": True})

    assert "lift_outage" in response.text


# --- the off switch ---------------------------------------------------------

def test_enabled_false_switches_the_demo_off(client):
    """The master switch could not be turned off while a scenario was armed."""
    client.post("/api/scenario", json={"lift_outage_outram": True})

    response = client.post("/api/scenario", json={"enabled": False})

    assert response.json()["enabled"] is False


def test_switching_off_silences_the_simulated_data(client):
    """The state is only worth anything if it reaches the payload."""
    trip = client.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}).json()
    client.post("/api/scenario", json={"lift_outage_outram": True})
    armed = client.get(f"/api/trips/{trip['trip_id']}/status").json()

    client.post("/api/scenario", json={"enabled": False})
    quiet = client.get(f"/api/trips/{trip['trip_id']}/status").json()

    assert any(a["source"] == "simulated" for a in armed["lift_alerts"])
    assert not any(a["source"] == "simulated" for a in quiet["lift_alerts"])


def test_switching_off_remembers_which_scenarios_were_armed(client):
    """`_on()` reads both, so the master switch alone is enough to silence it —
    and the screen's checkboxes should not all clear when you pause the demo."""
    client.post("/api/scenario", json={"lift_outage_outram": True})

    off = client.post("/api/scenario", json={"enabled": False}).json()

    assert off["enabled"] is False
    assert off["scenarios"]["lift_outage_outram"] is True


def test_arming_a_scenario_arms_the_demo(client):
    """A screen should not have to send `enabled` as well."""
    response = client.post("/api/scenario", json={"ewl_disruption": True})

    assert response.json()["enabled"] is True


def test_disarming_the_last_scenario_leaves_the_master_switch_alone(client):
    """Turning a scenario off is not a request to change the master switch."""
    client.post("/api/scenario", json={"lift_outage_outram": True})

    response = client.post("/api/scenario", json={"lift_outage_outram": False})

    assert response.json()["enabled"] is True
    assert response.json()["scenarios"]["lift_outage_outram"] is False


def test_an_empty_body_changes_nothing(client):
    client.post("/api/scenario", json={"lift_outage_outram": True})
    before = client.get("/api/scenario").json()

    assert client.post("/api/scenario", json={}).json() == before
