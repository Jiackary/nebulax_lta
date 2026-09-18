#!/usr/bin/env python3
"""Check the step-free claim, and print it beside an independent route (D11).

The claim, stated narrowly so it can be falsified:

  No walking leg of her planned trip uses an OSM-mapped staircase, and every
  station entrance or exit the plan sends her through is either tagged
  `wheelchair=yes` in OSM or has a lift that `v2/FacilitiesMaintenance` does not
  report as out of service.

What the claim does NOT cover: station interiors. OSM does not model the inside
of Singapore's MRT stations, so the route between the platform and the exit is
not checked by anything here (§6 limitation 8).

The comparison route comes from OneMap, which routes on its own data and knows
nothing about our step exclusions — so it is a real second opinion, not our own
graph with a flag flipped.

    python scripts/verify_stepfree.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import data                                          # noqa: E402
from app.config import HOME_DEFAULT, SGH, SGT                 # noqa: E402
from app.services import lifts as lift_service                # noqa: E402
from app.services import planner, walking                     # noqa: E402
from app.sources import onemap                                # noqa: E402

PASS, FAIL = "PASS", "FAIL"


def check_no_steps(plan: dict) -> tuple[str, list[str]]:
    """Every walk leg, edge by edge. A pair we cannot resolve to a graph edge is
    a FAIL, not a skip: an unresolved pair is an unchecked pair, and silently
    dropping it is what let a real staircase pass by nudging a coordinate 1 cm.
    """
    notes, verdict = [], PASS
    wg = data.walk_graph()
    index = {tuple(v): k for k, v in wg.nodes.items()}
    legs_seen = 0
    for leg in plan["legs"]:
        if leg["mode"] != "walk":
            continue
        legs_seen += 1
        coords = leg["geometry"]["coordinates"]
        used_steps = unresolved = 0
        pairs = list(zip(coords, coords[1:]))
        for a, b in pairs:
            u, v = index.get(tuple(a)), index.get(tuple(b))
            edge = wg.all_ways.get_edge_data(u, v) if (u is not None and v is not None) else None
            if edge is None:
                unresolved += 1
                continue
            if edge.get("steps"):
                used_steps += 1
        notes.append(f"    {leg['leg_id']}: {leg['distance_m']} m, "
                     f"{len(pairs) - unresolved}/{len(pairs)} edges resolved, "
                     f"{used_steps} staircase edges"
                     + (f", {unresolved} UNRESOLVED" if unresolved else ""))
        if used_steps or unresolved:
            verdict = FAIL
    if not legs_seen:
        notes.append("    no walking legs to check — nothing was verified")
        verdict = FAIL
    return verdict, notes


# A mapped elevator this close to the door is taken as serving it. Outram Exit 6
# has one at 43 m; Bedok's nearest mapped lift is 779 m, so there the
# `wheelchair=yes` tag is what carries the claim.
LIFT_NEAR_M = 75


async def check_entrances(plan: dict) -> tuple[str, list[str]]:
    """Every door she is sent through: wheelchair=yes, or a lift near it that no
    outage touches.

    An outage that names no exit (`station_only`) or names one this station does
    not have (`unmatched`) is treated as covering the whole station. We cannot
    tell which door it belongs to, so an untagged door at that station is no
    longer something this script is willing to call step-free.
    """
    alerts, _ = await lift_service.current_alerts()
    out_of_service = {(a["station_id"], e) for a in alerts
                      if a["resolution"] == "matched_exit"
                      for e in a.get("blocked_exit_refs") or
                      [(a["exit_code"] or "").replace("Exit ", "")]}
    station_level = {a["station_id"] for a in alerts
                     if a["resolution"] in ("station_only", "unmatched")}
    wg = data.walk_graph()
    notes, verdict, checked, skipped = [], PASS, 0, 0
    for leg in plan["legs"]:
        for end in ("from", "to"):
            node = leg.get(end) or {}
            code, exit_code = node.get("station_code"), node.get("exit_code")
            if not code or not exit_code:
                if node.get("station_code") or node.get("exit_code"):
                    skipped += 1        # half-identified door: cannot check it
                continue
            ref = exit_code.replace("Exit ", "")
            station = data.station_by_code().get(code)
            if not station:
                notes.append(f"    {code} {exit_code}: unknown station code -> FAIL")
                verdict, skipped = FAIL, skipped + 1
                continue
            checked += 1
            area = wg.area_of(*station["coord"])
            osm = wg.entrances_for(area).get(ref, {}) if area else {}
            tag = osm.get("wheelchair")
            lift_out = (station["station_id"], ref) in out_of_service
            station_out = station["station_id"] in station_level
            lift_m = _nearest_lift_m(wg, osm, area)
            lift_near = lift_m is not None and lift_m <= LIFT_NEAR_M

            if lift_out:
                ok, why = False, "its lift is reported OUT"
            elif tag == "no":
                ok, why = False, "OSM wheelchair=no"
            elif tag == "yes":
                ok, why = True, "OSM wheelchair=yes"
            elif station_out:
                ok, why = False, (f"OSM wheelchair={tag or 'untagged'} and a station-level "
                                  f"outage is reported here")
            elif lift_near:
                ok, why = True, (f"OSM wheelchair={tag or 'untagged'}, mapped lift "
                                 f"{lift_m:.0f} m away, no outage reported")
            else:
                ok, why = False, (f"OSM wheelchair={tag or 'untagged'} and no mapped lift "
                                  f"within {LIFT_NEAR_M} m — accessibility unknown")
            notes.append(f"    {station['name']} {exit_code}: {why} -> "
                         f"{'ok' if ok else 'FAIL'}")
            if not ok:
                verdict = FAIL
    notes.append(f"    checked {checked} entrance(s)"
                 + (f", {skipped} could not be identified" if skipped else ""))
    if checked == 0:
        notes.append("    no entrance was checked — this claim verified nothing")
        verdict = FAIL
    if skipped:
        verdict = FAIL
    return verdict, notes


def _nearest_lift_m(wg, osm: dict, area: str | None) -> float | None:
    if not osm.get("coord") or not area:
        return None
    lon, lat = osm["coord"]
    ds = [walking.haversine(lat, lon, lift["coord"][1], lift["coord"][0])
          for lift in wg.elevators if lift["area"] == area]
    return min(ds) if ds else None


async def baseline(plan: dict) -> list[str]:
    """OneMap's plain foot route for the same two walks — an outside opinion."""
    lines = []
    pairs = [("Home -> Bedok Exit B", HOME_DEFAULT["coord"], plan["legs"][0]["to"]["coord"]),
             ("Outram exit -> SGH", plan["legs"][2]["from"]["coord"], SGH["coord"])]
    for label, a, b in pairs:
        ours = walking.route(a, b, data.walk_graph().area_of(*a), step_free=True)
        straight = walking.haversine(a[1], a[0], b[1], b[0])
        try:
            r = await onemap.walk_route((a[1], a[0]), (b[1], b[0]))
            theirs_m = r.get("route_summary", {}).get("total_distance")
            lines.append(f"    {label}:")
            lines.append(f"      straight line            {straight:6.0f} m")
            lines.append(f"      ours, step-free          {ours.distance_m:6.0f} m "
                         f"(x{ours.distance_m / straight:.2f})")
            lines.append(f"      OneMap, plain foot route {theirs_m:6.0f} m "
                         f"(x{theirs_m / straight:.2f})")
        except Exception as exc:
            lines.append(f"    {label}: ours {ours.distance_m:.0f} m step-free, "
                         f"OneMap unavailable ({type(exc).__name__})")
    return lines


async def main() -> None:
    appointment = datetime.now(SGT).replace(second=0, microsecond=0) + timedelta(days=1, hours=10)
    blocked, access = await lift_service.blocked_exits_now()
    plan = planner.plan_trip(HOME_DEFAULT, appointment, blocked_exits=blocked, access=access)

    print("D11 — step-free claim check")
    print(f"  trip: {HOME_DEFAULT['label']} -> {SGH['label']}, {SGH['block']}")
    print(f"  appointment {appointment:%Y-%m-%d %H:%M}, {plan['summary']['leave_by_label']}\n")

    v1, n1 = check_no_steps(plan)
    print(f"  [{v1}] No walking leg uses an OSM-mapped staircase")
    print("\n".join(n1))

    v2, n2 = await check_entrances(plan)
    print(f"\n  [{v2}] Every entrance used is wheelchair=yes or has an in-service lift")
    print("\n".join(n2))

    print("\n  Independent comparison (OneMap, routed on its own data):")
    print("\n".join(await baseline(plan)))

    print("\n  Where we are longer than OneMap, it is because we route only on pedestrian")
    print("  ways OSM actually maps. Where no link is mapped we go around rather than assume")
    print("  a path exists, which over-estimates her walk instead of under-estimating it.")
    print("\n  Not covered by this claim: station interiors. OSM does not model the inside")
    print("  of MRT stations, so the walk from platform to exit is checked by nothing here.")
    print(f"\n  RESULT: {'PASS' if v1 == v2 == PASS else 'FAIL'}")
    sys.exit(0 if v1 == v2 == PASS else 1)


if __name__ == "__main__":
    asyncio.run(main())
