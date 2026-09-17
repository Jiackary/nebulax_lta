"""Scheduled checks (D3) and the retention sweep (privacy commitment 1).

  20:00 — every trip with an appointment tomorrow
  07:00 — every trip with an appointment later today
  hourly — delete trips more than 24 h past their appointment

An outage that starts after the last check is not caught, and the app must not
imply otherwise (§6 limitation 1). That honesty lives in `checks.label`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import store
from .api.push import send_push_async
from .config import SGT
from .services import notify

log = logging.getLogger("ps2.jobs")

EVENING, MORNING = "20:00", "07:00"


def window_for(label: str, now: datetime) -> tuple[datetime, datetime]:
    """The calendar window a check covers, in SGT (D3, F19).

    Rolling hour counts did not match the labels: "07:00 today" used now+24h and
    so swept in tomorrow's 06:30 appointment, and "20:00 the evening before"
    used 36 h and reached 08:00 two days out.
    """
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if label == EVENING:
        start = midnight + timedelta(days=1)
        return start, start + timedelta(days=1) - timedelta(seconds=1)
    return now, midnight + timedelta(days=1) - timedelta(seconds=1)


def check_key(label: str, now: datetime) -> str:
    """The dedupe key. Dated, or Monday's 20:00 run satisfies Wednesday's (F19)."""
    return f"{label}@{now:%Y-%m-%d}"


async def run_check(label: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(SGT)
    start, end = window_for(label, now)
    key = check_key(label, now)
    trips = store.trips_between(start, end)
    subs = store.subscriptions()
    sent = skipped = failed = 0

    for trip in trips:
        try:
            # Scheduled pushes are real deliveries: never the demo scenario (F09).
            payload = await notify.check_trip(trip, allow_simulated=False)
        except Exception:
            # One trip's failure must not end the run for the rest (F18).
            log.exception("check failed for trip %s", trip.get("trip_id"))
            continue
        if not payload:
            continue

        for sub in subs:
            if trip["trip_id"] not in sub["trip_ids"]:
                continue
            # Claimed per endpoint, so one bad subscription cannot cause a
            # re-send to the ones that already worked (F18).
            if not store.claim_send(trip["trip_id"], key, sub["endpoint"],
                                    payload["digest"]):
                skipped += 1
                continue
            ok, err = await send_push_async(
                {"endpoint": sub["endpoint"], "keys": sub["keys"]}, payload)
            if ok:
                sent += 1
                continue
            failed += 1
            if err == "ENDPOINT_GONE":
                # 404/410: the browser threw this subscription away. So do we,
                # rather than failing against it forever (F18).
                log.info("dropping expired push subscription")
                store.delete_subscription(sub["endpoint"], delete_trips=False)
            else:
                store.release_send(trip["trip_id"], key, sub["endpoint"])
                log.warning("push failed: %s", err)

    log.info("check %s: %d trips, %d sent, %d unchanged, %d failed",
             label, len(trips), sent, skipped, failed)
    return {"check": label, "trips": len(trips), "sent": sent,
            "unchanged": skipped, "failed": failed}


async def evening_check() -> dict:
    return await run_check(EVENING)


async def morning_check() -> dict:
    return await run_check(MORNING)


def retention_sweep() -> dict:
    removed = store.sweep()
    log.info("retention sweep removed %d trips, %d subscriptions",
             removed["trips"], removed["subscriptions"])
    return {"removed": removed["trips"], "subscriptions": removed["subscriptions"]}


def start() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="Asia/Singapore")
    sched.add_job(evening_check, "cron", hour=20, minute=0, id="evening")
    sched.add_job(morning_check, "cron", hour=7, minute=0, id="morning")
    # Hourly, and once now: daily at 03:00 let a trip live about 48 h (F20).
    sched.add_job(retention_sweep, "cron", minute=0, id="retention")
    retention_sweep()
    sched.start()
    return sched
