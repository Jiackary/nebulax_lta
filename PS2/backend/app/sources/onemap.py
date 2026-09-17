"""OneMap geocoding (I9).

Used for address search only. Walking legs route on our own OSM graph, because
OneMap's router does not exclude `highway=steps` and knows nothing about which
lift is out — D11's step-free claim cannot rest on it.

The token is a JWT that expires; on 401 we say so plainly rather than returning
an empty result set that looks like "no such address".
"""
from __future__ import annotations

import httpx

from ..config import ONEMAP, ONEMAP_TOKEN


class OneMapAuthError(RuntimeError):
    pass


async def search(query: str, limit: int = 8) -> list[dict]:
    if not ONEMAP_TOKEN:
        raise OneMapAuthError("ONEMAP_TOKEN is not set")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{ONEMAP}/common/elastic/search",
            params={"searchVal": query, "returnGeom": "Y", "getAddrDetails": "Y"},
            headers={"Authorization": f"Bearer {ONEMAP_TOKEN}"})
    if r.status_code == 401:
        raise OneMapAuthError("OneMap token rejected — it may have expired")
    r.raise_for_status()
    payload = r.json()
    # An unauthenticated call still returns rows, with the error alongside them.
    if payload.get("error"):
        raise OneMapAuthError(f"OneMap: {payload['error']}")
    out = []
    for row in payload.get("results", [])[:limit]:
        try:
            coord = [float(row["LONGITUDE"]), float(row["LATITUDE"])]
        except (KeyError, ValueError):
            continue
        out.append({
            "label": row.get("SEARCHVAL") or row.get("ADDRESS", ""),
            "address": row.get("ADDRESS", ""),
            "postal": None if row.get("POSTAL") in ("NIL", "") else row.get("POSTAL"),
            "coord": coord,
        })
    return out


async def walk_route(start: tuple[float, float], end: tuple[float, float]) -> dict:
    """Plain foot route — the independent baseline for D11's comparison."""
    if not ONEMAP_TOKEN:
        raise OneMapAuthError("ONEMAP_TOKEN is not set")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{ONEMAP}/public/routingsvc/route",
            params={"start": f"{start[0]},{start[1]}", "end": f"{end[0]},{end[1]}",
                    "routeType": "walk"},
            headers={"Authorization": f"Bearer {ONEMAP_TOKEN}"})
    if r.status_code == 401:
        raise OneMapAuthError("OneMap token rejected — it may have expired")
    r.raise_for_status()
    return r.json()
