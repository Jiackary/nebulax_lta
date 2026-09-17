"""LTA DataMall adapters. TTLs from backend plan §6, confirmed live 17 Sep.

Traps handled here so no caller has to think about them:
  T2  TrainServiceAlerts `value` is an OBJECT, not an array.
  T3  Status:1 does not mean all-clear — test AffectedSegments, not Status.
  T18 A missing key returns 404 (same as a wrong URL); a wrong key returns 401.
  T17 Bus Arrival returns nothing outside operating hours. Absence is not error.
"""
from __future__ import annotations

import httpx

from ..config import DATAMALL, LTA_ACCOUNT_KEY
from .base import Source


class DataMallAuthError(RuntimeError):
    pass


async def _get(client: httpx.AsyncClient, endpoint: str, **params) -> dict:
    if not LTA_ACCOUNT_KEY:
        raise DataMallAuthError("LTA_ACCOUNT_KEY is not set")
    r = await client.get(f"{DATAMALL}/{endpoint}", params=params or None,
                         headers={"AccountKey": LTA_ACCOUNT_KEY})
    # T18, re-measured 17 Sep 2026 — the trap is only half true now. A *wrong*
    # key returns a clean 401 with an empty body. A *missing or empty* key still
    # returns 404 "The requested API was not found", which is byte-identical to
    # what a genuinely wrong endpoint returns. So 404 stays ambiguous; 401 does not.
    if r.status_code == 401:
        raise DataMallAuthError(
            f"{endpoint}: 401 — the AccountKey was rejected. Check it at datamall.lta.gov.sg")
    if r.status_code == 404:
        raise DataMallAuthError(
            f"{endpoint}: 404 'The requested API was not found'. DataMall returns this "
            f"both for a missing AccountKey and for a wrong endpoint — check the header "
            f"is being sent before assuming the URL is wrong")
    r.raise_for_status()
    return r.json()


async def _fetch_lifts(client: httpx.AsyncClient) -> list[dict]:
    return (await _get(client, "v2/FacilitiesMaintenance")).get("value", [])


async def _fetch_alerts(client: httpx.AsyncClient) -> dict:
    payload = await _get(client, "TrainServiceAlerts")
    value = payload.get("value")
    # T2: `value` is an object here, unlike every other DataMall endpoint.
    if isinstance(value, list):
        value = value[0] if value else {}
    return value or {}


async def _fetch_crowd(line: str):
    async def inner(client: httpx.AsyncClient) -> list[dict]:
        return (await _get(client, "PCDRealTime", TrainLine=line)).get("value", [])
    return inner


async def _fetch_taxi_stands(client: httpx.AsyncClient) -> list[dict]:
    return (await _get(client, "TaxiStands")).get("value", [])


lifts = Source("facilities_maintenance", ttl=60, fetch=_fetch_lifts)
alerts = Source("train_service_alerts", ttl=60, fetch=_fetch_alerts)
taxi_stands = Source("taxi_stands", ttl=24 * 3600, fetch=_fetch_taxi_stands)

_crowd_sources: dict[str, Source] = {}


def crowd(line: str = "EWL") -> Source:
    if line not in _crowd_sources:
        async def inner(client: httpx.AsyncClient, _line=line) -> list[dict]:
            return (await _get(client, "PCDRealTime", TrainLine=_line)).get("value", [])
        _crowd_sources[line] = Source(f"crowd_{line.lower()}", ttl=600, fetch=inner)
    return _crowd_sources[line]


_bus_sources: dict[str, Source] = {}


def bus_arrival(stop_code: str) -> Source:
    """v3/BusArrival. T17: an empty Services list is normal outside operating hours."""
    if stop_code not in _bus_sources:
        async def inner(client: httpx.AsyncClient, _code=stop_code) -> list[dict]:
            payload = await _get(client, "v3/BusArrival", BusStopCode=_code)
            return payload.get("Services", [])
        _bus_sources[stop_code] = Source(f"bus_{stop_code}", ttl=20, fetch=inner)
    return _bus_sources[stop_code]


def alerts_are_clear(value: dict) -> bool:
    """T3: recovery leaves the segment in place with Stations:"" while free bus
    and shuttle stay populated, so `Status` is not the signal. Emptiness of
    AffectedSegments is."""
    segments = value.get("AffectedSegments") or []
    return not any((s.get("Stations") or "").strip() for s in segments)
