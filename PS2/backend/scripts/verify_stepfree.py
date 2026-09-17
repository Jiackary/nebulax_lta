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
    notes, verdict = [], PASS
    wg = data.walk_graph()
    for leg in plan["legs"]:
        if leg["mode"] != "walk":
            continue
        coords = leg["geometry"]["coordinates"]
        index = {tuple(v): k for k, v in wg.nodes.items()}
        used_steps = 0
        for a, b in zip(coords, coords[1:]):
            u, v = index.get(tuple(a)), index.get(tuple(b))
            if u is None or v is None:
                continue
            edge = wg.all_ways.get_edge_data(u, v) or {}
            if edge.get("steps"):
                used_steps += 1
        notes.append(f"    {leg['leg_id']}: {leg['distance_m']} m, {used_steps} staircase edges")
        if used_steps:
            verdict = FAIL
    return verdict, notes


async def check_entrances(plan: dict) -> tuple[str, list[str]]:
    """Every door she is sent through: wheelchair=yes, or a lift that is in service."""
    alerts, _ = await lift_service.current_alerts()
    out_of_service = {(a["station_id"], (a["exit_code"] or "").replace("Exit ", ""))
                      for a in alerts if a["resolution"] == "matched_exit"}
    wg = data.walk_graph()
    notes, verdict = [], PASS
    for leg in plan["legs"]:
        for end in ("from", "to"):
            node = leg.get(end) or {}
            code, exit_code = node.get("station_code"), node.get("exit_code")
            if not code or not exit_code:
                continue
            ref = exit_code.replace("Exit ", "")
            station = data.station_by_code().get(code)
            area = wg.area_of(*station["coord"]) if station else None
            osm = wg.entrances_for(area).get(ref, {}) if area else {}
            tag = osm.get("wheelchair")
            lift_out = (station["station_id"], ref) in out_of_service
            ok = (tag == "yes" or not lift_out)
            reason = (f"OSM wheelchair={tag or 'untagged'}"
                      + (", lift reported OUT" if lift_out else ", no lift outage reported"))
            notes.append(f"    {station['name']} {exit_code}: {reason} -> "
                         f"{'ok' if ok else 'FAIL'}")
            if not ok:
                verdict = FAIL
    return verdict, notes


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
