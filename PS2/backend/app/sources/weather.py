"""data.gov.sg 2-hour nowcast. No key required.

T14 / §6 limitation 10: the 24-hour forecast resolves to five coarse regions, so
per-area rain needs this endpoint. Even here the resolution is a named area, not
a street — the nearest area to SGH is "City" at 1.7 km.
"""
from __future__ import annotations

import math

import httpx

from ..config import WEATHER
from .base import Source

WET = {"Light Rain", "Moderate Rain", "Heavy Rain", "Passing Showers", "Light Showers",
       "Showers", "Heavy Showers", "Thundery Showers", "Heavy Thundery Showers",
       "Heavy Thundery Showers with Gusty Winds"}


async def _fetch(client: httpx.AsyncClient) -> dict:
    r = await client.get(f"{WEATHER}/two-hr-forecast")
    r.raise_for_status()
    return r.json()["data"]


nowcast = Source("weather_2hr", ttl=300, fetch=_fetch)


def area_for(data: dict, lat: float, lon: float) -> tuple[str, float]:
    """Nearest named forecast area, with how far away it is — the honest resolution."""
    best, best_km = None, float("inf")
    for a in data.get("area_metadata", []):
        loc = a["label_location"]
        km = math.dist((lat, lon), (loc["latitude"], loc["longitude"])) * 111.0
        if km < best_km:
            best, best_km = a["name"], km
    return best, round(best_km, 2)


def forecast_for(data: dict, area: str) -> str | None:
    items = data.get("items") or []
    if not items:
        return None
    for f in items[0].get("forecasts", []):
        if f["area"] == area:
            return f["forecast"]
    return None


def is_wet(text: str | None) -> bool:
    return bool(text) and text in WET
