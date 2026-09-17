"""TrainServiceAlerts -> advice for her specific journey (D2, D13).

Traps this module exists to absorb:
  T2  `value` is an object, not an array (handled in the adapter).
  T3  Status:1 is not all-clear. On recovery the segment persists with
      Stations:"" while free bus and shuttle stay populated. Test the segments.
  T4  The island-wide free-bus string appears both as "island wide" and
      "island-wide". Match loosely.
  T5  Messages can be test broadcasts prefixed "Test :", and can name line codes
      that are in no documented enum (SWL). Ignore tests; never crash on an
      unknown code.
  T6  Message is newest-first and one Content can bundle several lines.

Delay minutes are parsed with a rule, not a model (D13), and the sentence the
rule fired on is returned as `delay_basis` so a judge can check it.
"""
from __future__ import annotations

import re

from .. import data
from ..config import DEST_STATION, ORIGIN_STATION

DELAY_RE = re.compile(
    r"additional\s+travel(?:ling)?\s+time\s+of\s+(?:about\s+)?(\d+)\s*min", re.I)
TEST_RE = re.compile(r"^\s*test\s*:", re.I)
ISLANDWIDE_RE = re.compile(r"island[\s-]?wide", re.I)

HER_LINE = "EWL"
# Her ride, in the order the westbound train takes them.
HER_STATIONS = [f"EW{n}" for n in range(5, 17)]


def parse_delay(text: str) -> tuple[int | None, str | None]:
    """-> (minutes, the sentence it was read from)."""
    m = DELAY_RE.search(text or "")
    if not m:
        return None, None
    start = text.rfind(".", 0, m.start()) + 1
    end = text.find(".", m.end())
    sentence = text[start: end + 1 if end != -1 else len(text)].strip()
    return int(m.group(1)), sentence


def _segments(value: dict) -> list[dict]:
    """Segments that actually name stations. T3: recovery leaves empty ones."""
    return [s for s in (value.get("AffectedSegments") or [])
            if (s.get("Stations") or "").strip()]


def _messages(value: dict) -> list[dict]:
    return [m for m in (value.get("Message") or [])
            if not TEST_RE.match(m.get("Content", ""))]


def assess(value: dict, observed_at: str) -> dict | None:
    """Return the disruption block if one touches her journey, else None."""
    segments = _segments(value)
    if not segments:
        return None

    mine = []
    for s in segments:
        line = data.canonical_line(s.get("Line", "")) or (s.get("Line") or "").upper()
        stations = [x.strip().upper() for x in (s.get("Stations") or "").split(",") if x.strip()]
        if line == HER_LINE and set(stations) & set(HER_STATIONS):
            mine.append((s, line, stations))
    if not mine:
        return None

    seg, line, stations = mine[0]
    delay, basis = None, None
    for m in _messages(value):
        delay, basis = parse_delay(m.get("Content", ""))
        if delay:
            break

    overlap = [c for c in HER_STATIONS if c in stations]
    free_bus = bool((seg.get("FreePublicBus") or "").strip())
    island = bool(ISLANDWIDE_RE.search(seg.get("FreePublicBus") or ""))
    direction = (seg.get("Direction") or "").strip()
    line_name = data.line_codes()["lines"].get(line, {}).get("name", line)

    headline = f"{line_name} delays"
    if direction and direction.lower() != "both":
        headline += f" towards {direction}"
    if delay:
        detail = (f"About {delay} minutes of extra travelling time between "
                  f"{data.station_by_code()[overlap[0]]['name']} and "
                  f"{data.station_by_code()[overlap[-1]]['name']}.")
    else:
        detail = (f"Delays reported between {data.station_by_code()[overlap[0]]['name']} "
                  f"and {data.station_by_code()[overlap[-1]]['name']}.")

    out = {
        "line": line,
        "severity": "critical" if value.get("Status") == 2 else "warn",
        "headline": headline,
        "detail": detail,
        "delay_min": delay,
        "delay_basis": (f'Parsed from LTA\'s advisory: "{basis}"' if basis else
                        "LTA has not stated a delay figure."),
        "affected_stations": overlap,
        "on_her_route": True,
        "free_bus_available": free_bus,
        "free_bus_islandwide": island,
        "source": value.get("_source", "live"),
        "observed_at": observed_at,
    }
    if out["source"] == "simulated":
        out["simulated_note"] = value.get("_simulated_note")
    return out
