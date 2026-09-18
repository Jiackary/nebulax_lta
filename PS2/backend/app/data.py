"""Loads the committed build-time artefacts once, and holds the walking graphs.

Everything here is derived by `scripts/build_data.py` and checked into the repo,
so the app starts with no network and a judge sees the same numbers we did.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .config import DERIVED, HANDCHECKED


def _load(name: str):
    path: Path = DERIVED / name
    if not path.exists():
        raise RuntimeError(f"{name} missing — run `python scripts/build_data.py --all` first")
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def stations() -> dict:
    return _load("stations.json")


@lru_cache(maxsize=1)
def line_codes() -> dict:
    return _load("line_codes.json")


@lru_cache(maxsize=1)
def exits() -> dict:
    return _load("exits.geojson")


@lru_cache(maxsize=1)
def ridetimes() -> dict:
    return _load("ridetimes.json")


@lru_cache(maxsize=1)
def headways() -> dict:
    return _load("headways.json")


@lru_cache(maxsize=1)
def bus_options() -> dict:
    return _load("bus_options.json")


@lru_cache(maxsize=1)
def public_holidays() -> frozenset[str]:
    """ISO dates that run the `sunday_ph` timetable (F27).

    Hand-entered rather than derived — `build_data.py` reads the GTFS
    `service_id` prefix and never `calendar_dates.txt`, so no committed artefact
    knows the dates. Absent file means an empty set, which is the old behaviour:
    every weekday uses the weekday table.
    """
    path = HANDCHECKED / "public_holidays.json"
    if not path.exists():
        return frozenset()
    return frozenset(h["date"] for h in json.loads(path.read_text())["holidays"])


@lru_cache(maxsize=1)
def graph_raw() -> dict:
    return _load("stepfree_graph.json")


def canonical_line(code: str) -> str | None:
    """Any spelling of a line -> our one canonical id (T1)."""
    return line_codes()["alias"].get((code or "").strip().upper())


@lru_cache(maxsize=1)
def station_by_code() -> dict[str, dict]:
    """Every stop_code — including the ones that share a parent — to its station.

    `parent_station` unifies 28 interchanges, so an alert naming TE17 and one
    naming EW16 resolve to the same physical place (I3).
    """
    out = {}
    for sid, st in stations().items():
        for code in st["codes"]:
            out[code] = {**st, "station_id": sid}
        out[st["stop_code"]] = {**st, "station_id": sid}
    return out


@lru_cache(maxsize=1)
def exits_by_station() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in exits()["features"]:
        p = f["properties"]
        out.setdefault(p["station_id"], []).append(
            {**p, "coord": f["geometry"]["coordinates"]})
    for v in out.values():
        v.sort(key=lambda e: e["exit_code"])
    return out


class WalkGraph:
    """The corridor foot network, with and without staircases."""

    def __init__(self) -> None:
        raw = graph_raw()
        self.nodes = {int(k): v for k, v in raw["nodes"].items()}
        self.component = {int(k): v for k, v in raw["components"].items()}
        self.main_by_area = raw["main_component_by_area"]
        self.entrances = raw["entrances"]
        self.elevators = raw["elevators"]
        self.corridor = raw["corridor"]
        self.built_at = raw["built_at"]

        self.step_free = nx.Graph()
        self.all_ways = nx.Graph()
        for e in raw["edges"]:
            attrs = dict(w=e["len_m"], covered=e["covered"], steps=e["steps"],
                         highway=e["highway"])
            self.all_ways.add_edge(e["u"], e["v"], **attrs)
            if not e["steps"]:
                self.step_free.add_edge(e["u"], e["v"], **attrs)
        self._by_area: dict[tuple[str, bool], list[int]] = {}

    def area_of(self, lon: float, lat: float) -> str | None:
        for name, (s, w, n, e) in self.corridor.items():
            if s <= lat <= n and w <= lon <= e:
                return name
        return None

    def candidates(self, area: str, step_free: bool) -> list[int]:
        """Only nodes in the area's main component — the rest are stubs (I11).

        `self.component` was computed at build time on the graph *with* stairs,
        so for step-free snapping it is the wrong partition: drop the staircases
        and Bedok's one main component falls into 105 pieces (12,077 nodes, then
        235, 77, …). Snapping to the nearest node of any piece then strands an
        origin on a 47-node island and answers "no step-free walking route" for
        a coordinate 42 m from the network she can actually use (F17). So for
        `step_free` the components are recomputed here, on the step-free graph,
        and only the largest is offered.

        Dropping the small pieces rather than routing within them is the safe
        direction: a route confined to an island would be a walk that cannot
        reach any entrance. An origin too far from the main piece still fails
        `MAX_ORIGIN_SNAP_M` in the planner and is told so honestly.
        """
        key = (area, step_free)
        if key not in self._by_area:
            G = self.step_free if step_free else self.all_ways
            want = self.main_by_area[area]
            nodes = [n for n in G.nodes if self.component.get(n) == want]
            if step_free and nodes:
                nodes = sorted(max(nx.connected_components(G.subgraph(nodes)), key=len))
            self._by_area[key] = nodes
        return self._by_area[key]

    def station_of_entrance(self, ent: dict) -> str | None:
        """Which station an OSM entrance belongs to (F08).

        A corridor bbox holds more than one station, so keying entrances by the
        bare `ref` let Chinatown's Exit C and Cantonment's Exit 2 stand in for
        Outram Park's. OSM names most entrances after their station
        ("Outram Park", "Chinatown (C)"), so the name decides it. Only genuinely
        unnamed ones fall back to the nearest station — and with no radius cut-off,
        because Outram Exit 6, the door her plan actually uses, is 276 m from the
        station centroid and a 250 m rule would discard it.
        """
        if not hasattr(self, "_ent_station"):
            self._ent_station = {}
        key = ent["osm_id"]
        if key in self._ent_station:
            return self._ent_station[key]

        from .services.walking import haversine
        in_area = [(sid, st) for sid, st in stations().items()
                   if self.area_of(*st["coord"]) == ent["area"]]
        name = re.sub(r"\s*\(.*\)\s*$", "", (ent.get("name") or "")).strip().casefold()
        found = None
        if name:
            found = next((sid for sid, st in in_area
                          if st["name"].casefold() == name), None)
        if found is None and in_area:
            lon, lat = ent["coord"]
            found = min(in_area,
                        key=lambda p: haversine(lat, lon, p[1]["coord"][1],
                                                p[1]["coord"][0]))[0]
        self._ent_station[key] = found
        return found

    def entrances_for(self, area: str, station_id: str | None = None) -> dict[str, dict]:
        """Entrances in `area`, keyed by ref — restricted to one station's own.

        Without `station_id` this is the old behaviour and still mixes stations;
        every caller that decides where she may walk passes it.
        """
        from .services.walking import haversine
        out: dict[str, dict] = {}
        for e in self.entrances:
            if not e["ref"] or e["area"] != area:
                continue
            if station_id is not None and self.station_of_entrance(e) != station_id:
                continue
            prior = out.get(e["ref"])
            if prior is None:
                out[e["ref"]] = e
                continue
            # Same ref twice within one station: keep the one at the station.
            st = stations().get(self.station_of_entrance(e) or "")
            if not st:
                continue
            d = (haversine(st["coord"][1], st["coord"][0], e["coord"][1], e["coord"][0]),
                 haversine(st["coord"][1], st["coord"][0],
                           prior["coord"][1], prior["coord"][0]))
            if d[0] < d[1]:
                out[e["ref"]] = e
        return out


@lru_cache(maxsize=1)
def walk_graph() -> WalkGraph:
    return WalkGraph()
