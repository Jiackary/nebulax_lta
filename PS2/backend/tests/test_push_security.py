"""F03, F04, F05, F14 — the push endpoints as an unauthenticated attacker sees them.

Every test in `test_push_delivery.py` stubs the sender, so none of these paths
were exercised at all. Taken from `.claude/repro/push_repro.py` and
`.claude/repro/http_repro.py`.
"""
from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import store
from app.api import push
from app.main import app

GOOD = "https://fcm.googleapis.com/fcm/send/abc123"
KEYS = {"p256dh": "BPb0v...", "auth": "k9s..."}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _subscribe(client, endpoint, trip_ids):
    return client.post("/api/push/subscribe", json={
        "subscription": {"endpoint": endpoint, "keys": KEYS}, "trip_ids": trip_ids})


# --- F03: SSRF via the subscription endpoint --------------------------------

@pytest.mark.parametrize("endpoint", [
    "http://169.254.169.254/latest/meta-data/",      # cloud metadata
    "https://127.0.0.1:8000/internal/admin",
    "http://localhost/admin",
    "https://example.com/not-a-push-service",
    "file:///etc/passwd",
    "https://fcm.googleapis.com.evil.test/x",        # suffix confusion
    "https://evil.test/#fcm.googleapis.com",
])
def test_subscribe_rejects_endpoints_that_are_not_push_services(client, endpoint):
    assert _subscribe(client, endpoint, []).status_code == 422


@pytest.mark.parametrize("endpoint", [
    "https://fcm.googleapis.com/fcm/send/abc",
    "https://web.push.apple.com/abc",
    "https://sin.notify.windows.com/w/?token=abc",
    "https://updates.push.services.mozilla.com/wpush/v2/abc",
])
def test_subscribe_accepts_the_real_push_services(client, endpoint):
    assert _subscribe(client, endpoint, []).status_code == 200


def test_send_push_refuses_a_disallowed_endpoint_without_calling_out(monkeypatch):
    called = []
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-key")
    import pywebpush
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: called.append(kw))

    sent, error = push.send_push({"endpoint": "http://127.0.0.1:1/x", "keys": KEYS}, {})

    assert sent is False
    assert error == "ENDPOINT_NOT_ALLOWED"
    assert called == []


def test_upstream_response_body_is_never_returned_to_the_caller(monkeypatch):
    """pywebpush puts the upstream body in its exception text; that used to be
    handed back in results[].error."""
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-key")
    import pywebpush

    def boom(**kwargs):
        raise Exception("Push failed: 404 Not Found\n"
                        "Response body:INTERNAL-ADMIN-PAGE-CONTENT")

    monkeypatch.setattr(pywebpush, "webpush", boom)

    sent, error = push.send_push({"endpoint": GOOD, "keys": KEYS}, {})

    assert sent is False
    assert error == "PUSH_FAILED"
    assert "INTERNAL-ADMIN-PAGE-CONTENT" not in error


# --- F14: the sender must not block the event loop, and must time out -------

def test_webpush_is_given_a_timeout(monkeypatch):
    captured = {}
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY", "test-key")
    import pywebpush
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: captured.update(kw))

    push.send_push({"endpoint": GOOD, "keys": KEYS}, {})

    assert captured["timeout"] == push.PUSH_TIMEOUT_S


def test_a_slow_push_does_not_block_the_event_loop(monkeypatch):
    monkeypatch.setattr(push, "send_push",
                        lambda *_: (time.sleep(0.4), (True, None))[1])

    async def scenario():
        ticks = 0
        send = asyncio.create_task(push.send_push_async({"endpoint": GOOD}, {}))
        while not send.done():
            await asyncio.sleep(0.01)
            ticks += 1
        return ticks, await send

    ticks, (sent, _) = asyncio.run(scenario())

    assert sent is True
    assert ticks > 5, "event loop was blocked while the push was in flight"


# --- F04: DELETE /push/subscribe --------------------------------------------

def test_delete_without_an_endpoint_is_rejected(client):
    assert client.delete("/api/push/subscribe").status_code == 422


def test_delete_only_removes_the_caller_s_own_subscription(client):
    """One bare DELETE used to remove every subscription and every linked trip."""
    mine = client.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}).json()
    hers = client.post("/api/trips", json={"appointment_at": "2026-09-21T14:30:00"}).json()
    _subscribe(client, GOOD, [mine["trip_id"]])
    other = "https://web.push.apple.com/other-device"
    _subscribe(client, other, [hers["trip_id"]])

    result = client.delete("/api/push/subscribe", params={"endpoint": GOOD}).json()

    assert result["subscriptions_removed"] == 1
    assert result["trips_removed"] == 1
    assert client.get(f"/api/trips/{mine['trip_id']}").status_code == 404
    assert client.get(f"/api/trips/{hers['trip_id']}").status_code == 200
    assert [s["endpoint"] for s in store.subscriptions()] == [other]


def test_store_refuses_a_delete_all(client):
    with pytest.raises(ValueError):
        store.delete_subscription(None)


# --- F05: /push/test --------------------------------------------------------

def test_push_test_without_a_trip_id_is_rejected(client):
    """It used to take all_trips()[0] — someone else's trip — push to its
    owner, and return the id, which is enough to read her home coordinate."""
    client.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"})

    assert client.post("/api/push/test").status_code == 422


def test_push_test_does_not_fall_back_to_another_trip(client):
    hers = client.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}).json()

    response = client.post("/api/push/test", params={"trip_id": "t_nope"})

    assert response.status_code == 404
    assert hers["trip_id"] not in response.text
