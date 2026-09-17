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


# "NSL - … . EWL - …": one Content bundles several lines (T6). A line code
# followed by a dash starts that line's clause.
LINE_CLAUSE_RE = re.compile(r"(?:^|(?<=[.;:]))\s*([A-Z]{2,4})\s*-\s+")
TOWARDS_RE = re.compile(r"towards\s+([A-Za-z' ]+?)\s*(?:[.,;]|$)", re.I)
# Her westbound ride. The headsign the EWL uses for it.
HER_HEADSIGN = "tuas link"


def line_clauses(content: str) -> list[tuple[str | None, str]]:
    """Split one Content into (line code, text) clauses.

    Text before the first line marker keeps `None` — a bare advisory with no
    line prefix still has to be readable.
    """
    text = content or ""
    marks = list(LINE_CLAUSE_RE.finditer(text))
    if not marks:
        return [(None, text)]
    out = []
    if marks[0].start() > 0:
        out.append((None, text[:marks[0].start()]))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1).upper(), text[m.end():end]))
    return out


def clause_is_hers(clause: str) -> bool:
    """Does this clause describe the direction she travels?

    A clause naming the other headsign is not hers; one naming no direction
    could be either, so it counts (§6: warn rather than miss).
    """
    m = TOWARDS_RE.search(clause)
    if not m:
        return True
    towards = m.group(1).strip().casefold()
    return towards in (HER_HEADSIGN, "both")


def delay_for_line(content: str, line: str) -> tuple[int | None, str | None]:
    """The delay figure stated for *her* line and direction (F10).

    Taking the first figure in the message let an NSL advisory set the delay for
    an EWL trip, and that number drives the push body and the leave-earlier
    advice.
    """
    clauses = line_clauses(content)
    tagged = [c for c in clauses if c[0] is not None]
    for code, text in clauses:
        if code is not None and code != line:
            continue
        if code is None and tagged:
            continue            # untagged preamble, e.g. "1820hrs : "
        if not clause_is_hers(text):
            continue
        delay, basis = parse_delay(text)
        if delay:
            return delay, basis
    return None, None


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
        delay, basis = delay_for_line(m.get("Content", ""), line)
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
