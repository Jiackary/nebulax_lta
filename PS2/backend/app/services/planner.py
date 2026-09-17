"""Her door-to-door step-free plan (capability 1; D8, D11).

Shape: walk → EWL → walk. One persona, one journey, so the rail leg is not a
search — it is Bedok to Outram Park, and the work is in choosing *which exits*
and saying honestly how long it takes.
"""
from __future__ import annotations

from datetime import datetime

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
                                    prefer_sheltered=prefer_sheltered)
    last = walking.choose_entrance(SGH["coord"], SGH["area"],
                                   blocked=blocked.get(DEST_STATION),
                                   prefer_sheltered=prefer_sheltered)
    if not first or not last:
        raise RuntimeError("no step-free walking route to a usable entrance")
    board_exit, walk_in, board_ent = first
    alight_exit, walk_out, alight_ent = last
    if walk_in.snap_m > MAX_ORIGIN_SNAP_M:
        raise RuntimeError("origin is outside the supported Bedok walking area")

    ride = timing.ride_minutes(RAIL_ROUTE, ORIGIN_STATION, DEST_STATION)
    ride_min, ride_spread = ride if ride else (None, None)
    headway = timing.headway_min(RAIL_ROUTE, ORIGIN_STATION, RAIL_DIRECTION, appointment_at)

    walk_in_r = timing.walk_range(walk_in.distance_m, pace)
    walk_out_r = timing.walk_range(walk_out.distance_m, pace)
    wait_r = timing.wait_range(headway)
    ride_r = timing.Range(ride_min or 0, ride_min or 0, ride_min or 0)
    total = walk_in_r + wait_r + ride_r + walk_out_r

    clock = timing.leave_by(appointment_at, total, buffer_min)
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
            "step_free": "yes" if walk_in.steps_used == 0 else "no",
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
            "step_free": "yes",
            "access": access or {
                "board_at": {"exit_code": f"Exit {board_exit}", "status": "unknown"},
                "alight_at": {"exit_code": f"Exit {alight_exit}", "status": "unknown"},
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
            "instruction": _arrival_sentence(walk_out, alight_exit, prefer_sheltered),
            "step_free": "yes" if walk_out.steps_used == 0 else "no",
            "surface_warnings": [],
            "geometry": {"type": "LineString", "coordinates": walk_out.coords},
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
            "step_free": "yes" if (walk_in.steps_used == 0 and walk_out.steps_used == 0) else "no",
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


def _arrival_sentence(walk: walking.Walk, exit_code: str, sheltered: bool) -> str:
    s = (f"Leave by Exit {exit_code} and take the lift to street level. "
         f"Walk {walk.distance_m:.0f} m to {SGH['label']}, {SGH['block']}.")
    if walk.sheltered_pct >= 60:
        s += " Sheltered most of the way."
    return s
