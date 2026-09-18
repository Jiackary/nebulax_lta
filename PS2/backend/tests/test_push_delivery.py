"""Scheduled delivery, against the real SQLite dedupe.

These used to stub `was_sent`/`mark_sent`, so the dedupe logic itself was never
exercised — which is how the duplicate-push and dateless-key bugs (F18, F19)
survived a passing suite. Only the network call is stubbed now.
"""
import asyncio
from datetime import datetime, timedelta

from app import jobs, store
from app.api import push
from app.config import SGT

ENDPOINT = "https://fcm.googleapis.com/fcm/send/one"
OTHER = "https://web.push.apple.com/two"


def _async(fn):
    """`send_push` is awaited via `send_push_async` (F14)."""
    async def stub(*args, **kwargs):
        return fn(*args, **kwargs)
    return stub


def _payload(trip_id="t_one"):
    return {"trip_id": trip_id, "digest": "digest", "title": "Warning", "body": "Body"}


def _a_trip(when=None):
    """A real stored trip, appointment tomorrow so the 20:00 window covers it."""
    when = when or (datetime.now(SGT) + timedelta(days=1)).replace(
        hour=10, minute=30, second=0, microsecond=0)
    return store.save_trip(when, {"label": "Home", "coord": [103.93057, 1.324782]},
                           {}, {"summary": {}, "legs": []})


def _stub_check(monkeypatch, trip_id):
    async def check_trip(trip, **kwargs):
        return _payload(trip["trip_id"]) if trip["trip_id"] == trip_id else None
    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)


def test_scheduled_check_only_sends_to_subscriptions_for_that_trip(monkeypatch):
    trip_id, other_id = _a_trip(), _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    store.save_subscription(OTHER, {}, [other_id])
    _stub_check(monkeypatch, trip_id)
    sent_to = []
    monkeypatch.setattr(jobs, "send_push_async", _async(
        lambda sub, _: (sent_to.append(sub["endpoint"]) or True, None)))

    asyncio.run(jobs.run_check(jobs.EVENING))

    assert sent_to == [ENDPOINT]


def test_failed_delivery_is_retried_by_a_later_run(monkeypatch):
    trip_id = _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    _stub_check(monkeypatch, trip_id)
    attempts = []
    monkeypatch.setattr(jobs, "send_push_async", _async(
        lambda sub, _: (attempts.append(sub["endpoint"]) and False, "PUSH_FAILED")))

    asyncio.run(jobs.run_check(jobs.EVENING))
    asyncio.run(jobs.run_check(jobs.EVENING))

    assert len(attempts) == 2, "a failed claim must be released for the next run"


def test_a_partial_failure_does_not_resend_to_the_ones_that_worked(monkeypatch):
    """The F18 duplicate: marking was per trip, so one bad subscription meant
    the digest was never recorded and the working phone got it again."""
    trip_id = _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    store.save_subscription(OTHER, {}, [trip_id])
    _stub_check(monkeypatch, trip_id)
    delivered = []

    def send(sub, _payload):
        if sub["endpoint"] == ENDPOINT:
            delivered.append(sub["endpoint"])
            return True, None
        return False, "PUSH_FAILED"

    monkeypatch.setattr(jobs, "send_push_async", _async(send))

    asyncio.run(jobs.run_check(jobs.EVENING))
    asyncio.run(jobs.run_check(jobs.EVENING))
    asyncio.run(jobs.run_check(jobs.EVENING))

    assert delivered == [ENDPOINT], "the working subscription was pushed to more than once"


def test_unchanged_warning_is_not_sent_again(monkeypatch):
    trip_id = _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    _stub_check(monkeypatch, trip_id)
    sent_to = []
    monkeypatch.setattr(jobs, "send_push_async", _async(
        lambda sub, _: (sent_to.append(sub["endpoint"]) or True, None)))

    first = asyncio.run(jobs.run_check(jobs.EVENING))
    second = asyncio.run(jobs.run_check(jobs.EVENING))

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["unchanged"] == 1
    assert sent_to == [ENDPOINT]


def test_an_expired_subscription_is_dropped(monkeypatch):
    """404/410 endpoints were never pruned and failed forever."""
    trip_id = _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    _stub_check(monkeypatch, trip_id)
    monkeypatch.setattr(jobs, "send_push_async",
                        _async(lambda *_: (False, "ENDPOINT_GONE")))

    asyncio.run(jobs.run_check(jobs.EVENING))

    assert store.subscriptions() == []
    assert store.get_trip(trip_id) is not None, "pruning must not delete her trip"


def test_one_failing_trip_does_not_end_the_run(monkeypatch):
    good_id, bad_id = _a_trip(), _a_trip()
    store.save_subscription(ENDPOINT, {}, [good_id, bad_id])
    sent_to = []

    async def check_trip(trip, **kwargs):
        if trip["trip_id"] == bad_id:
            raise RuntimeError("upstream down")
        return _payload(trip["trip_id"])

    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)
    monkeypatch.setattr(jobs, "send_push_async", _async(
        lambda sub, p: (sent_to.append(p["trip_id"]) or True, None)))

    asyncio.run(jobs.run_check(jobs.EVENING))

    assert good_id in sent_to


def test_manual_push_only_sends_to_subscriptions_for_selected_trip(monkeypatch):
    trip_id, other_id = _a_trip(), _a_trip()
    store.save_subscription(ENDPOINT, {}, [trip_id])
    store.save_subscription(OTHER, {}, [other_id])
    sent_to = []

    async def check_trip(trip, **kwargs):
        return _payload(trip["trip_id"])

    monkeypatch.setattr(push.notify, "check_trip", check_trip)
    monkeypatch.setattr(push, "send_push_async", _async(
        lambda sub, _: (sent_to.append(sub["endpoint"]) or True, None)))

    result = asyncio.run(push.push_test(trip_id))

    assert sent_to == [ENDPOINT]
    assert result["subscriptions"] == 1


# --- F19: the check windows and the dated dedupe key ------------------------

def test_the_evening_check_covers_tomorrow_only():
    now = datetime(2026, 9, 21, 20, 0, tzinfo=SGT)          # Monday evening

    start, end = jobs.window_for(jobs.EVENING, now)

    assert start == datetime(2026, 9, 22, 0, 0, tzinfo=SGT)
    assert end < datetime(2026, 9, 23, 0, 0, tzinfo=SGT)


def test_the_evening_check_does_not_reach_two_days_ahead():
    """36 h from Monday 20:00 reached Wednesday 08:00, so a Wednesday 07:30
    appointment got its warning two evenings early."""
    now = datetime(2026, 9, 21, 20, 0, tzinfo=SGT)
    wednesday_0730 = datetime(2026, 9, 23, 7, 30, tzinfo=SGT)

    start, end = jobs.window_for(jobs.EVENING, now)

    assert not (start <= wednesday_0730 <= end)


def test_the_morning_check_stops_at_midnight():
    """now+24h swept in tomorrow's 06:30 appointment."""
    now = datetime(2026, 9, 21, 7, 0, tzinfo=SGT)
    tomorrow_0630 = datetime(2026, 9, 22, 6, 30, tzinfo=SGT)

    start, end = jobs.window_for(jobs.MORNING, now)

    assert not (start <= tomorrow_0630 <= end)
    assert start <= datetime(2026, 9, 21, 10, 30, tzinfo=SGT) <= end


def test_the_dedupe_key_is_dated():
    monday = datetime(2026, 9, 21, 20, 0, tzinfo=SGT)
    tuesday = datetime(2026, 9, 22, 20, 0, tzinfo=SGT)

    assert jobs.check_key(jobs.EVENING, monday) != jobs.check_key(jobs.EVENING, tuesday)


def test_the_real_evening_before_push_is_not_skipped(monkeypatch):
    """Monday's 20:00 run used to satisfy the (trip, "20:00") key, so Tuesday's
    run — the actual evening before — found it already sent and skipped it."""
    wednesday = datetime(2026, 9, 23, 7, 30, tzinfo=SGT)
    trip_id = _a_trip(wednesday)
    store.save_subscription(ENDPOINT, {}, [trip_id])
    _stub_check(monkeypatch, trip_id)
    sent_on = []

    monkeypatch.setattr(jobs, "send_push_async", _async(
        lambda sub, _: (sent_on.append("sent") or True, None)))

    asyncio.run(jobs.run_check(jobs.EVENING, now=datetime(2026, 9, 21, 20, 0, tzinfo=SGT)))
    asyncio.run(jobs.run_check(jobs.EVENING, now=datetime(2026, 9, 22, 20, 0, tzinfo=SGT)))

    assert len(sent_on) == 1, "exactly one evening-before push, on Tuesday"
