"""Trip planning endpoints (API contract §3, §6)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conlist, field_validator

from .. import data, store
from ..config import ATTRIBUTION, HOME_DEFAULT, SGT, SGH, USE_FIXTURES
from ..services import planner, timing
from ..sources import onemap

router = APIRouter()


# An appointment outside this window is a typo, not a plan (F15). Generous on
# both sides: she may well book a year out.
MAX_APPOINTMENT_DAYS = 400
# Exactly the keys of `timing.PACE`. Inventing names here would 422 a pace the
# planner supports, and silently fall back to slow for one it does not (F15).
PACES = tuple(timing.PACE)


class Preferences(BaseModel):
    # "sprint" used to be accepted, stored, and silently planned as slow.
    walking_pace: Literal[PACES] = "slow"
    avoid_stairs: bool = True
    prefer_sheltered: bool = True
    # A negative buffer produced a leave-by *after* the appointment; 1e12
    # overflowed into a 500.
    buffer_min: int = Field(planner.DEFAULT_BUFFER_MIN, ge=0, le=120)


class Origin(BaseModel):
    label: str = Field(default=HOME_DEFAULT["label"], max_length=200)
    # A bare list let [], [103.93] and [x, y, z] through to a TypeError and a
    # plain-text 500.
    coord: conlist(float, min_length=2, max_length=2) = Field(
        default_factory=lambda: list(HOME_DEFAULT["coord"]))

    @field_validator("coord")
    @classmethod
    def coord_is_on_earth(cls, value: list[float]) -> list[float]:
        lon, lat = value
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("coord must be [longitude, latitude] in degrees")
        return value


class TripRequest(BaseModel):
    origin: Origin = Field(default_factory=Origin)
    destination_id: str = "SGH"
    appointment_at: datetime
    preferences: Preferences = Field(default_factory=Preferences)

    @field_validator("appointment_at")
    @classmethod
    def appointment_in_singapore_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=SGT)
        else:
            value = value.astimezone(SGT)
        now = datetime.now(SGT)
        if value < now - timedelta(minutes=1):
            raise ValueError("appointment_at is in the past")
        if value > now + timedelta(days=MAX_APPOINTMENT_DAYS):
            raise ValueError(
                f"appointment_at is more than {MAX_APPOINTMENT_DAYS} days away")
        return value


def _err(code: str, message: str, status: int = 400, retryable: bool = False):
    return HTTPException(status_code=status,
                         detail={"error": {"code": code, "message": message,
                                           "retryable": retryable}})


def build_plan(origin: dict, appointment: datetime, prefs: dict) -> tuple[dict, dict]:
    """Plan, then let the live overlay revise the exits if a lift is out (D7).

    Returns `(effective, baseline)`. The baseline is the clear-day route, planned
    with nothing blocked, and it is what gets stored as `plan_original`: if an
    outage that was live at creation were baked into the original, clearing it
    would read as a reroute in the wrong direction (F07).
    """
    from ..services import lifts as lift_service
    blocked, access = lift_service.blocked_exits_sync()

    def _plan(blocked_exits, access_info):
        return planner.plan_trip(
            origin, appointment,
            pace=prefs.get("walking_pace", "slow"),
            buffer_min=prefs.get("buffer_min", planner.DEFAULT_BUFFER_MIN),
            prefer_sheltered=prefs.get("prefer_sheltered", False),
            blocked_exits=blocked_exits, access=access_info)

    effective = _plan(blocked, access)
    baseline = _plan({}, None) if blocked else effective
    return effective, baseline


@router.post("/trips")
def create_trip(req: TripRequest):
    if req.destination_id != "SGH":
        raise _err("INVALID_REQUEST",
                   "This app plans one journey: home to Singapore General Hospital.")
    origin = req.origin.model_dump()
    prefs = req.preferences.model_dump()
    try:
        plan, baseline = build_plan(origin, req.appointment_at, prefs)
    except RuntimeError as exc:
        raise _err("INVALID_REQUEST", str(exc))
    trip_id = store.save_trip(req.appointment_at, origin, prefs, plan, baseline)
    return {"trip_id": trip_id, **plan}


@router.get("/trips/{trip_id}")
def get_trip(trip_id: str):
    trip = store.get_trip(trip_id)
    if not trip:
        raise _err("TRIP_NOT_FOUND", "That trip no longer exists.", status=404)
    return {"trip_id": trip_id, **trip["plan"]}


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: str):
    if not store.delete_trip(trip_id):
        raise _err("TRIP_NOT_FOUND", "That trip no longer exists.", status=404)
    return {"deleted": True,
            "note": "The trip and its server copy are gone."}


@router.get("/places/search")
async def places_search(q: str):
    """Address autocomplete, via OneMap (I9).

    A token failure is reported as a token failure — an empty list here would
    read as 'no such address', which is a different and misleading thing.
    """
    if len(q.strip()) < 3:
        return {"results": []}
    if USE_FIXTURES:
        # PS2_USE_FIXTURES=1 means no network, and OneMap ignored it entirely (F16).
        raise _err("UPSTREAM_UNAVAILABLE",
                   "Address search needs the network; this server is running offline "
                   "from recorded fixtures.", status=503, retryable=False)
    try:
        return {"results": await onemap.search(q), "source": "OneMap"}
    except onemap.OneMapAuthError as exc:
        raise _err("UPSTREAM_UNAVAILABLE",
                   f"Address search is unavailable: {exc}", status=503, retryable=True)
    except (httpx.HTTPError, ValueError) as exc:
        # A timeout, connection error, 5xx or non-JSON body used to be a 500.
        raise _err("UPSTREAM_UNAVAILABLE",
                   f"Address search is unavailable: {type(exc).__name__}",
                   status=503, retryable=True)


@router.get("/destinations")
def destinations():
    return {"destinations": [{"id": "SGH", "label": SGH["label"], "block": SGH["block"],
                              "coord": SGH["coord"]}]}
