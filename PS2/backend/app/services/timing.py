"""Timing and its uncertainty (I1, D8, PS2_README.md:L248).

The correction that matters: GTFS train ride time is a single fixed value on her
line — 30.67 min across all 698 EW5→EW16 trips, zero spread. So the visible
uncertainty cannot come from the ride. It comes from two places we can defend:

  * **wait** — 0 to one headway, from the measured timetable (2.5 min at 08h
    weekday, 5.0 off-peak at Bedok).
  * **walking pace** — a band around her assumed pace. This is an assumption,
    not a measurement, and §6 limitation 4 requires us to say so.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import SGT
from .. import data

# metres per second: (nominal, slow end, fast end)
PACE = {
    "slow": (0.7, 0.6, 0.85),
    "normal": (1.2, 1.0, 1.4),
}
DAYTYPE_OF_WEEKDAY = {0: "weekday", 1: "weekday", 2: "weekday", 3: "weekday",
                      4: "weekday", 5: "saturday", 6: "sunday_ph"}


@dataclass
class Range:
    """Minutes: what it takes if everything goes well, and if it does not."""
    fast: float
    nominal: float
    slow: float

    def __add__(self, other: "Range") -> "Range":
        return Range(self.fast + other.fast, self.nominal + other.nominal,
                     self.slow + other.slow)


def walk_range(distance_m: float, pace: str) -> Range:
    nominal, slow, fast = PACE.get(pace, PACE["slow"])
    return Range(distance_m / fast / 60, distance_m / nominal / 60, distance_m / slow / 60)


def daytype_of(when: datetime) -> str:
    """Which of the three timetables applies.

    A public holiday runs the Sunday service whatever weekday it lands on, so
    the weekday map alone put her on 2.5 min headways on Christmas Day (F27).
    """
    if when.date().isoformat() in data.public_holidays():
        return "sunday_ph"
    return DAYTYPE_OF_WEEKDAY[when.weekday()]


def _hours(route: str, stop_code: str, direction: str, when: datetime) -> dict:
    table = data.headways().get(route, {}).get(stop_code, {})
    return table.get(daytype_of(when), {}).get(direction, {})


def headway_min(route: str, stop_code: str, direction: str, when: datetime) -> float | None:
    """Measured median gap between departures, in the hour `when` falls in.

    `None` means we have no measurement for that hour. There is deliberately no
    nearest-hour fallback any more: it answered a 03:00 query with the 01:00
    figure, which had the planner promise "a train every 5 min at this hour" on
    a line that shuts around midnight (F27). Use `has_service` to tell "no
    trains then" apart from "no table for this stop at all".
    """
    hours = _hours(route, stop_code, direction, when)
    return hours.get(str(when.hour)) if hours else None


def has_service(route: str, stop_code: str, direction: str,
                when: datetime) -> bool | None:
    """Does anything depart in that hour? `None` when we have no table to say.

    The hourly buckets are built from real departure gaps, so an hour missing
    from a table that has other hours is an hour nothing departed in — before
    the first train, after the last, or between the peaks of a peak-only
    shuttle. Treating that as "unknown headway, assume 5 min" is how a 01:30
    appointment got a plan.
    """
    hours = _hours(route, stop_code, direction, when)
    if not hours:
        return None
    return str(when.hour) in hours


def wait_range(headway: float | None) -> Range:
    """She does not time her arrival to the platform, so the wait is uniform
    across the headway. Nominal is half."""
    if not headway:
        return Range(0.0, 2.5, 5.0)
    return Range(0.0, headway / 2, headway)


def ride_minutes(route: str, origin: str, dest: str) -> tuple[float, float] | None:
    """(median, spread) for a station pair, measured end to end including dwell."""
    pairs = data.ridetimes().get("_pairs", {}).get(route, {})
    row = pairs.get(f"{origin}>{dest}")
    if not row:
        return None
    return row["median"], round(row["max"] - row["min"], 2)


def leave_by(appointment: datetime, total: Range, buffer_min: int) -> dict:
    """Plan against the slow end, so following the advice still arrives in time.

    `leave_by` is the one big number on her screen (API contract §3); the window
    stays visible underneath because a bare point estimate risks the level-3 cap
    on route planning.
    """
    depart = appointment - timedelta(minutes=buffer_min + total.slow)
    depart = depart.replace(second=0, microsecond=0)
    arrive_early = depart + timedelta(minutes=total.fast)
    arrive_late = depart + timedelta(minutes=total.slow)
    return {
        "leave_by": depart.astimezone(SGT),
        "arrive_early": arrive_early.astimezone(SGT),
        "arrive_late": arrive_late.astimezone(SGT),
    }


def basis_sentence(ride: float | None, spread: float | None, headway: float | None,
                   pace: str, walk_m: float) -> str:
    nominal = PACE.get(pace, PACE["slow"])[0]
    bits = []
    if ride is not None:
        # "Scheduled", never "takes": GTFS is a timetable, not a stopwatch (D8).
        if spread == 0:
            bits.append(f"Train ride is a scheduled {ride:.0f} min, fixed by the timetable")
        else:
            bits.append(f"Train ride is a scheduled {ride:.0f} min")
    if headway:
        # "when she boards", not "at this hour": the figure is looked up at the
        # hour she reaches the platform, which is rarely the appointment's (F27).
        bits.append(f"a train every {headway:g} min when she boards, "
                    f"so 0–{headway:g} min of waiting")
    bits.append(f"{walk_m:.0f} m of walking at an assumed {nominal} m/s")
    return ". ".join(b[0].upper() + b[1:] for b in bits) + "."
