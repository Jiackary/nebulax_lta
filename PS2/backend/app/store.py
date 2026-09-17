"""SQLite: her trips and push subscriptions, and nothing else.

The privacy statement (decision record §8) makes promises this module has to
keep. Commitment 1 is the hard one: a trip is deleted 24 hours after its
appointment, and immediately when she removes it or turns notifications off.
`sweep()` is what makes that true, and `jobs.py` runs it daily.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from .config import DB_PATH, SGT

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    trip_id         TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    appointment_at  TEXT NOT NULL,
    origin          TEXT NOT NULL,
    preferences     TEXT NOT NULL,
    plan            TEXT NOT NULL,
    -- The plan as first built, never overwritten. `plan` is the effective plan
    -- for the outages known at the last /status call; keeping the original is
    -- what lets a reroute be undone when the outage clears (F07).
    plan_original   TEXT
);
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint    TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    keys        TEXT NOT NULL,
    trip_ids    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sent (
    trip_id   TEXT NOT NULL,
    check_at  TEXT NOT NULL,
    digest    TEXT NOT NULL,
    PRIMARY KEY (trip_id, check_at)
);
"""


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        # A database created before F07 has no plan_original.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(trips)")}
        if "plan_original" not in cols:
            c.execute("ALTER TABLE trips ADD COLUMN plan_original TEXT")
            c.execute("UPDATE trips SET plan_original = plan WHERE plan_original IS NULL")


def new_trip_id() -> str:
    return "t_" + secrets.token_urlsafe(4).replace("-", "").replace("_", "")[:4]


def save_trip(appointment_at: datetime, origin: dict, preferences: dict, plan: dict,
              plan_original: dict | None = None) -> str:
    trip_id = new_trip_id()
    plan_original = plan_original if plan_original is not None else plan
    with conn() as c:
        c.execute(
            "INSERT INTO trips (trip_id, created_at, appointment_at, origin, preferences,"
            " plan, plan_original) VALUES (?,?,?,?,?,?,?)",
            (trip_id, datetime.now(SGT).isoformat(timespec="seconds"),
             appointment_at.astimezone(SGT).isoformat(timespec="seconds"),
             json.dumps(origin), json.dumps(preferences),
             json.dumps(plan), json.dumps(plan_original)))
    return trip_id


def get_trip(trip_id: str) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM trips WHERE trip_id=?", (trip_id,)).fetchone()
    if not row:
        return None
    return {"trip_id": row["trip_id"],
            "created_at": row["created_at"],
            "appointment_at": row["appointment_at"],
            "origin": json.loads(row["origin"]),
            "preferences": json.loads(row["preferences"]),
            "plan": json.loads(row["plan"]),
            "plan_original": json.loads(row["plan_original"] or row["plan"])}


def update_plan(trip_id: str, plan: dict) -> None:
    with conn() as c:
        c.execute("UPDATE trips SET plan=? WHERE trip_id=?", (json.dumps(plan), trip_id))


def delete_trip(trip_id: str) -> bool:
    with conn() as c:
        n = c.execute("DELETE FROM trips WHERE trip_id=?", (trip_id,)).rowcount
        c.execute("DELETE FROM sent WHERE trip_id=?", (trip_id,))
    return n > 0


def all_trips() -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT trip_id FROM trips").fetchall()
    return [get_trip(r["trip_id"]) for r in rows]


def trips_between(start: datetime, end: datetime) -> list[dict]:
    return [t for t in all_trips()
            if start <= datetime.fromisoformat(t["appointment_at"]) <= end]


def save_subscription(endpoint: str, keys: dict, trip_ids: list[str]) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO push_subs (endpoint, created_at, keys, trip_ids)"
                  " VALUES (?,?,?,?)",
                  (endpoint, datetime.now(SGT).isoformat(timespec="seconds"),
                   json.dumps(keys), json.dumps(trip_ids)))


def subscriptions() -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM push_subs").fetchall()
    return [{"endpoint": r["endpoint"], "keys": json.loads(r["keys"]),
             "trip_ids": json.loads(r["trip_ids"])} for r in rows]


def delete_subscription(endpoint: str) -> dict:
    """Unsubscribing deletes her stored trips too (§8 commitment 1).

    One endpoint only. The `endpoint=None` branch used to delete every
    subscription and every trip linked to them, which any HTTP client could
    reach unauthenticated (F04).
    """
    if not endpoint:
        raise ValueError("delete_subscription requires an endpoint")
    with conn() as c:
        subs = c.execute("SELECT trip_ids FROM push_subs WHERE endpoint=?",
                         (endpoint,)).fetchall()
        c.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))
        trip_ids = {t for r in subs for t in json.loads(r["trip_ids"])}
        for tid in trip_ids:
            c.execute("DELETE FROM trips WHERE trip_id=?", (tid,))
            c.execute("DELETE FROM sent WHERE trip_id=?", (tid,))
    return {"subscriptions_removed": len(subs), "trips_removed": len(trip_ids)}


def sweep(now: datetime | None = None) -> int:
    """Delete trips more than 24 h past their appointment (§8 commitment 1)."""
    now = now or datetime.now(SGT)
    cutoff = now - timedelta(hours=24)
    removed = 0
    for t in all_trips():
        if datetime.fromisoformat(t["appointment_at"]) < cutoff:
            delete_trip(t["trip_id"])
            removed += 1
    return removed


def mark_sent(trip_id: str, check_at: str, digest: str) -> bool:
    """True if this is new — stops a check re-sending the same warning."""
    with conn() as c:
        row = c.execute("SELECT digest FROM sent WHERE trip_id=? AND check_at=?",
                        (trip_id, check_at)).fetchone()
        if row and row["digest"] == digest:
            return False
        c.execute("INSERT OR REPLACE INTO sent (trip_id, check_at, digest) VALUES (?,?,?)",
                  (trip_id, check_at, digest))
    return True


def was_sent(trip_id: str, check_at: str, digest: str) -> bool:
    """Whether this check already delivered an unchanged warning."""
    with conn() as c:
        row = c.execute("SELECT digest FROM sent WHERE trip_id=? AND check_at=?",
                        (trip_id, check_at)).fetchone()
    return bool(row and row["digest"] == digest)
