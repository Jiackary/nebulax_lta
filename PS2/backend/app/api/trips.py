"""Trip planning endpoints (API contract §3, §6)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import data, store
from ..config import ATTRIBUTION, HOME_DEFAULT, SGT, SGH
from ..services import planner
from ..sources import onemap

router = APIRouter()


class Preferences(BaseModel):
    walking_pace: str = "slow"
    avoid_stairs: bool = True
    prefer_sheltered: bool = True
    buffer_min: int = planner.DEFAULT_BUFFER_MIN


class Origin(BaseModel):
    label: str = HOME_DEFAULT["label"]
    coord: list[float] = Field(default_factory=lambda: list(HOME_DEFAULT["coord"]))


class TripRequest(BaseModel):
    origin: Origin = Field(default_factory=Origin)
    destination_id: str = "SGH"
    appointment_at: datetime
    preferences: Preferences = Field(default_factory=Preferences)


def _err(code: str, message: str, status: int = 400, retryable: bool = False):
    return HTTPException(status_code=status,
                         detail={"error": {"code": code, "message": message,
                                           "retryable": retryable}})


def build_plan(origin: dict, appointment: datetime, prefs: dict) -> dict:
    """Plan, then let the live overlay revise the exits if a lift is out (D7)."""
    from ..services import lifts as lift_service
    blocked, access = lift_service.blocked_exits_sync()
    plan = planner.plan_trip(
        origin, appointment,
        pace=prefs.get("walking_pace", "slow"),
        buffer_min=prefs.get("buffer_min", planner.DEFAULT_BUFFER_MIN),
        prefer_sheltered=prefs.get("prefer_sheltered", False),
        blocked_exits=blocked, access=access)
    return plan


@router.post("/trips")
def create_trip(req: TripRequest):
    if req.destination_id != "SGH":
        raise _err("INVALID_REQUEST",
                   "This app plans one journey: home to Singapore General Hospital.")
    origin = req.origin.model_dump()
    prefs = req.preferences.model_dump()
    try:
        plan = build_plan(origin, req.appointment_at, prefs)
    except RuntimeError as exc:
        raise _err("INVALID_REQUEST", str(exc))
    trip_id = store.save_trip(req.appointment_at, origin, prefs, plan)
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
    try:
        return {"results": await onemap.search(q), "source": "OneMap"}
    except onemap.OneMapAuthError as exc:
        raise _err("UPSTREAM_UNAVAILABLE",
                   f"Address search is unavailable: {exc}", status=503, retryable=True)


@router.get("/destinations")
def destinations():
    return {"destinations": [{"id": "SGH", "label": SGH["label"], "block": SGH["block"],
                              "coord": SGH["coord"]}]}
