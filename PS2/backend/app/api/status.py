"""Live overlay for a trip (API contract §4) and the scenario toggle (§8)."""
from __future__ import annotations

import json
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


def _blocked_signature(blocked: dict[str, set[str]]) -> str:
    return json.dumps({k: sorted(v) for k, v in sorted(blocked.items())})


def route_key(plan: dict) -> list:
    """The parts of a plan a reroute actually changes — the doors and the clock."""
    doors = [(leg.get(end) or {}).get("exit_code")
             for leg in plan.get("legs", []) for end in ("from", "to")]
    return [doors, plan.get("summary", {}).get("leave_by")]


async def refresh_plan(trip: dict, alerts: list[dict]) -> bool:
    """Derive the effective plan for the outages known right now (D7, F07).

    The stored `plan_original` is never overwritten, and the effective plan is
    re-derived from it rather than from the last rerouted one. That is what makes
    a reroute reversible: when the outage clears, the next call plans with no
    blocked exits and lands back on the original.

    Returns whether the effective plan differs from the original — "we moved
    you" is a statement about the route she is being given, not about whether
    *this* call happened to re-plan.
    """
    blocked, access = lift_service.blocked_exits(alerts)
    signature = _blocked_signature(blocked)
    if trip["plan"].get("blocked_signature") == signature:
        return bool(trip["plan"].get("rerouted"))

    original = trip.get("plan_original") or trip["plan"]
    from ..services import planner
    prefs = trip.get("preferences") or {}
    appointment = datetime.fromisoformat(original["appointment_at"])
    plan = planner.plan_trip(
        trip["origin"], appointment,
        pace=prefs.get("walking_pace", "slow"),
        buffer_min=prefs.get("buffer_min", planner.DEFAULT_BUFFER_MIN),
        prefer_sheltered=prefs.get("prefer_sheltered", False),
        blocked_exits=blocked, access=access)

    rerouted = route_key(plan) != route_key(original)
    plan["rerouted"] = rerouted
    plan["blocked_signature"] = signature
    trip["plan"] = plan
    store.update_plan(trip["trip_id"], plan)
    return rerouted


async def build_status(trip: dict) -> dict:
    now = datetime.now(SGT)
    alerts, lifts_fetched = await lift_service.current_alerts()
    rerouted = await refresh_plan(trip, alerts)
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

    overall = _overall(alerts, disruption, wx, rerouted, trip["plan"])
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
        "rerouted": rerouted,
        "stale": bool(lifts_fetched.stale or alerts_fetched.stale or crowd_stale or wx_stale),
        "observed_at": lifts_fetched.observed_iso,
    }


def _overall(alerts: list[dict], disruption: dict | None, wx: dict | None,
             rerouted: bool = False, plan: dict | None = None) -> dict:
    """The one line that must be readable in a second (API contract §4).

    "Your route does not use it" is a safety claim, so it is only made where it
    can be checked: a `matched_exit` outage whose doors the plan provably avoids
    (F01). An outage that names no exit (`station_only`) or names one this
    station does not have (`unmatched`) cannot be placed on or off her path —
    Outram Park is a three-line interchange, so a concourse lift there may well
    be on her step-free route. Those say so and ask her to check.
    """
    if disruption:
        return {
            "severity": disruption["severity"],
            "headline": disruption["headline"],
            "detail": disruption["detail"],
            "action": {"kind": "view_alternatives", "label": "See your options"},
        }
    on_route = [a for a in alerts if a["affects_route"]]
    if on_route:
        matched = [a for a in on_route if a["resolution"] == "matched_exit"]
        uncertain = [a for a in on_route if a["resolution"] in ("station_only", "unmatched")]
        a = (matched or on_route)[0]
        headline = f"A lift is out at {a['station_name']}."

        still_used = []
        if plan:
            for alert in matched:
                one, _ = lift_service.blocked_exits([alert])
                if lift_service.plan_uses_blocked_exit(plan, one):
                    still_used.append(alert)

        if still_used:
            # We know the door is out and could not move her off it. Never soften.
            return {
                "severity": "critical",
                "headline": headline,
                "detail": (still_used[0]["detail"] + " Your route still uses it and we "
                           "could not find another step-free way in. Please check before "
                           "you go."),
                "action": {"kind": "view_alternatives", "label": "See your options"},
            }
        if rerouted:
            detail = a["detail"] + " We have moved you to another exit."
            if uncertain:
                detail += (" Another lift there is also out and we cannot tell which exit "
                           "it serves.")
            return {"severity": "warn", "headline": headline, "detail": detail,
                    "action": {"kind": "view_reroute", "label": "See the new route"}}
        if uncertain:
            u = uncertain[0]
            return {
                "severity": "warn",
                "headline": headline,
                "detail": (u["detail"] + " We cannot tell which exit it serves, so it may "
                           "affect your route. Please check before you go."),
                "action": {"kind": "view_trip", "label": "See your trip"},
            }
        return {
            "severity": "warn",
            "headline": headline,
            "detail": a["detail"] + " Your route does not use it.",
            "action": {"kind": "view_trip", "label": "See your trip"},
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
