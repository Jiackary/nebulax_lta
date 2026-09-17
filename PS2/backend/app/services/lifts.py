"""Lift outages, matched to the exit they affect (D7, D13).

`v2/FacilitiesMaintenance` describes a lift in free text with no fixed format
(T20). Four live rows on 17 Sep produced ALL CAPS and Title Case, a `(TEL)` line
prefix, and an internal lift with no exit reference at all; `LiftID` gave
`B3L02`, `B1 L01` with a space, and an empty string.

Rules, not a model (D13): the text is formulaic, rules run offline and instantly,
and a judge can check them without paying for anything.

Three outcomes, and the difference matters:
  matched_exit — the exit parsed out is one this station is known to have.
  unmatched    — an exit was named but this station has no such exit. A real
                 failure, but a *detectable* one: we degrade to a station-level
                 warning instead of routing her to a door that may not exist.
  station_only — no exit in the text at all, e.g. an internal concourse-to-
                 platform lift. Correctly not an exit outage.

The feed carries no dates (T8), so this detects, it does not predict (§6
limitation 1).
"""
from __future__ import annotations

import asyncio
import re

from .. import data
from ..config import DEST_STATION, ORIGIN_STATION

# "Exit A", "EXIT A", "Exit 12", "Exits A/B", "Exits 6 & 7", "Exits 6, 7",
# "Exit6" (no space) and "EXIT NO. 6". A leading "(TEL)" is a line prefix, not
# part of the exit, so it is stripped before matching.
#
# The trailing (?![A-Z0-9]) stops a code being taken out of the middle of a word
# — without it "Exit lobby" would parse as exit "LO".
EXIT_SEP = r"(?:\s*(?:/|,|&|\+|\bAND\b)\s*)"
EXIT_RE = re.compile(
    r"\bEXITS?\.?\s*(?:NOS?\.?\s*)?"
    r"([A-Z0-9]{1,2}(?:" + EXIT_SEP + r"[A-Z0-9]{1,2})*)(?![A-Z0-9])",
    re.I)
SPLIT_RE = re.compile(EXIT_SEP, re.I)
LINE_PREFIX_RE = re.compile(r"^\s*\(([A-Z]{2,5})\)\s*")


def parse_exits(lift_desc: str) -> tuple[list[str], str | None]:
    """-> (every exit code named, the line prefix if the text carried one).

    Every code, not the first: a lift serving "Exits 5/6" takes both doors out,
    and keeping only the first is a false negative — the dangerous direction
    (F02).
    """
    text = (lift_desc or "").strip()
    prefix = None
    m = LINE_PREFIX_RE.match(text)
    if m:
        prefix = m.group(1).upper()
        text = text[m.end():]
    found: list[str] = []
    for hit in EXIT_RE.finditer(text):
        for part in SPLIT_RE.split(hit.group(1)):
            code = part.strip().upper()
            if code and code not in found:
                found.append(code)
    return found, prefix


def station_for(station_code: str) -> dict | None:
    """Resolve any line's code for a station to the one physical station.

    `parent_station` unifies 28 interchanges, so a TE11 row and a DT10 row are
    the same place (I3).
    """
    return data.station_by_code().get((station_code or "").strip().upper())


def match_row(row: dict) -> dict:
    """One FacilitiesMaintenance row -> the alert shape of API contract §4."""
    station_code = (row.get("StationCode") or "").strip().upper()
    station = station_for(station_code)
    desc = row.get("LiftDesc") or ""
    exits, prefix = parse_exits(desc)

    station_id = station["station_id"] if station else None
    known = {e["exit_code"] for e in data.exits_by_station().get(station_id, [])}

    # Every exit this station actually has, not just the first (F02).
    matched = [e for e in exits if e in known]
    if not exits:
        resolution, exit_code = "station_only", None
    elif matched:
        resolution = "matched_exit"
        exit_code = matched[0]
    else:
        resolution, exit_code = "unmatched", None

    label = "Lift out of service"
    if resolution == "matched_exit":
        if len(matched) == 1:
            detail = f"Exit {matched[0]}'s lift is under maintenance."
        else:
            names = ", ".join(matched[:-1]) + f" and {matched[-1]}"
            detail = f"The lift serving Exits {names} is under maintenance."
    elif resolution == "unmatched":
        detail = (f"A lift at {station['name'] if station else station_code} is under "
                  f"maintenance. We could not tell which exit it serves.")
    else:
        detail = (f"An internal lift at {station['name'] if station else station_code} "
                  f"is under maintenance.")

    return {
        "station_code": station_code,
        "station_name": station["name"] if station else station_code,
        "station_id": station_id,
        "line": data.canonical_line(row.get("Line", "")) or row.get("Line"),
        "exit_code": f"Exit {exit_code}" if exit_code else None,
        # Every door this outage takes out. `exit_code` stays the first, for the
        # contract's single-exit field; anything deciding where she may walk
        # must read this list instead (F02).
        "blocked_exit_refs": matched,
        "lift_id": (row.get("LiftID") or "").strip() or None,
        "lift_desc": desc,
        "resolution": resolution,
        "parsed_exits": exits,
        "line_prefix": prefix,
        "severity": "warn",
        "label": label,
        "detail": detail,
        "affects_route": False,
        "source": row.get("_source", "live"),
    }


def match_all(rows: list[dict]) -> list[dict]:
    return [match_row(r) for r in rows]


def route_stations() -> set[str]:
    """The station ids her trip actually passes through, via parent_station."""
    out = set()
    for code in (ORIGIN_STATION, DEST_STATION):
        st = station_for(code)
        if st:
            out.add(st["station_id"])
    return out


def annotate_for_route(alerts: list[dict]) -> list[dict]:
    on_route = route_stations()
    for a in alerts:
        a["affects_route"] = a["station_id"] in on_route
    return alerts


def blocked_exits(alerts: list[dict]) -> tuple[dict[str, set[str]], dict]:
    """Exits she must not be sent to, keyed by the station code the planner uses.

    Only `matched_exit` blocks a door. An `unmatched` or `station_only` row
    cannot name a door, so blocking one would be guesswork — it becomes a
    station-level warning instead (§6 limitation 2).
    """
    blocked: dict[str, set[str]] = {}
    for a in alerts:
        if a["resolution"] != "matched_exit" or not a["affects_route"]:
            continue
        refs = a.get("blocked_exit_refs") or [a["exit_code"].replace("Exit ", "")]
        for code in (ORIGIN_STATION, DEST_STATION):
            st = station_for(code)
            if st and st["station_id"] == a["station_id"]:
                blocked.setdefault(code, set()).update(refs)
    return blocked, {}


async def current_alerts(*, allow_simulated: bool = True) -> tuple[list[dict], object]:
    """Live outages (plus any labelled synthetic ones) matched and annotated."""
    from ..scenario import lift_rows
    rows, fetched = await lift_rows(allow_simulated=allow_simulated)
    return annotate_for_route(match_all(rows)), fetched


async def blocked_exits_now() -> tuple[dict, dict]:
    """Async entry point — use this from anything already inside a loop."""
    try:
        alerts, _ = await current_alerts()
    except Exception:                         # upstream down: plan without it
        return {}, {}
    return blocked_exits(alerts)


def blocked_exits_sync() -> tuple[dict, dict]:
    """Planner entry point for sync callers. Never blocks a plan on an upstream.

    Inside a running loop this cannot start another, so it returns empty rather
    than leaving a coroutine un-awaited; async callers must use
    `blocked_exits_now()` instead.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        return {}, {}
    try:
        return blocked_exits(asyncio.run(current_alerts())[0])
    except Exception:
        return {}, {}


def plan_uses_blocked_exit(plan: dict, blocked: dict[str, set[str]]) -> bool:
    """Is the stored plan sending her to a door whose lift is now out?"""
    if not blocked:
        return False
    for leg in plan.get("legs", []):
        for end in ("from", "to"):
            node = leg.get(end) or {}
            code, exit_code = node.get("station_code"), node.get("exit_code")
            if not code or not exit_code:
                continue
            if exit_code.replace("Exit ", "") in blocked.get(code, set()):
                return True
    return False
