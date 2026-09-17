import asyncio

from app import jobs
from app.api import push


def _async(fn):
    """`send_push` is now awaited via `send_push_async` (F14)."""
    async def stub(*args, **kwargs):
        return fn(*args, **kwargs)
    return stub


def _trip(trip_id="t_one"):
    return {"trip_id": trip_id, "appointment_at": "2026-09-19T10:30:00+08:00"}


def _payload(trip_id="t_one"):
    return {"trip_id": trip_id, "digest": "digest", "title": "Warning", "body": "Body"}


def test_scheduled_check_only_sends_to_subscriptions_for_that_trip(monkeypatch):
    sent_to = []
    marked = []

    monkeypatch.setattr(jobs.store, "trips_between", lambda *_: [_trip()])
    monkeypatch.setattr(
        jobs.store,
        "subscriptions",
        lambda: [
            {"endpoint": "matching", "keys": {}, "trip_ids": ["t_one"]},
            {"endpoint": "other", "keys": {}, "trip_ids": ["t_two"]},
        ],
    )

    async def check_trip(_, **kwargs):
        return _payload()

    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)
    monkeypatch.setattr(jobs.store, "was_sent", lambda *_: False, raising=False)
    monkeypatch.setattr(
        jobs,
        "send_push_async",
        _async(lambda subscription, _: (sent_to.append(subscription["endpoint"]) or True, None)),
    )
    monkeypatch.setattr(
        jobs.store,
        "mark_sent",
        lambda *args: (marked.append(args) or True),
    )

    asyncio.run(jobs.run_check("20:00", 36))

    assert sent_to == ["matching"]
    assert len(marked) == 1


def test_failed_delivery_is_not_marked_sent(monkeypatch):
    marked = []

    monkeypatch.setattr(jobs.store, "trips_between", lambda *_: [_trip()])
    monkeypatch.setattr(
        jobs.store,
        "subscriptions",
        lambda: [{"endpoint": "matching", "keys": {}, "trip_ids": ["t_one"]}],
    )

    async def check_trip(_, **kwargs):
        return _payload()

    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)
    monkeypatch.setattr(jobs.store, "was_sent", lambda *_: False, raising=False)
    monkeypatch.setattr(jobs, "send_push_async", _async(lambda *_: (False, "temporary failure")))
    monkeypatch.setattr(
        jobs.store,
        "mark_sent",
        lambda *args: (marked.append(args) or True),
    )

    asyncio.run(jobs.run_check("20:00", 36))

    assert marked == []


def test_partial_delivery_failure_is_not_marked_sent(monkeypatch):
    marked = []
    monkeypatch.setattr(jobs.store, "trips_between", lambda *_: [_trip()])
    monkeypatch.setattr(
        jobs.store,
        "subscriptions",
        lambda: [
            {"endpoint": "works", "keys": {}, "trip_ids": ["t_one"]},
            {"endpoint": "fails", "keys": {}, "trip_ids": ["t_one"]},
        ],
    )

    async def check_trip(_, **kwargs):
        return _payload()

    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)
    monkeypatch.setattr(jobs.store, "was_sent", lambda *_: False, raising=False)
    monkeypatch.setattr(
        jobs,
        "send_push_async",
        _async(lambda subscription, _: (subscription["endpoint"] == "works", "temporary failure")),
    )
    monkeypatch.setattr(
        jobs.store,
        "mark_sent",
        lambda *args: (marked.append(args) or True),
    )

    asyncio.run(jobs.run_check("20:00", 36))

    assert marked == []


def test_unchanged_warning_is_not_sent_again(monkeypatch):
    sent_to = []
    monkeypatch.setattr(jobs.store, "trips_between", lambda *_: [_trip()])
    monkeypatch.setattr(
        jobs.store,
        "subscriptions",
        lambda: [{"endpoint": "matching", "keys": {}, "trip_ids": ["t_one"]}],
    )

    async def check_trip(_, **kwargs):
        return _payload()

    monkeypatch.setattr(jobs.notify, "check_trip", check_trip)
    monkeypatch.setattr(jobs.store, "was_sent", lambda *_: True, raising=False)
    monkeypatch.setattr(
        jobs,
        "send_push_async",
        _async(lambda subscription, _: (sent_to.append(subscription["endpoint"]) or True, None)),
    )

    result = asyncio.run(jobs.run_check("20:00", 36))

    assert sent_to == []
    assert result["unchanged"] == 1


def test_manual_push_only_sends_to_subscriptions_for_selected_trip(monkeypatch):
    sent_to = []
    monkeypatch.setattr(push.store, "get_trip", lambda _: _trip())
    monkeypatch.setattr(
        push.store,
        "subscriptions",
        lambda: [
            {"endpoint": "matching", "keys": {}, "trip_ids": ["t_one"]},
            {"endpoint": "other", "keys": {}, "trip_ids": ["t_two"]},
        ],
    )

    async def check_trip(_, **kwargs):
        return _payload()

    monkeypatch.setattr(push.notify, "check_trip", check_trip)
    monkeypatch.setattr(
        push,
        "send_push_async",
        _async(lambda subscription, _: (sent_to.append(subscription["endpoint"]) or True, None)),
    )

    result = asyncio.run(push.push_test("t_one"))

    assert sent_to == ["matching"]
    assert result["subscriptions"] == 1
