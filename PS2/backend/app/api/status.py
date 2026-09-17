"""Live overlay for a trip (API contract §4) and the scenario toggle (§8)."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import data, scenario, store
from ..config import DEST_STATION, ORIGIN_STATION, SGT
from ..services import crowd as crowd_service
from ..services import disruption as disruption_service
from ..services import lifts as lift_service
from ..services import weather_policy
from ..sources import datamall, weather

router = APIRouter()


def _err(code: str, message: str, status: int = 404):
    return HTTPException(status_code=status,
                         detail={"error": {"code": code, "message": message,
                                           "retryable": False}})


def _next_check(now: datetime) -> datetime:
    """The scheduled checks are 20:00 and 07:00 (D3)."""
    today_2000 = now.replace(hour=20, minute=0, second=0, microsecond=0)
    today_0700 = now.replace(hour=7, minute=0, second=0, microsecond=0)
    for t in (today_0700, today_2000):
        if t > now:
            return t
    return today_0700 + timedelta(days=1)


async def build_status(trip: dict) -> dict:
    now = datetime.now(SGT)
    alerts, lifts_fetched = await lift_service.current_alerts()
    alert_value, alerts_fetched = await scenario.alert_value()

    for a in alerts:
        if a["source"] == "simulated":
            a["simulated_note"] = scenario.NOTE_LIFT
        a["observed_at"] = lifts_fetched.observed_iso

    disruption = disruption_service.assess(alert_value, alerts_fetched.observed_iso)

    try:
        crowd_fetched = await datamall.crowd("EWL").get()
        crowd_rows = crowd_service.for_stations(crowd_fetched.data,
                                                {ORIGIN_STATION, DEST_STATION})
        for row in crowd_rows:
            row["observed_at"] = crowd_fetched.observed_iso
        crowd_stale = crowd_fetched.stale
    except Exception:
        crowd_rows, crowd_stale = [], True

    try:
        wx_fetched = await weather.nowcast.get()
        wx = weather_policy.assess(wx_fetched.data)
        wx["observed_at"] = wx_fetched.observed_iso
        wx_stale = wx_fetched.stale
    except Exception:
        wx, wx_stale = None, True

    overall = _overall(alerts, disruption, wx)
    return {
        "trip_id": trip["trip_id"],
        "overall": overall,
        "lift_alerts": alerts,
        "disruption": disruption,
        "crowd": crowd_rows,
        "weather": wx,
        "checks": {
            "last_checked_at": now.isoformat(timespec="seconds"),
            "next_check_at": _next_check(now).isoformat(timespec="seconds"),
            "label": f"Checked {now:%H:%M}. We'll check again at {_next_check(now):%H:%M}.",
        },
        "stale": bool(lifts_fetched.stale or alerts_fetched.stale or crowd_stale or wx_stale),
        "observed_at": lifts_fetched.observed_iso,
    }


def _overall(alerts: list[dict], disruption: dict | None, wx: dict | None) -> dict:
    """The one line that must be readable in a second (API contract §4)."""
    if disruption:
        return {
            "severity": disruption["severity"],
            "headline": disruption["headline"],
            "detail": disruption["detail"],
            "action": {"kind": "view_alternatives", "label": "See your options"},
        }
    on_route = [a for a in alerts if a["affects_route"]]
    if on_route:
        a = on_route[0]
        where = a["exit_code"] or "a lift"
        return {
            "severity": "warn",
            "headline": f"A lift is out at {a['station_name']}.",
            "detail": a["detail"] + " We have planned your walk around it.",
            "action": {"kind": "view_reroute", "label": "See the new route"},
        }
    if wx and wx["rain_expected"]:
        return {"severity": "info", "headline": "Rain is forecast.",
                "detail": wx["label"],
                "action": {"kind": "view_trip", "label": "See your trip"}}
    return {"severity": "ok", "headline": "Your usual route is clear.",
            "detail": "No lift outages or delays on your way to the hospital.",
            "action": {"kind": "view_trip", "label": "See your trip"}}


@router.get("/trips/{trip_id}/status")
async def trip_status(trip_id: str):
    trip = store.get_trip(trip_id)
    if not trip:
        raise _err("TRIP_NOT_FOUND", "That trip no longer exists.")
    return await build_status(trip)


class ScenarioRequest(BaseModel):
    enabled: bool | None = None
    lift_outage_outram: bool | None = None
    ewl_disruption: bool | None = None


@router.get("/scenario")
def get_scenario():
    return scenario.state()


@router.post("/scenario")
def set_scenario(req: ScenarioRequest):
    return scenario.set_state(**req.model_dump())
