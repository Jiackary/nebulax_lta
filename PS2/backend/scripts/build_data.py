#!/usr/bin/env python3
"""PS2 build-time data pipeline — backend plan §5.

Fetches the upstream sources once, derives the small committed artefacts the
runtime reads, and prints a measurement for every claim the write-up makes.

    python scripts/build_data.py --fetch    # pull upstream into data/cache (gitignored)
    python scripts/build_data.py --build    # derive data/derived/* from the cache
    python scripts/build_data.py --all

Raw pulls are cached to disk deliberately: the brief forbids looping on the
public Overpass instance (PS2_README.md:L57), and a cached corpus keeps the
demo alive if a network dies on judging day.

Never log a download URL: DataMall's S3 links embed an AWS security token.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import statistics
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
DERIVED = ROOT / "data" / "derived"
SGT = timezone(timedelta(hours=8))

DATAMALL = "https://datamall2.mytransport.sg/ltaodataservice"
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "PS2-SmartCommuterCompanion/0.1 (LTA NebulaX hackathon; contact via repo)"

# Her corridor: the only two places she walks. Bboxes are (S, W, N, E).
BEDOK_STATION = (1.32401132, 103.930173)
SGH_COORD = (1.279643, 103.835541)

CORRIDOR = {
    "bedok": (1.3180, 103.9230, 1.3350, 103.9430),
    "outram": (1.2740, 103.8300, 1.2870, 103.8450),
}

# Coordinate precision for every derived artefact. 6 dp is ~11 cm at this
# latitude — well inside the 8 m tolerance the shelter join uses and far finer
# than OSM's own survey accuracy, so it costs nothing and shrinks the graph.
COORD_DP = 6

# Walkable highway values. `steps` is collected but never routed over (D11).
WALKABLE = {
    "footway", "path", "pedestrian", "corridor", "steps", "living_street",
    "residential", "service", "unclassified", "tertiary", "tertiary_link",
    "secondary", "secondary_link", "primary", "primary_link", "track",
    "road", "crossing",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def account_key() -> str:
    key = os.environ.get("LTA_ACCOUNT_KEY", "").strip()
    if not key:
        sys.exit("LTA_ACCOUNT_KEY is not set. `set -a; . .env; set +a` first.")
    return key


# --------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------

def _download_link(endpoint: str, dest: Path, params: dict | None = None) -> None:
    """DataMall endpoints that return an expiring S3 link rather than data (T11)."""
    with httpx.Client(timeout=120, follow_redirects=True) as c:
        r = c.get(f"{DATAMALL}/{endpoint}", params=params,
                  headers={"AccountKey": account_key()})
        if r.status_code == 404:
            sys.exit(f"{endpoint}: 404 — DataMall masks a bad AccountKey as 404, not 401 (T18).")
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("value") or []
        if not rows:
            sys.exit(f"{endpoint}: no rows in response")
        # T22/I4: the guide documents `Link`; the live feed returns lowercase `link`.
        row = rows[0]
        link = row.get("link") or row.get("Link")
        if not link:
            sys.exit(f"{endpoint}: neither `link` nor `Link` present; keys={list(row)}")
        blob = c.get(link)          # never log this URL — it carries an AWS token
        if blob.status_code != 200:
            # raise_for_status() would put the full presigned URL, including
            # X-Amz-Security-Token, into the traceback (F32). Tracebacks get
            # pasted into chat and CI logs.
            sys.exit(f"{endpoint}: download failed ({blob.status_code})")
        dest.write_bytes(blob.content)
    log(f"  {endpoint} -> {dest.name} ({dest.stat().st_size:,} bytes)")


def _write_atomic(path: Path, text: str) -> None:
    """Write via a temp file and os.replace, so an interrupted run cannot leave
    a half-written cache that later reads as valid (F34)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def fetch_gtfs() -> None:
    if (CACHE / "gtfs" / "stops.txt").exists():
        log("fetch: GTFSScheduleTrain — cached, skipping")
        return
    log("fetch: GTFSScheduleTrain")
    zip_path = CACHE / "gtfs_train.zip"
    _download_link("GTFSScheduleTrain", zip_path)
    out = CACHE / "gtfs"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)
    log(f"  extracted {len(list(out.glob('*.txt')))} files")


def fetch_geospatial(layer: str) -> None:
    if list((CACHE / layer).rglob("*.shp")) if (CACHE / layer).exists() else False:
        log(f"fetch: GeospatialWholeIsland {layer} — cached, skipping")
        return
    log(f"fetch: GeospatialWholeIsland {layer}")
    zip_path = CACHE / f"{layer}.zip"
    _download_link("GeospatialWholeIsland", zip_path, params={"ID": layer})
    out = CACHE / layer
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)


def _paged(client: httpx.Client, endpoint: str) -> list[dict]:
    """DataMall pages 500 at a time via $skip (guide p.9)."""
    rows, skip = [], 0
    while True:
        r = client.get(f"{DATAMALL}/{endpoint}", params={"$skip": skip},
                       headers={"AccountKey": account_key()})
        if r.status_code == 404:
            sys.exit(f"{endpoint}: 404 — check the AccountKey header is being sent (T18)")
        r.raise_for_status()
        batch = r.json().get("value", [])
        rows.extend(batch)
        if len(batch) < 500:
            return rows
        skip += 500


def fetch_bus() -> None:
    """BusRoutes + BusStops, for the accessible-bus alternative in D2.2.

    Both files are written only after both fetches succeed, and the skip check
    looks at both. Writing bus_routes.json first meant that if BusStops failed
    once, every later `--all` run saw the cache as present, skipped the fetch,
    and `build_bus_options` died with FileNotFoundError (F34).
    """
    routes_path, stops_path = CACHE / "bus_routes.json", CACHE / "bus_stops.json"
    if routes_path.exists() and stops_path.exists():
        log("fetch: BusRoutes/BusStops — cached, skipping")
        return
    with httpx.Client(timeout=60) as c:
        log("fetch: BusRoutes (paged)")
        routes = _paged(c, "BusRoutes")
        log(f"  {len(routes):,} route rows")
        log("fetch: BusStops (paged)")
        stops = _paged(c, "BusStops")
        log(f"  {len(stops):,} stops")
    _write_atomic(routes_path, json.dumps(routes))
    _write_atomic(stops_path, json.dumps(stops))


def fetch_overpass() -> None:
    """One request per corridor area, cached. Never call this in a loop."""
    for name, (s, w, n, e) in CORRIDOR.items():
        dest = CACHE / f"osm_{name}.json"
        if dest.exists():
            log(f"fetch: overpass {name} — cached, skipping")
            continue
        bbox = f"{s},{w},{n},{e}"
        # `out body geom` — `out geom` alone omits the node id array, which the
        # graph needs to know where two ways meet. Verified against the live API.
        walkable = "|".join(sorted(WALKABLE))
        query = f"""
[out:json][timeout:180];
(
  way[highway~"^({walkable})$"]({bbox});
  node[railway~"^(subway_entrance|train_station_entrance)$"]({bbox});
  node[highway=elevator]({bbox});
);
out body geom;
"""
        log(f"fetch: overpass {name} ({bbox})")
        # The public instance returns a transient 504 under load often enough to
        # break an unattended run. A default User-Agent gets 406 (decision record §2).
        for attempt in range(1, 5):
            with httpx.Client(timeout=300, headers={"User-Agent": UA}) as c:
                r = c.post(OVERPASS, data={"data": query})
            if r.status_code == 200:
                dest.write_bytes(r.content)
                break
            log(f"  attempt {attempt}: HTTP {r.status_code}, retrying in {attempt * 15}s")
            time.sleep(attempt * 15)
        else:
            sys.exit(f"overpass {name}: still failing after 4 attempts")
        log(f"  -> {dest.name} ({dest.stat().st_size:,} bytes)")


# --------------------------------------------------------------------------
# GTFS helpers
# --------------------------------------------------------------------------

def read_csv(name: str) -> list[dict]:
    path = CACHE / "gtfs" / name
    if not path.exists():
        sys.exit(f"missing {path} — run --fetch first")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def hhmmss(t: str) -> int:
    """GTFS times can exceed 24h for post-midnight trips."""
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------

def build_stations() -> dict:
    """stops.txt -> the canonical station table (PS2_README.md:L134, I3)."""
    rows = read_csv("stops.txt")
    parents = {r["stop_id"]: r for r in rows if r["location_type"] == "1"}
    stations: dict[str, dict] = {}
    for sid, r in parents.items():
        stations[sid] = {
            "stop_code": r["stop_code"],
            "name": r["stop_name"],
            "coord": [round(float(r["stop_lon"]), COORD_DP), round(float(r["stop_lat"]), COORD_DP)],
            "codes": set(),
            "platforms": [],
            "entrances": [],
        }
    for r in rows:
        parent = r["parent_station"]
        if not parent or parent not in stations:
            continue
        st = stations[parent]
        if r["location_type"] == "0":
            st["codes"].add(r["stop_code"])
            st["platforms"].append({"stop_id": r["stop_id"], "code": r["stop_code"],
                                    "platform": r["platform_code"]})
        elif r["location_type"] == "2":
            st["entrances"].append({
                "exit_code": r["stop_name"].strip().upper(),
                "stop_id": r["stop_id"],
                "coord": [round(float(r["stop_lon"]), COORD_DP), round(float(r["stop_lat"]), COORD_DP)],
            })
    out = {}
    for sid, st in sorted(stations.items()):
        st["codes"] = sorted(st["codes"] or {st["stop_code"]})
        st["entrances"].sort(key=lambda e: e["exit_code"])
        out[sid] = st
    multi = {k: v["codes"] for k, v in out.items() if len(v["codes"]) > 1}
    ents = sum(len(v["entrances"]) for v in out.values())
    log(f"stations.json: {len(out)} stations, {ents} entrances, "
        f"{len(multi)} interchanges spanning >1 code")
    log(f"  EW16 -> {out['EW16']['codes']}   DT10 -> {out['DT10']['codes']}")
    return out


def build_line_codes(stations: dict) -> dict:
    """Every spelling of every line -> one canonical id (T1)."""
    routes = read_csv("routes.txt")
    colour = {}
    gtfs_ids = defaultdict(list)
    for r in routes:
        short = r["route_short_name"]
        colour[short] = "#" + r["route_color"]
        gtfs_ids[short].append(r["route_id"])

    # canonical id -> (display name, station-code prefixes, GTFS route_short_names,
    #                  every alias any feed is known to use)
    # CEL and CGL have no GTFS short name of their own: the Circle Line Extension
    # rides under CC and the Changi branch is route_id EWL_CGL with short name CG.
    spec = {
        "NSL": ("North-South Line", ["NS"], ["NS"], ["NSL", "NS"]),
        "EWL": ("East-West Line", ["EW"], ["EW"], ["EWL", "EW"]),
        "CGL": ("East-West Line (Changi Extension)", ["CG"], ["CG"], ["CGL", "CG", "EWL_CGL"]),
        "NEL": ("North East Line", ["NE"], ["NE"], ["NEL", "NE"]),
        "CCL": ("Circle Line", ["CC"], ["CC"], ["CCL", "CC"]),
        "CEL": ("Circle Line Extension", ["CE"], [], ["CEL", "CE"]),
        "DTL": ("Downtown Line", ["DT"], ["DT"], ["DTL", "DT"]),
        "TEL": ("Thomson-East Coast Line", ["TE"], ["TE"], ["TEL", "TE"]),
        "BPL": ("Bukit Panjang LRT", ["BP"], ["BP"], ["BPL", "BPLRT", "BP"]),
        "STL": ("Sengkang LRT", ["STC", "SE", "SW"], ["SK"], ["STL", "SLRT", "SK"]),
        "PTL": ("Punggol LRT", ["PTC", "PE", "PW"], ["PG"], ["PTL", "PLRT", "PG"]),
    }
    lines, alias = {}, {}
    for canon, (name, prefixes, shorts, aliases) in spec.items():
        swatch = next((x for x in shorts if x in colour), None)
        lines[canon] = {
            "name": name,
            "colour": colour.get(swatch, "#666666"),
            "station_prefixes": prefixes,
            "gtfs_route_ids": sorted({rid for x in shorts for rid in gtfs_ids.get(x, [])}),
            "aliases": aliases,
        }
        for a in aliases + [canon]:
            alias[a.upper()] = canon
    # Every route_id in the feed must resolve, or the table has a hole.
    mapped = {rid for v in lines.values() for rid in v["gtfs_route_ids"]}
    unmapped = [r["route_id"] for r in routes if r["route_id"] not in mapped]
    log(f"line_codes.json: {len(lines)} canonical lines, {len(alias)} aliases")
    if unmapped:
        log(f"  WARNING unmapped route_ids: {unmapped}")
    # Sanity: every station code prefix in the network resolves to a line.
    codes = {c for st in stations.values() for c in st["codes"]}
    bad = sorted({c for c in codes
                  if not any(c.startswith(p) for v in lines.values() for p in v["station_prefixes"])})
    if bad:
        log(f"  WARNING station codes with no line: {bad}")
    return {"lines": lines, "alias": alias}


def build_exits(stations: dict) -> dict:
    """The exit layer: GTFS entrances, unioned with exits only the shapefile has.

    GTFS leads because it keys on `stop_code` (no station-name join, T21) and
    ships WGS84 (no SVY21 reprojection, T19). But the two are NOT independent
    sources — 97% of shared exits sit within 0.5 m of each other, so LTA plainly
    derives both from one survey. The shapefile earns its place for coverage
    instead: it carries exits GTFS omits at 7 stations (Bugis 8 vs 4). Taking the
    union maximises the chance a LiftDesc exit reference resolves at all (D7).
    """
    feats = []
    for sid, st in stations.items():
        for e in st["entrances"]:
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": e["coord"]},
                "properties": {"station_id": sid, "stop_code": st["stop_code"],
                               "station_name": st["name"], "exit_code": e["exit_code"],
                               "source": "gtfs_stops"},
            })
    extra = _shapefile_only_exits(stations)
    feats.extend(extra)
    gj = {"type": "FeatureCollection",
          "attribution": "Contains information from LTA DataMall "
                         "(GTFSScheduleTrain stops.txt; TrainStationExit Jul2026)",
          "features": feats}
    log(f"exits.geojson: {len(feats)} exits "
        f"({len(feats) - len(extra)} from GTFS, {len(extra)} added from the shapefile)")
    return gj


def _load_shapefile_exits() -> dict[str, dict[str, tuple]]:
    """station name (suffix stripped) -> {exit code: (lat, lon)}, reprojected (T19)."""
    import re
    try:
        import shapefile
        from pyproj import Transformer
    except ImportError:
        log("  TrainStationExit skipped: pyshp/pyproj missing")
        return {}
    hits = list((CACHE / "TrainStationExit").rglob("*.shp"))
    if not hits:
        log("  TrainStationExit not in cache (--fetch to get it)")
        return {}
    base = str(hits[0])[:-4]
    tr = Transformer.from_crs(open(base + ".prj").read(), "EPSG:4326", always_xy=True)
    rd = shapefile.Reader(base)
    out: dict[str, dict[str, tuple]] = defaultdict(dict)
    for rec, shape in zip(rd.records(), rd.shapes()):
        d = rec.as_dict()
        name = re.sub(r"\s+(MRT|LRT)\s+STATION$", "", d["stn_name"].strip().upper())
        code = d["exit_code"].strip().upper().replace("EXIT ", "")
        lon, lat = tr.transform(*shape.points[0])
        out[name][code] = (lat, lon)
    return out


def _shapefile_only_exits(stations: dict) -> list[dict]:
    """Exits present in TrainStationExit but missing from GTFS, plus the agreement stats."""
    shp = _load_shapefile_exits()
    if not shp:
        return []
    by_name = {st["name"].upper(): (sid, st) for sid, st in stations.items()}
    added, seps, same_set, diff_set = [], [], 0, []
    for name, exits in shp.items():
        hit = by_name.get(name)
        if not hit:
            continue
        sid, st = hit
        gtfs = {e["exit_code"]: e["coord"] for e in st["entrances"]}
        if set(gtfs) == set(exits):
            same_set += 1
        else:
            diff_set.append(name)
        for code, (lat, lon) in exits.items():
            if code in gtfs:
                seps.append(_haversine(gtfs[code][1], gtfs[code][0], lat, lon))
            else:
                added.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [round(lon, COORD_DP), round(lat, COORD_DP)]},
                    "properties": {"station_id": sid, "stop_code": st["stop_code"],
                                   "station_name": st["name"], "exit_code": code,
                                   "source": "trainstationexit_jul2026"},
                })
    if seps:
        seps.sort()
        identical = sum(1 for x in seps if x < 0.5)
        log(f"  GTFS vs TrainStationExit: exit sets identical at {same_set} stations, "
            f"differ at {len(diff_set)} ({', '.join(sorted(diff_set))})")
        log(f"  shared exits within 0.5 m: {identical}/{len(seps)} "
            f"({100 * identical / len(seps):.1f}%) — same survey, NOT independent corroboration")
        log(f"  separation median {statistics.median(seps):.2f} m, max {max(seps):.1f} m")
    return added


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


DAYTYPE = {"WD": "weekday", "WE": "saturday", "PH": "sunday_ph"}


def _service_daytype(service_id: str) -> str:
    for k, v in DAYTYPE.items():
        if service_id.startswith(f"SERVICE_{k}"):
            return v
    return "weekday"


def _trip_index() -> dict:
    return {t["trip_id"]: t for t in read_csv("trips.txt")}


def build_ridetimes(stations: dict) -> dict:
    """Consecutive-segment run times per route+direction, measured across every trip.

    I1/T24: these are fixed values on her line, not ranges. The spread printed
    here is the evidence for that claim, recomputed on every build.
    """
    trips = _trip_index()
    by_trip: dict[str, list] = defaultdict(list)
    for r in read_csv("stop_times.txt"):
        by_trip[r["trip_id"]].append(r)

    seg: dict[tuple, list[float]] = defaultdict(list)
    seq: dict[tuple, list[str]] = {}
    pair_ew: list[float] = []
    # End-to-end times per ordered station pair. Summing consecutive segments
    # under-counts by the dwell at every intermediate stop (40 s each on the EWL,
    # which is 6.7 min across her 11-stop ride), so pairs are measured directly.
    pairs: dict[tuple, list[float]] = defaultdict(list)
    for tid, rows in by_trip.items():
        t = trips.get(tid)
        if not t:
            continue
        rows.sort(key=lambda r: int(r["stop_sequence"]))
        key = (t["route_id"], t["direction_id"])
        codes = [r["stop_id"].rsplit("_", 1)[0] for r in rows]
        # Keep the longest observed sequence: plenty of trips start mid-line, so
        # the first one seen is not the canonical stop order.
        if len(codes) > len(seq.get(key, ())):
            seq[key] = codes
        for a, b in zip(rows, rows[1:]):
            ca, cb = a["stop_id"].rsplit("_", 1)[0], b["stop_id"].rsplit("_", 1)[0]
            seg[(key, ca, cb)].append((hhmmss(b["arrival_time"]) - hhmmss(a["departure_time"])) / 60)
        for i, a in enumerate(rows):
            dep = hhmmss(a["departure_time"])
            ca = codes[i]
            for j in range(i + 1, len(rows)):
                pairs[(key[0], ca, codes[j])].append((hhmmss(rows[j]["arrival_time"]) - dep) / 60)
        # her leg, measured end to end across every trip that serves it
        pos = {c: i for i, c in enumerate(codes)}
        if "EW5" in pos and "EW16" in pos and pos["EW5"] < pos["EW16"]:
            dep = hhmmss(rows[pos["EW5"]]["departure_time"])
            arr = hhmmss(rows[pos["EW16"]]["arrival_time"])
            pair_ew.append((arr - dep) / 60)

    headsigns: dict[tuple, Counter] = defaultdict(Counter)
    for tid in by_trip:
        t = trips.get(tid)
        if t and t.get("trip_headsign"):
            headsigns[(t["route_id"], t["direction_id"])][t["trip_headsign"]] += 1

    out = {}
    for (key, ca, cb), vals in seg.items():
        route, direction = key
        out.setdefault(route, {}).setdefault(direction, {
            "stops": seq[key], "segments": {},
            "headsign": (headsigns[key].most_common(1) or [("", 0)])[0][0],
        })
        out[route][direction]["segments"][f"{ca}>{cb}"] = {
            "min": round(min(vals), 2), "median": round(statistics.median(vals), 2),
            "max": round(max(vals), 2), "trips": len(vals),
        }
    claim = {
        "pair": "EW5>EW16", "trips": len(pair_ew),
        "min": round(min(pair_ew), 2), "median": round(statistics.median(pair_ew), 2),
        "max": round(max(pair_ew), 2),
        "note": "Scheduled ride time, not a stopwatch. Fixed across all trips (I1/T24).",
    }
    pair_out: dict = {}
    for (route, a, b), vals in pairs.items():
        pair_out.setdefault(route, {})[f"{a}>{b}"] = {
            "min": round(min(vals), 2), "median": round(statistics.median(vals), 2),
            "max": round(max(vals), 2), "trips": len(vals),
        }
    out["_pairs"] = pair_out
    out["_claims"] = {"ew5_ew16": claim}
    log(f"  end-to-end pairs: {sum(len(v) for v in pair_out.values()):,} across "
        f"{len(pair_out)} routes (EWL EW5>EW16 = "
        f"{pair_out['EWL']['EW5>EW16']['median']} min, includes dwell)")
    log(f"ridetimes.json: {claim['trips']} EW5>EW16 trips, "
        f"min {claim['min']} / median {claim['median']} / max {claim['max']} min")
    spread = claim["max"] - claim["min"]
    log(f"  ride-time spread = {spread:.2f} min -> "
        f"{'FIXED, confirms I1' if spread < 0.01 else 'VARIES — I1 needs revisiting'}")
    return out


def build_headways(stations: dict) -> dict:
    """Median gap between departures, per route/station/direction/daytype/hour (I1)."""
    trips = _trip_index()
    deps: dict[tuple, list[int]] = defaultdict(list)
    for r in read_csv("stop_times.txt"):
        t = trips.get(r["trip_id"])
        if not t:
            continue
        code = r["stop_id"].rsplit("_", 1)[0]
        deps[(t["route_id"], code, t["direction_id"], _service_daytype(t["service_id"]))].append(
            hhmmss(r["departure_time"]))

    out: dict = {}
    for (route, code, direction, daytype), times in deps.items():
        times.sort()
        by_hour: dict[int, list[float]] = defaultdict(list)
        for a, b in zip(times, times[1:]):
            gap = (b - a) / 60
            if 0 < gap <= 60:
                by_hour[(a // 3600) % 24].append(gap)
        node = out.setdefault(route, {}).setdefault(code, {}).setdefault(daytype, {}).setdefault(direction, {})
        for hour, gaps in by_hour.items():
            node[str(hour)] = round(statistics.median(gaps), 1)
    ew5 = out.get("EWL", {}).get("EW5", {}).get("weekday", {})
    log(f"headways.json: {len(out)} routes")
    for d, hours in sorted(ew5.items()):
        log(f"  EWL EW5 weekday dir={d}: 08h={hours.get('8')} min, 13h={hours.get('13')} min")
    return out


def _near_shelter(tree, tol: float, a: dict, b: dict) -> bool:
    """Is this segment's midpoint within tol of an LTA covered linkway?"""
    if tree is None:
        return False
    from shapely.geometry import Point
    mid = Point((a["lon"] + b["lon"]) / 2, (a["lat"] + b["lat"]) / 2)
    for idx in tree.query(mid.buffer(tol)):
        if tree.geometries[idx].distance(mid) <= tol:
            return True
    return False


def _load_covered_linkways() -> list:
    """LTA CoveredLinkWay, reprojected (T19) and clipped to her corridor.

    OSM's own `covered=yes` tagging is thin here — it marks 6% of corridor
    footway length. LTA surveys sheltered walkways directly, which is what D9's
    rain policy needs.
    """
    try:
        import shapefile
        from pyproj import Transformer
        from shapely.geometry import LineString, box
    except ImportError:
        log("  CoveredLinkWay skipped: pyshp/pyproj/shapely missing")
        return []
    hits = list((CACHE / "CoveredLinkWay").rglob("*.shp"))
    if not hits:
        log("  CoveredLinkWay not in cache — shelter falls back to OSM tags only")
        return []
    base = str(hits[0])[:-4]
    tr = Transformer.from_crs(open(base + ".prj").read(), "EPSG:4326", always_xy=True)
    clips = [box(w, s, e, n) for (s, w, n, e) in CORRIDOR.values()]
    lines = []
    rd = shapefile.Reader(base)
    for shape in rd.shapes():
        if len(shape.points) < 2:
            continue
        pts = [tr.transform(x, y) for x, y in shape.points]
        ls = LineString(pts)
        if any(c.intersects(ls) for c in clips):
            lines.append(ls)
    log(f"  CoveredLinkWay ({hits[0].parent.name}): {rd.numRecords:,} island-wide, "
        f"{len(lines)} in her corridor")
    return lines


def _label_components(nodes: dict, edges: list) -> tuple[dict, dict]:
    """node id -> component index, plus the component that actually matters per area.

    Routing must snap to the area's main component. The nearest node to a
    destination is often a driveway stub with no way out.
    """
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from((e["u"], e["v"]) for e in edges)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    label = {str(n): i for i, c in enumerate(comps) for n in c}
    # the main component for an area is the one carrying most of its edges
    tally: dict[str, Counter] = defaultdict(Counter)
    for e in edges:
        tally[e["area"]][label[str(e["u"])]] += 1
    main = {area: c.most_common(1)[0][0] for area, c in tally.items()}
    sizes = [len(c) for c in comps]
    log(f"  components: {len(comps)} (largest {sizes[0]:,}, "
        f"{sum(1 for x in sizes if x <= 2)} stubs of <=2 nodes)")
    for area, idx in sorted(main.items()):
        log(f"    {area}: main component #{idx} holds {len(comps[idx]):,} nodes")
    return label, main


def build_osm_graph() -> tuple[dict, dict]:
    """Foot graph for her two walking areas, plus the shelter layer (D9, D11)."""
    nodes: dict[int, list] = {}
    edges: list[dict] = []
    entrances: list[dict] = []
    elevators: list[dict] = []
    steps_count = 0

    covered_lines = _load_covered_linkways()
    tree = None
    if covered_lines:
        from shapely.strtree import STRtree
        from shapely.geometry import Point
        tree = STRtree(covered_lines)
    # ~8 m in degrees at this latitude; a walkway and its footway rarely coincide
    # exactly, and LTA's centreline is offset from OSM's.
    SHELTER_TOL = 8.0 / 111_320

    for area in CORRIDOR:
        path = CACHE / f"osm_{area}.json"
        if not path.exists():
            sys.exit(f"missing {path} — run --fetch first")
        payload = json.loads(path.read_text())
        for el in payload["elements"]:
            tags = el.get("tags", {})
            if el["type"] == "node":
                pt = [round(el["lon"], COORD_DP), round(el["lat"], COORD_DP)]
                if tags.get("railway") in ("subway_entrance", "train_station_entrance"):
                    entrances.append({"osm_id": el["id"], "coord": pt,
                                      "ref": (tags.get("ref") or "").strip().upper(),
                                      "wheelchair": tags.get("wheelchair"),
                                      "name": tags.get("name"), "area": area})
                if tags.get("highway") == "elevator":
                    elevators.append({"osm_id": el["id"], "coord": pt,
                                      "level": tags.get("level"), "area": area})
                continue
            if el["type"] != "way" or tags.get("highway") not in WALKABLE:
                continue
            geom = el.get("geometry") or []
            if len(geom) < 2:
                continue
            is_steps = tags.get("highway") == "steps"
            steps_count += is_steps
            covered_osm = (tags.get("covered") in ("yes", "booth", "arcade")
                           or tags.get("tunnel") == "building_passage"
                           or tags.get("indoor") == "yes")
            ids = el.get("nodes")
            if not ids or len(ids) != len(geom):
                sys.exit(f"way {el['id']}: node ids missing or misaligned — "
                         "the Overpass query must use `out body geom`")
            for i, (a, b) in enumerate(zip(geom, geom[1:])):
                na, nb = ids[i], ids[i + 1]
                nodes[na] = [round(a["lon"], COORD_DP), round(a["lat"], COORD_DP)]
                nodes[nb] = [round(b["lon"], COORD_DP), round(b["lat"], COORD_DP)]
                edges.append({
                    "u": na, "v": nb, "way": el["id"],
                    "len_m": round(_haversine(a["lat"], a["lon"], b["lat"], b["lon"]), 2),
                    "highway": tags["highway"], "steps": is_steps,
                    "covered": covered_osm or _near_shelter(tree, SHELTER_TOL, a, b),
                    "covered_osm": covered_osm,
                    "wheelchair": tags.get("wheelchair"),
                    "oneway": tags.get("oneway") == "yes",
                    "area": area,
                })
    # Label connected components now, so the planner never snaps a trip onto an
    # isolated stub. A bbox extract leaves plenty: 112 two-node fragments here,
    # and the nearest node to Outram Exit 4 sits in one of them.
    components, main_by_area = _label_components(nodes, edges)

    graph = {
        "attribution": "© OpenStreetMap contributors",
        "licence": "ODbL 1.0",
        "built_at": datetime.now(SGT).isoformat(timespec="seconds"),
        "corridor": CORRIDOR,
        "nodes": nodes, "edges": edges,
        "components": components, "main_component_by_area": main_by_area,
        "entrances": entrances, "elevators": elevators,
    }
    covered_m = sum(e["len_m"] for e in edges if e["covered"])
    osm_only_m = sum(e["len_m"] for e in edges if e["covered_osm"])
    total_m = sum(e["len_m"] for e in edges)
    log(f"stepfree_graph.json: {len(nodes):,} nodes, {len(edges):,} edges "
        f"({steps_count} step ways excluded from routing)")
    log(f"  entrances {len(entrances)} ({sum(1 for e in entrances if e['ref'])} with ref, "
        f"{sum(1 for e in entrances if e['wheelchair'])} with wheelchair tag), "
        f"elevators {len(elevators)}")
    log(f"  sheltered {covered_m / 1000:.2f} km of {total_m / 1000:.2f} km "
        f"({100 * covered_m / total_m:.0f}%) — OSM tags alone would give "
        f"{100 * osm_only_m / total_m:.0f}%")
    covered_gj = {
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors; "
                       "contains information from LTA DataMall (CoveredLinkWay)",
        "features": [{"type": "Feature",
                      "geometry": {"type": "LineString",
                                   "coordinates": [nodes[e["u"]], nodes[e["v"]]]},
                      "properties": {"way": e["way"], "highway": e["highway"],
                                     "area": e["area"], "osm_tagged": e["covered_osm"]}}
                     for e in edges if e["covered"]],
    }
    return graph, covered_gj


def build_bus_options() -> dict:
    """Bus services that serve both her end and the hospital end, in one ride.

    D2.2 offers "a regular bus to SGH". Whether such a bus exists is a question
    about the network, not an assumption — so it is answered here from
    BusRoutes, and if the answer is none, the option is not offered.
    """
    rp, sp = CACHE / "bus_routes.json", CACHE / "bus_stops.json"
    if not rp.exists():
        log("  bus options skipped: run --fetch first")
        return {}
    routes = json.loads(rp.read_text())
    stops = {s["BusStopCode"]: s for s in json.loads(sp.read_text())}

    def near(lat: float, lon: float, radius: float) -> set[str]:
        return {code for code, s in stops.items()
                if _haversine(lat, lon, s["Latitude"], s["Longitude"]) <= radius}

    home_stops = near(BEDOK_STATION[0], BEDOK_STATION[1], 500)
    sgh_stops = near(SGH_COORD[0], SGH_COORD[1], 500)
    log(f"  bus stops within 500 m: {len(home_stops)} near Bedok, {len(sgh_stops)} near SGH")

    by_service: dict[tuple, list] = defaultdict(list)
    for r in routes:
        by_service[(r["ServiceNo"], r["Direction"])].append(r)

    options = []
    for (svc, direction), rows in by_service.items():
        rows.sort(key=lambda r: r["StopSequence"])
        board = next((r for r in rows if r["BusStopCode"] in home_stops), None)
        if not board:
            continue
        alight = next((r for r in rows
                       if r["BusStopCode"] in sgh_stops
                       and r["StopSequence"] > board["StopSequence"]), None)
        if not alight:
            continue
        options.append({
            "service_no": svc, "direction": direction,
            "board": {"code": board["BusStopCode"],
                      "name": stops[board["BusStopCode"]]["Description"],
                      "road": stops[board["BusStopCode"]]["RoadName"],
                      "coord": [stops[board["BusStopCode"]]["Longitude"],
                                stops[board["BusStopCode"]]["Latitude"]],
                      "first_bus": board.get("WD_FirstBus"), "last_bus": board.get("WD_LastBus")},
            "alight": {"code": alight["BusStopCode"],
                       "name": stops[alight["BusStopCode"]]["Description"],
                       "road": stops[alight["BusStopCode"]]["RoadName"],
                       "coord": [stops[alight["BusStopCode"]]["Longitude"],
                                 stops[alight["BusStopCode"]]["Latitude"]]},
            "stops": alight["StopSequence"] - board["StopSequence"],
            "distance_km": round(alight["Distance"] - board["Distance"], 1),
        })
    options.sort(key=lambda o: o["stops"])
    if options:
        for o in options[:5]:
            log(f"    bus {o['service_no']} dir {o['direction']}: "
                f"{o['board']['name']} -> {o['alight']['name']}, "
                f"{o['stops']} stops, {o['distance_km']} km")
    else:
        log("    no single bus serves both ends — D2.2 cannot offer one")
    log(f"  bus_options.json: {len(options)} direct services")
    return {"direct": options,
            "home_stop_count": len(home_stops), "sgh_stop_count": len(sgh_stops)}


def write(name: str, payload) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / name
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False))
    log(f"  wrote {name} ({path.stat().st_size:,} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if not (args.fetch or args.build or args.all):
        ap.error("pick --fetch, --build or --all")

    CACHE.mkdir(parents=True, exist_ok=True)
    if args.fetch or args.all:
        log("=== fetch ===")
        fetch_gtfs()
        fetch_geospatial("TrainStationExit")
        fetch_geospatial("CoveredLinkWay")
        fetch_bus()
        fetch_overpass()

    if args.build or args.all:
        log("=== build ===")
        stations = build_stations()
        lines = build_line_codes(stations)
        exits = build_exits(stations)
        ridetimes = build_ridetimes(stations)
        headways = build_headways(stations)
        graph, covered = build_osm_graph()
        bus = build_bus_options()
        log("=== write ===")
        write("stations.json", stations)
        write("line_codes.json", lines)
        write("exits.geojson", exits)
        write("ridetimes.json", ridetimes)
        write("headways.json", headways)
        write("stepfree_graph.json", graph)
        write("covered_ways.geojson", covered)
        write("bus_options.json", bus)
        log("done.")


if __name__ == "__main__":
    main()
