"""Disruption alternatives (API contract §5)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import scenario, store
from ..services import alternatives as alt_service
from ..services import disruption as disruption_service

router = APIRouter()


@router.get("/trips/{trip_id}/alternatives")
async def trip_alternatives(trip_id: str):
    trip = store.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail={"error": {
            "code": "TRIP_NOT_FOUND", "message": "That trip no longer exists.",
            "retryable": False}})
    trip["trip_id"] = trip_id
    value, fetched = await scenario.alert_value()
    disruption = disruption_service.assess(value, fetched.observed_iso)
    return await alt_service.build(trip, disruption)
