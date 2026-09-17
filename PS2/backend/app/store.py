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
-- One row per (trip, dated check, endpoint). Marking per trip was
-- all-or-nothing, so one failing subscription re-sent to the working ones on a
-- later run (F18); and the key carried no date, so Monday's 20:00 run could
-- satisfy Wednesday's evening-before warning (F19).
CREATE TABLE IF NOT EXISTS sent (
    trip_id   TEXT NOT NULL,
    check_at  TEXT NOT NULL,
    endpoint  TEXT NOT NULL DEFAULT '',
    digest    TEXT NOT NULL,
    PRIMARY KEY (trip_id, check_at, endpoint)
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
        # A database created before F18 keys `sent` per trip, not per endpoint.
        sent_cols = {r["name"] for r in c.execute("PRAGMA table_info(sent)")}
        if sent_cols and "endpoint" not in sent_cols:
            c.execute("ALTER TABLE sent RENAME TO sent_old")
            c.executescript(SCHEMA)
            c.execute("INSERT INTO sent (trip_id, check_at, endpoint, digest)"
                      " SELECT trip_id, check_at, '', digest FROM sent_old")
            c.execute("DROP TABLE sent_old")


def new_trip_id() -> str:
    """A trip id is the only thing protecting her home coordinate.

    It used to be 4 characters — about 14.8M values, and roughly 0.03% came out
    as 3 — while GET, DELETE, status and offline need nothing else (F30).
    """
    return "t_" + secrets.token_urlsafe(16)


def save_trip(appointment_at: datetime, origin: dict, preferences: dict, plan: dict,
              plan_original: dict | None = None) -> str:
    plan_original = plan_original if plan_original is not None else plan
    for _ in range(5):                        # retry a collision rather than 500
        trip_id = new_trip_id()
        try:
            with conn() as c:
                c.execute(
                    "INSERT INTO trips (trip_id, created_at, appointment_at, origin,"
                    " preferences, plan, plan_original) VALUES (?,?,?,?,?,?,?)",
                    (trip_id, datetime.now(SGT).isoformat(timespec="seconds"),
                     appointment_at.astimezone(SGT).isoformat(timespec="seconds"),
                     json.dumps(origin), json.dumps(preferences),
                     json.dumps(plan), json.dumps(plan_original)))
            return trip_id
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("could not allocate a trip id")


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
    """Upsert, merging `trip_ids` rather than replacing them.

    INSERT OR REPLACE overwrote the list, so re-subscribing for trip B silently
    unlinked trip A: A got no warnings and `DELETE /push/subscribe` left it on
    the server, against privacy commitment 1 (F31).
    """
    with conn() as c:
        row = c.execute("SELECT trip_ids FROM push_subs WHERE endpoint=?",
                        (endpoint,)).fetchone()
        merged = list(json.loads(row["trip_ids"])) if row else []
        for tid in trip_ids:
            if tid not in merged:
                merged.append(tid)
        c.execute("INSERT OR REPLACE INTO push_subs (endpoint, created_at, keys, trip_ids)"
                  " VALUES (?,?,?,?)",
                  (endpoint, datetime.now(SGT).isoformat(timespec="seconds"),
                   json.dumps(keys), json.dumps(merged)))


def subscriptions() -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM push_subs").fetchall()
    return [{"endpoint": r["endpoint"], "keys": json.loads(r["keys"]),
             "trip_ids": json.loads(r["trip_ids"])} for r in rows]


def delete_subscription(endpoint: str, delete_trips: bool = True) -> dict:
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
        if delete_trips:
            for tid in trip_ids:
                c.execute("DELETE FROM trips WHERE trip_id=?", (tid,))
                c.execute("DELETE FROM sent WHERE trip_id=?", (tid,))
        else:
            # Pruning an expired endpoint (404/410) must not delete her trips.
            trip_ids = set()
            c.execute("DELETE FROM sent WHERE endpoint=?", (endpoint,))
    return {"subscriptions_removed": len(subs), "trips_removed": len(trip_ids)}


def sweep(now: datetime | None = None) -> dict:
    """Delete trips more than 24 h past their appointment (§8 commitment 1).

    Run hourly and at startup. Daily at 03:00 meant a 03:30 appointment survived
    the next sweep at 23.5 h and only went at 47.5 h — about 48 h, not the 24
    promised (F20). Subscriptions whose trips are all gone go too; they were
    never swept and kept dangling trip_ids.
    """
    now = now or datetime.now(SGT)
    cutoff = now - timedelta(hours=24)
    removed = 0
    for t in all_trips():
        if datetime.fromisoformat(t["appointment_at"]) < cutoff:
            delete_trip(t["trip_id"])
            removed += 1

    live = {t["trip_id"] for t in all_trips()}
    subs_removed = 0
    with conn() as c:
        for row in c.execute("SELECT endpoint, trip_ids FROM push_subs").fetchall():
            linked = json.loads(row["trip_ids"])
            if linked and not (set(linked) & live):
                c.execute("DELETE FROM push_subs WHERE endpoint=?", (row["endpoint"],))
                subs_removed += 1
    return {"trips": removed, "subscriptions": subs_removed}


def claim_send(trip_id: str, check_at: str, endpoint: str, digest: str) -> bool:
    """Claim one delivery. True if this caller won it and should send.

    Atomic, so two uvicorn workers running the same cron minute cannot both
    send. `check_at` carries the date, and the claim is per endpoint (F18, F19).
    """
    with conn() as c:
        existing = c.execute(
            "SELECT digest FROM sent WHERE trip_id=? AND check_at=? AND endpoint=?",
            (trip_id, check_at, endpoint)).fetchone()
        if existing and existing["digest"] == digest:
            return False
        if existing:
            c.execute("DELETE FROM sent WHERE trip_id=? AND check_at=? AND endpoint=?",
                      (trip_id, check_at, endpoint))
        cur = c.execute(
            "INSERT OR IGNORE INTO sent (trip_id, check_at, endpoint, digest)"
            " VALUES (?,?,?,?)", (trip_id, check_at, endpoint, digest))
        return cur.rowcount > 0


def release_send(trip_id: str, check_at: str, endpoint: str) -> None:
    """Undo a claim whose delivery failed, so a later run retries it."""
    with conn() as c:
        c.execute("DELETE FROM sent WHERE trip_id=? AND check_at=? AND endpoint=?",
                  (trip_id, check_at, endpoint))


def was_sent(trip_id: str, check_at: str, digest: str, endpoint: str = "") -> bool:
    """Whether this check already delivered an unchanged warning."""
    with conn() as c:
        row = c.execute(
            "SELECT digest FROM sent WHERE trip_id=? AND check_at=? AND endpoint=?",
            (trip_id, check_at, endpoint)).fetchone()
    return bool(row and row["digest"] == digest)
