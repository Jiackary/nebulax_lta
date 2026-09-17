"""F15, F16, F21 — request validation and the error shape the contract promises.

Ported from `.claude/repro/rev/` and `vr/C/`.
"""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import trips
from app.main import app
from app.sources import onemap

FUTURE = "2026-09-21T10:30:00"


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# --- F21: the error shape is always top level -------------------------------

def test_unknown_route_uses_the_contract_error_shape(client):
    body = client.get("/api/nope").json()

    assert body["error"]["code"] == "NOT_FOUND"
    assert "detail" not in body


def test_wrong_method_uses_the_contract_error_shape(client):
    body = client.post("/api/health").json()

    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "detail" not in body


def test_an_uncaught_exception_is_not_text_plain(client, monkeypatch):
    def explode(*_args, **_kwargs):
        # Not RuntimeError: the route catches that and answers 400 by design.
        raise ZeroDivisionError("boom")

    monkeypatch.setattr(trips, "build_plan", explode)

    response = client.post("/api/trips", json={"appointment_at": FUTURE})

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["error"]["retryable"] is True


# --- F15: request validation ------------------------------------------------

@pytest.mark.parametrize("coord", [[], [103.93], [103.93, 1.32, 5.0]])
def test_coord_must_be_a_pair(client, coord):
    """These reached a TypeError and came back as a plain-text 500."""
    response = client.post("/api/trips",
                           json={"appointment_at": FUTURE, "origin": {"coord": coord}})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_coord_must_be_on_earth(client):
    response = client.post("/api/trips", json={
        "appointment_at": FUTURE, "origin": {"coord": [999.0, 999.0]}})

    assert response.status_code == 422


@pytest.mark.parametrize("buffer_min", [-120, 1_000_000_000_000])
def test_buffer_min_is_bounded(client, buffer_min):
    """-120 produced a leave-by after the appointment; 1e12 overflowed to a 500."""
    response = client.post("/api/trips", json={
        "appointment_at": FUTURE, "preferences": {"buffer_min": buffer_min}})

    assert response.status_code == 422


@pytest.mark.parametrize("when", ["2001-03-04T10:30:00", "9999-01-01T10:30:00"])
def test_appointments_outside_a_sane_window_are_rejected(client, when):
    response = client.post("/api/trips", json={"appointment_at": when})

    assert response.status_code == 422


def test_walking_pace_is_an_enum(client):
    """'sprint' was accepted, stored, and silently planned as slow."""
    response = client.post("/api/trips", json={
        "appointment_at": FUTURE, "preferences": {"walking_pace": "sprint"}})

    assert response.status_code == 422


def test_a_valid_request_still_plans(client):
    response = client.post("/api/trips", json={
        "appointment_at": FUTURE,
        "preferences": {"walking_pace": "steady", "buffer_min": 20}})

    assert response.status_code == 200
    assert response.json()["summary"]["buffer_min"] == 20


# --- F16: address search --------------------------------------------------

def test_address_search_short_circuits_in_fixtures_mode(client):
    """OneMap ignored PS2_USE_FIXTURES entirely and still called out."""
    response = client.get("/api/places/search", params={"q": "outram"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


def test_address_search_reports_network_errors_as_upstream(client, monkeypatch):
    """Only OneMapAuthError was caught; a timeout or 5xx gave a 500."""
    monkeypatch.setattr(trips, "USE_FIXTURES", False)

    async def timeout(_q):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(onemap, "search", timeout)

    response = client.get("/api/places/search", params={"q": "outram"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert response.json()["error"]["retryable"] is True


def test_address_search_reports_a_non_json_body_as_upstream(client, monkeypatch):
    monkeypatch.setattr(trips, "USE_FIXTURES", False)

    async def not_json(_q):
        raise ValueError("Expecting value: line 1 column 1")

    monkeypatch.setattr(onemap, "search", not_json)

    assert client.get("/api/places/search", params={"q": "outram"}).status_code == 503
