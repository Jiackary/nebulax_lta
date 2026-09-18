"""Walking legs on our own OSM graph.

Why not OneMap's walk router: it does not exclude `highway=steps` and knows
nothing about which lift is out, so D11's step-free claim cannot rest on it.
OneMap is used for geocoding, and as the independent baseline in
`verify_stepfree.py` — never to build the route we show her.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import networkx as nx

from .. import data

# How much further she will walk to stay dry, when rain is forecast (D9).
SHELTER_DETOUR_FACTOR = 1.8


@dataclass
class Walk:
    distance_m: float
    covered_m: float
    coords: list[list[float]]
    steps_used: int
    snap_m: float
    highways: dict = field(default_factory=dict)

    @property
    def sheltered_pct(self) -> int:
        return round(100 * self.covered_m / self.distance_m) if self.distance_m else 0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _snap(wg, coord: list[float], area: str, step_free: bool) -> tuple[int, float]:
    lon, lat = coord
    best, best_d = None, float("inf")
    for n in wg.candidates(area, step_free):
        p = wg.nodes[n]
        d = haversine(lat, lon, p[1], p[0])
        if d < best_d:
            best, best_d = n, d
    return best, best_d


def route(origin: list[float], dest: list[float], area: str, *,
          step_free: bool = True, prefer_sheltered: bool = False) -> Walk | None:
    """Shortest walk. With `prefer_sheltered`, uncovered ways cost more, so she
    takes a longer covered route when one exists — and we can say why (D9)."""
    wg = data.walk_graph()
    G = wg.step_free if step_free else wg.all_ways
    a, da = _snap(wg, origin, area, step_free)
    b, db = _snap(wg, dest, area, step_free)
    if a is None or b is None:
        return None

    if prefer_sheltered:
        def weight(u, v, e):
            return e["w"] if e["covered"] else e["w"] * SHELTER_DETOUR_FACTOR
    else:
        def weight(u, v, e):
            return e["w"]

    try:
        path = nx.shortest_path(G, a, b, weight=weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

    dist = cov = 0.0
    steps = 0
    highways: dict[str, float] = {}
    for u, v in zip(path, path[1:]):
        e = G[u][v]
        dist += e["w"]
        if e["covered"]:
            cov += e["w"]
        if e["steps"]:
            steps += 1
        highways[e["highway"]] = round(highways.get(e["highway"], 0) + e["w"], 1)
    return Walk(round(dist, 1), round(cov, 1), [wg.nodes[n] for n in path],
                steps, round(max(da, db), 1), highways)


def choose_entrance(target: list[float], area: str, *, blocked: set[str] | None = None,
                    prefer_sheltered: bool = False,
                    station_id: str | None = None) -> tuple[str, Walk, dict] | None:
    """Pick the entrance giving the shortest step-free walk.

    Excludes anything OSM tags `wheelchair=no` — a useful negative, e.g. Outram
    Park exit 5 — and anything `blocked` (a lift outage, from D7). An entrance
    with no wheelchair tag is *unknown*, not unusable: OSM coverage is 60%
    island-wide (§6 limitation 5).

    An entrance OSM tags `wheelchair=yes` is preferred over an untagged one even
    when the untagged one is nearer (F11): with Outram Exit 6 out, the shortest
    walk was the untagged Exit 7 at 555 m, and sending her there while claiming
    `step_free: "yes"` asserts something nobody checked. The tagged Exit 1 at
    635 m costs about a minute and is known to work.
    """
    wg = data.walk_graph()
    blocked = blocked or set()
    best = None
    for ref, ent in wg.entrances_for(area, station_id).items():
        if ref in blocked or ent.get("wheelchair") == "no":
            continue
        walk = route(target, ent["coord"], area, step_free=True,
                     prefer_sheltered=prefer_sheltered)
        if walk is None:
            continue
        # Known-accessible first, then shortest.
        rank = (0 if ent.get("wheelchair") == "yes" else 1, walk.distance_m)
        if best is None or rank < best[0]:
            best = (rank, ref, walk, ent)
    return None if best is None else best[1:]
