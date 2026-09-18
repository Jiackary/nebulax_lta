"""The offline bundle for her underground leg (API contract §6, D6).

She is underground for 31 minutes with no signal (T15). The brief requires us to
state what the app does about that, so: everything she needs is fetched before
she goes under, and nothing live is presented as current once she is.

Map tiles are deliberately absent. `tile.openstreetmap.org` prohibits bulk
downloading and offline caching outright (PS2_README.md:L57), and no permitting
provider has been chosen (issue I6, parked). `tile_pack_url` is therefore null
and the offline screen degrades to large plain text — which is the more useful
thing for this persona anyway.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from .. import store
from . import schemas
from ..config import SGT
from .status import build_status

router = APIRouter()


def steps_plain(plan: dict) -> list[str]:
    """The offline screen: one sentence per leg, large text, no map needed."""
    out = []
    for leg in plan["legs"]:
        line = leg["instruction"]
        if leg["mode"] == "rail" and leg.get("duration_min"):
            line = line.rstrip(".") + f", about {leg['duration_min']} minutes."
        out.append(line)
    return out


@router.get("/trips/{trip_id}/offline", response_model=schemas.OfflineBundle,
             response_model_exclude_unset=True,
             responses=schemas.ERROR_RESPONSES)
async def offline_bundle(trip_id: str):
    trip = store.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail={"error": {
            "code": "TRIP_NOT_FOUND", "message": "That trip no longer exists.",
            "retryable": False}})
    trip["trip_id"] = trip_id
    now = datetime.now(SGT)
    warnings: list[str] = []
    try:
        snapshot = await build_status(trip)   # may re-plan around a new outage
    except Exception:
        snapshot = None

    plan = trip["plan"]          # refresh_plan may have replaced this during build_status

    # Never hand her written steps with no idea whether they still hold (F06).
    # Walking her through a door whose lift is out is the failure this bundle
    # exists to prevent, so the absence of a check is itself the warning.
    if snapshot is None:
        warnings.append("We could not check for lift outages or delays just now. "
                        "These steps are your last plan and may be out of date.")
    else:
        if snapshot.get("replan_failed"):
            warnings.append(snapshot["overall"]["detail"])
        elif snapshot["overall"]["severity"] in ("warn", "critical"):
            warnings.append(snapshot["overall"]["detail"])

    return {
        "trip_id": trip_id,
        "generated_at": now.isoformat(timespec="seconds"),
        "plan": plan,
        "status_snapshot": snapshot,
        "warnings": warnings,
        "steps_plain": (warnings + steps_plain(plan)) if warnings else steps_plain(plan),
        "tiles": {
            "style_url": None,
            "tile_pack_url": None,
            "attribution": "© OpenStreetMap contributors",
            "zoom_range": [13, 17],
            "unavailable_reason": ("No tile provider whose terms permit offline caching has "
                                   "been chosen. The offline screen shows written steps."),
        },
        "offline_notice": (f"No signal: plan as of {now:%H:%M}. Times may have changed."),
        "attribution": plan["attribution"],
    }
