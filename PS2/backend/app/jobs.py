"""Scheduled checks (D3) and the retention sweep (privacy commitment 1).

  20:00 — every trip with an appointment in the next 36 h
  07:00 — every trip with an appointment today
  03:00 — delete trips more than 24 h past their appointment

An outage that starts after the last check is not caught, and the app must not
imply otherwise (§6 limitation 1). That honesty lives in `checks.label`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import store
from .api.push import send_push
from .config import SGT
from .services import notify

log = logging.getLogger("ps2.jobs")


async def run_check(label: str, horizon_hours: int) -> dict:
    now = datetime.now(SGT)
    trips = store.trips_between(now, now + timedelta(hours=horizon_hours))
    subs = store.subscriptions()
    sent = skipped = 0
    for trip in trips:
        payload = await notify.check_trip(trip)
        if not payload:
            continue
        if not store.mark_sent(trip["trip_id"], label, payload["digest"]):
            skipped += 1
            continue
        for sub in subs:
            ok, err = send_push({"endpoint": sub["endpoint"], "keys": sub["keys"]}, payload)
            if ok:
                sent += 1
            else:
                log.warning("push failed: %s", err)
    log.info("check %s: %d trips, %d sent, %d unchanged", label, len(trips), sent, skipped)
    return {"check": label, "trips": len(trips), "sent": sent, "unchanged": skipped}


async def evening_check() -> dict:
    return await run_check("20:00", 36)


async def morning_check() -> dict:
    return await run_check("07:00", 24)


def retention_sweep() -> dict:
    removed = store.sweep()
    log.info("retention sweep removed %d trips", removed)
    return {"removed": removed}


def start() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="Asia/Singapore")
    sched.add_job(evening_check, "cron", hour=20, minute=0, id="evening")
    sched.add_job(morning_check, "cron", hour=7, minute=0, id="morning")
    sched.add_job(retention_sweep, "cron", hour=3, minute=0, id="retention")
    sched.start()
    return sched
