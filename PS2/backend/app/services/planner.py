"""Her door-to-door step-free plan (capability 1; D8, D11).

Shape: walk → EWL → walk. One persona, one journey, so the rail leg is not a
search — it is Bedok to Outram Park, and the work is in choosing *which exits*
and saying honestly how long it takes.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import data
from ..config import ATTRIBUTION, DEST_STATION, ORIGIN_STATION, SGH, SGT
from . import timing, walking

RAIL_ROUTE = "EWL"
RAIL_DIRECTION = "1"          # westbound, headsign "Tuas Link"
DEFAULT_BUFFER_MIN = 15
MAX_ORIGIN_SNAP_M = 100


def _station(code: str) -> dict:
    return data.station_by_code()[code]


def _leg_point(code: str, exit_code: str | None, coord: list[float]) -> dict:
    st = _station(code)
    out = {"name": st["name"], "station_code": code, "coord": coord}
    if exit_code:
        out["exit_code"] = f"Exit {exit_code}"
    return out


def plan_trip(origin: dict, appointment_at: datetime, *, pace: str = "slow",
              buffer_min: int = DEFAULT_BUFFER_MIN, prefer_sheltered: bool = False,
              blocked_exits: dict[str, set[str]] | None = None,
              access: dict | None = None) -> dict:
    """Build the TripPlan of API contract §3.

    `blocked_exits` maps a station code to exits she must not be sent to — that
    is how a lift outage changes the route (D7). `access` carries the lift status
    the matcher resolved, so the leg can name the lift it expects her to use.
    """
    blocked = blocked_exits or {}
    wg = data.walk_graph()
    origin_coord = origin["coord"]
    area_from = wg.area_of(*origin_coord)
    if area_from != "bedok":
        raise RuntimeError("origin is outside the supported Bedok walking area")

    first = walking.choose_entrance(origin_coord, area_from,
                                    blocked=blocked.get(ORIGIN_STATION),
                                    prefer_sheltered=prefer_sheltered,
                                    station_id=_station(ORIGIN_STATION)["station_id"])
    last = walking.choose_entrance(SGH["coord"], SGH["area"],
                                   blocked=blocked.get(DEST_STATION),
                                   prefer_sheltered=prefer_sheltered,
                                   station_id=_station(DEST_STATION)["station_id"])
    if not first or not last:
        raise RuntimeError("no step-free walking route to a usable entrance")
    board_exit, walk_in, board_ent = first
    alight_exit, walk_out, alight_ent = last
    if walk_in.snap_m > MAX_ORIGIN_SNAP_M:
        raise RuntimeError("origin is outside the supported Bedok walking area")

    # `step_free` is a claim, and "unknown" is not "no" (contract §6 limitation 5,
    # D11). A walk with no staircase edge over a door nobody has tagged is not
    # known to be step-free, so it says unknown rather than yes (F11).
    board_known = board_ent.get("wheelchair") == "yes"
    alight_known = alight_ent.get("wheelchair") == "yes"

    def _step_free(walk, entrance_known: bool) -> str:
        if walk.steps_used:
            return "no"
        return "yes" if entrance_known else "unknown"

    ride = timing.ride_minutes(RAIL_ROUTE, ORIGIN_STATION, DEST_STATION)
    ride_min, ride_spread = ride if ride else (None, None)

    walk_in_r = timing.walk_range(walk_in.distance_m, pace)
    walk_out_r = timing.walk_range(walk_out.distance_m, pace)
    ride_r = timing.Range(ride_min or 0, ride_min or 0, ride_min or 0)

    def schedule(headway: float | None):
        """Everything downstream of the headway, plus when she reaches the platform."""
        wait_r = timing.wait_range(headway)
        total = walk_in_r + wait_r + ride_r + walk_out_r
        clock = timing.leave_by(appointment_at, total, buffer_min)
        # She walks in before she waits, and `leave_by` plans against the slow
        # end, so the slow walk is the hour to ask about.
        board_at = clock["leave_by"] + timedelta(minutes=walk_in_r.slow)
        return wait_r, total, clock, board_at

    # The headway that governs her wait is the one at the hour she reaches the
    # platform, not the hour of her appointment — an hour apart on this trip, and
    # 2.5 min against 5.0 across the 08h boundary (F27). Locate the boarding time
    # with a first pass, then price the wait at that hour. One pass is enough:
    # the shift is minutes, and the second lookup is what the plan is built from.
    _, _, _, board_at = schedule(
        timing.headway_min(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, appointment_at))
    headway = timing.headway_min(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, board_at)
    wait_r, total, clock, board_at = schedule(headway)

    # Refusing beats inventing a train. The old nearest-hour fallback planned a
    # 01:30 appointment as "leave 00:20" on a line that had stopped running.
    if timing.has_service(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, board_at) is False:
        raise RuntimeError(
            f"no {data.line_codes()['lines'][RAIL_ROUTE]['name']} service from "
            f"{_station(ORIGIN_STATION)['name']} around "
            f"{board_at.astimezone(SGT):%H:%M} — the line is not running then")

    total_walk_m = walk_in.distance_m + walk_out.distance_m
    total_cov_m = walk_in.covered_m + walk_out.covered_m

    stops = data.ridetimes()[RAIL_ROUTE][RAIL_DIRECTION]["stops"]
    headsign = data.ridetimes()[RAIL_ROUTE][RAIL_DIRECTION]["headsign"]
    n_stops = stops.index(DEST_STATION) - stops.index(ORIGIN_STATION)
    line = data.line_codes()["lines"][RAIL_ROUTE]

    legs = [
        {
            "leg_id": "l1", "mode": "walk",
            "from": {"name": origin.get("label", "Home"), "coord": origin_coord},
            "to": _leg_point(ORIGIN_STATION, board_exit, board_ent["coord"]),
            "duration_min": round(walk_in_r.nominal),
            "distance_m": round(walk_in.distance_m),
            "covered_m": round(walk_in.covered_m),
            "instruction": _walk_sentence(walk_in, _station(ORIGIN_STATION)["name"],
                                          board_exit, prefer_sheltered),
            "step_free": _step_free(walk_in, board_known),
            "surface_warnings": [],
            "geometry": {"type": "LineString", "coordinates": walk_in.coords},
        },
        {
            "leg_id": "l2", "mode": "rail",
            "from": _leg_point(ORIGIN_STATION, board_exit, _station(ORIGIN_STATION)["coord"]),
            "to": _leg_point(DEST_STATION, alight_exit, _station(DEST_STATION)["coord"]),
            "line": {"code": RAIL_ROUTE, "name": line["name"], "colour": line["colour"]},
            "duration_min": round(ride_min) if ride_min else None,
            "headway_min": headway,
            "instruction": f"Take the {line['name']} towards {headsign}. {n_stops} stops.",
            # Station interiors are not mapped (§6 limitation 8), so this can be
            # no stronger than what is known about the two doors (F11).
            "step_free": "yes" if (board_known and alight_known) else "unknown",
            "access": access or {
                "board_at": {"exit_code": f"Exit {board_exit}",
                             "status": "yes" if board_known else "unknown"},
                "alight_at": {"exit_code": f"Exit {alight_exit}",
                              "status": "yes" if alight_known else "unknown"},
            },
            "geometry": {"type": "LineString",
                         "coordinates": [_station(ORIGIN_STATION)["coord"],
                                         _station(DEST_STATION)["coord"]]},
        },
        {
            "leg_id": "l3", "mode": "walk",
            "from": _leg_point(DEST_STATION, alight_exit, alight_ent["coord"]),
            "to": {"name": f"{SGH['label']}, {SGH['block']}", "coord": SGH["coord"]},
            "duration_min": round(walk_out_r.nominal),
            "distance_m": round(walk_out.distance_m),
            "covered_m": round(walk_out.covered_m),
            "instruction": _arrival_sentence(walk_out, alight_exit, prefer_sheltered,
                                             alight_known),
            "step_free": _step_free(walk_out, alight_known),
            "surface_warnings": [],
            # `walk_out` is routed SGH -> exit, but this leg runs exit -> SGH.
            # A frontend animating progress along the line ran it backwards (F33).
            "geometry": {"type": "LineString",
                         "coordinates": list(reversed(walk_out.coords))},
        },
    ]

    lons = [c[0] for leg in legs for c in leg["geometry"]["coordinates"]]
    lats = [c[1] for leg in legs for c in leg["geometry"]["coordinates"]]

    return {
        "appointment_at": appointment_at.astimezone(SGT).isoformat(timespec="seconds"),
        "summary": {
            "leave_by": clock["leave_by"].isoformat(timespec="seconds"),
            "leave_by_label": f"Leave at {clock['leave_by']:%H:%M}",
            "arrival_window": [clock["arrive_early"].isoformat(timespec="seconds"),
                               clock["arrive_late"].isoformat(timespec="seconds")],
            "arrival_label": f"arrive {clock['arrive_early']:%H:%M}–{clock['arrive_late']:%H:%M}",
            "appointment_label": f"appointment {appointment_at.astimezone(SGT):%H:%M}",
            "buffer_min": buffer_min,
            "duration_min": round(total.nominal),
            "range_min": [round(total.fast), round(total.slow)],
            "timing_basis": timing.basis_sentence(ride_min, ride_spread, headway,
                                                  pace, total_walk_m),
            "step_free": ("no" if (walk_in.steps_used or walk_out.steps_used)
                          else "yes" if (board_known and alight_known) else "unknown"),
            "sheltered_pct": round(100 * total_cov_m / total_walk_m) if total_walk_m else 0,
            "walk_distance_m": round(total_walk_m),
        },
        "legs": legs,
        "map": {
            "bbox": [round(min(lons), 6), round(min(lats), 6),
                     round(max(lons), 6), round(max(lats), 6)],
            "geometry": {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"leg_id": leg["leg_id"], "mode": leg["mode"]},
                 "geometry": leg["geometry"]} for leg in legs]},
        },
        "attribution": ATTRIBUTION,
    }


def _walk_sentence(walk: walking.Walk, station: str, exit_code: str, sheltered: bool) -> str:
    s = f"Walk {walk.distance_m:.0f} m to {station} MRT Exit {exit_code}."
    if walk.sheltered_pct >= 60:
        s += " Sheltered most of the way."
    elif sheltered and walk.sheltered_pct > 0:
        s += f" About {walk.sheltered_pct}% of it is covered."
    return s


def _arrival_sentence(walk: walking.Walk, exit_code: str, sheltered: bool,
                      entrance_known: bool = True) -> str:
    # Only promise a lift where the door is tagged accessible (F11).
    lift = ("and take the lift to street level" if entrance_known
            else "and look for the lift to street level — we could not confirm "
                 "this exit has one")
    s = (f"Leave by Exit {exit_code} {lift}. "
         f"Walk {walk.distance_m:.0f} m to {SGH['label']}, {SGH['block']}.")
    if walk.sheltered_pct >= 60:
        s += " Sheltered most of the way."
    return s
