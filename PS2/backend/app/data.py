"""Loads the committed build-time artefacts once, and holds the walking graphs.

Everything here is derived by `scripts/build_data.py` and checked into the repo,
so the app starts with no network and a judge sees the same numbers we did.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import networkx as nx

from .config import DERIVED


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
        """Only nodes in the area's main component — the rest are stubs (I11)."""
        key = (area, step_free)
        if key not in self._by_area:
            G = self.step_free if step_free else self.all_ways
            want = self.main_by_area[area]
            self._by_area[key] = [n for n in G.nodes if self.component.get(n) == want]
        return self._by_area[key]

    def entrances_for(self, area: str) -> dict[str, dict]:
        return {e["ref"]: e for e in self.entrances if e["ref"] and e["area"] == area}


@lru_cache(maxsize=1)
def walk_graph() -> WalkGraph:
    return WalkGraph()
