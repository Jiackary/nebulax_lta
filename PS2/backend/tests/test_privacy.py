"""F20, F30, F31 — the privacy statement's commitment 1, kept by the store.

"A trip is deleted 24 hours after its appointment, and immediately when she
removes it or turns notifications off" (decision record §8). All three findings
are ways that was not quite true.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app import store
from app.config import SGT

ENDPOINT = "https://fcm.googleapis.com/fcm/send/one"
OTHER = "https://web.push.apple.com/two"


def _trip(appointment: datetime) -> str:
    return store.save_trip(appointment, {"label": "Home", "coord": [103.93057, 1.324782]},
                           {}, {"summary": {}, "legs": []})


# --- F30: the trip id is the only access control ----------------------------

def test_trip_ids_are_not_guessable():
    """4 characters is about 14.8M values, and GET/DELETE/status/offline need
    nothing else — and GET returns her home coordinate."""
    trip_id = _trip(datetime.now(SGT) + timedelta(days=1))

    assert len(trip_id) >= 20


def test_trip_ids_are_unique_across_many_trips():
    ids = {_trip(datetime.now(SGT) + timedelta(days=1)) for _ in range(200)}

    assert len(ids) == 200


# --- F31: re-subscribing must not orphan an earlier trip --------------------

def test_resubscribing_keeps_the_earlier_trip_linked():
    """INSERT OR REPLACE overwrote trip_ids, so trip A stopped getting warnings
    and DELETE /push/subscribe left it on the server."""
    a = _trip(datetime.now(SGT) + timedelta(days=1))
    b = _trip(datetime.now(SGT) + timedelta(days=2))

    store.save_subscription(ENDPOINT, {"p256dh": "x"}, [a])
    store.save_subscription(ENDPOINT, {"p256dh": "x"}, [b])

    linked = store.subscriptions()[0]["trip_ids"]
    assert set(linked) == {a, b}


def test_unsubscribing_deletes_every_linked_trip():
    a = _trip(datetime.now(SGT) + timedelta(days=1))
    b = _trip(datetime.now(SGT) + timedelta(days=2))
    store.save_subscription(ENDPOINT, {}, [a])
    store.save_subscription(ENDPOINT, {}, [b])

    result = store.delete_subscription(ENDPOINT)

    assert result["trips_removed"] == 2
    assert store.get_trip(a) is None
    assert store.get_trip(b) is None


# --- F20: retention is 24 h, not 48 ----------------------------------------

def test_a_trip_is_gone_within_24_hours_of_its_appointment():
    """The 03:00-only sweep let a 03:30 appointment survive to about 47.5 h."""
    appointment = datetime(2026, 9, 21, 3, 30, tzinfo=SGT)
    trip_id = _trip(appointment)

    store.sweep(now=appointment + timedelta(hours=24, minutes=1))

    assert store.get_trip(trip_id) is None


def test_a_trip_survives_until_24_hours_have_passed():
    appointment = datetime(2026, 9, 21, 3, 30, tzinfo=SGT)
    trip_id = _trip(appointment)

    store.sweep(now=appointment + timedelta(hours=23))

    assert store.get_trip(trip_id) is not None


def test_the_sweep_drops_subscriptions_whose_trips_are_all_gone():
    """push_subs rows were never swept and kept dangling trip_ids."""
    appointment = datetime(2026, 9, 21, 3, 30, tzinfo=SGT)
    trip_id = _trip(appointment)
    store.save_subscription(ENDPOINT, {}, [trip_id])

    removed = store.sweep(now=appointment + timedelta(hours=25))

    assert removed["trips"] == 1
    assert removed["subscriptions"] == 1
    assert store.subscriptions() == []


def test_the_sweep_keeps_a_subscription_that_still_has_a_live_trip():
    past = datetime(2026, 9, 21, 3, 30, tzinfo=SGT)
    sweep_at = past + timedelta(hours=25)
    old = _trip(past)
    upcoming = _trip(sweep_at + timedelta(days=1))     # still ahead of the sweep
    store.save_subscription(ENDPOINT, {}, [old, upcoming])

    store.sweep(now=sweep_at)

    assert [s["endpoint"] for s in store.subscriptions()] == [ENDPOINT]
    assert store.get_trip(upcoming) is not None
