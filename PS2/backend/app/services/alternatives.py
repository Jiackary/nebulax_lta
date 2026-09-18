"""The three options she gets during an EWL disruption (D2, API contract §5).

Each option is shown *against* the original so she can judge the trade-off
(PS2_README.md:L264), and each says why in a sentence.

  1. Leave later — offered only when the parsed delay fits inside her buffer.
     Her usual step-free route is unchanged, which is the best outcome for
     someone who does not want to improvise.
  2. Accessible bus — a single-bus ride, no transfers. Checked live for
     `Feature=WAB` and its `Load`, with `Monitored` surfaced honestly as
     "scheduled" rather than implied live tracking (T10).
  3. Barrier-free taxi — the nearest `TaxiStands` entry flagged `Bfa`, anchored
     at the station her current leg is heading to (I7). No fare estimate: we
     cannot verify one, so we do not print one.

Free bridging buses and MRT shuttles are deliberately not offered (D2), and the
reason is returned rather than hidden.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import data
from ..config import DEST_STATION, ORIGIN_STATION, SGH, SGT
from ..sources import datamall, onemap
from .walking import haversine

# Beyond this, a live bus arrival describes a bus she will not be on (F23).
LIVE_ARRIVAL_WINDOW_MIN = 30


class _NotNow(Exception):
    """Live arrival data is not applicable to this departure."""


LOAD_LABELS = {"SEA": ("Seats available", "ok"),
               "SDA": ("Standing available", "info"),
               "LSD": ("Limited standing", "warn")}


async def _bus_option(appointment: datetime, origin_coord: list[float]) -> dict | None:
    """A single-bus ride to the hospital, with no transfers.

    *Which* bus comes from `bus_options.json`, derived at build time by
    intersecting `BusRoutes` services that stop near Bedok with those that stop
    near SGH. Four exist, and two of them alight at SGH Block 3 itself.

    *How long it takes* comes from OneMap's public-transport router when it
    offers a matching single-bus itinerary. When it does not — its results vary
    and it returns at most three — we still offer the bus, but we say the
    journey time is unknown rather than inventing one.
    """
    direct = data.bus_options().get("direct", [])
    if not direct:
        return None
    # Fewest stops first; two of the four alight at SGH Block 3, which is where
    # she is actually going.
    by_service = {o["service_no"]: o for o in direct}

    def preference(o: dict) -> tuple:
        # Alighting at Block 3 is worth more to her than a few minutes saved.
        return (0 if "BLK 3" in o["alight"]["name"].upper() else 1, o["stops"])

    # Prefer a service OneMap can actually time for this departure, so the
    # number we show is measured rather than asserted.
    timed: dict[str, dict] = {}
    try:
        plan = await onemap.pt_route(origin_coord, SGH["coord"], appointment)
        for it in (plan.get("plan") or {}).get("itineraries", []):
            legs = [l for l in it["legs"] if l["mode"] == "BUS"]
            if len(legs) != 1:
                continue
            route_no = str(legs[0].get("route") or "")
            if route_no in by_service and route_no not in timed:
                timed[route_no] = {"duration_min": round(it["duration"] / 60),
                                   "ride_min": round(legs[0]["duration"] / 60),
                                   "walk_min": round(it["walkTime"] / 60)}
    except Exception:
        pass

    pool = [by_service[n] for n in timed] or direct
    chosen = sorted(pool, key=preference)[0]
    service_no = chosen["service_no"]
    board_code = chosen["board"]["code"]

    t = timed.get(service_no, {})
    duration_min = t.get("duration_min")
    ride_min = t.get("ride_min")
    walk_min = t.get("walk_min")
    basis = ("Journey time from OneMap's public-transport route for this departure; "
             "arrival and load read live from LTA." if duration_min else
             f"{chosen['stops']} stops, {chosen['distance_km']} km, from LTA's route data. "
             f"Journey time not stated: we have no verified figure for it.")

    live = {"eta_min": None, "eta_is_scheduled": None, "load": None,
            "load_label": None, "wheelchair_accessible": None,
            "not_running": False, "observed_at": None, "stale": None}
    # A live arrival describes a bus leaving now. For a trip later today it says
    # nothing useful, and "Not running now; first bus 0530" read at 01:03 for a
    # 15:00 appointment is simply wrong (F23).
    minutes_away = (appointment - datetime.now(SGT)).total_seconds() / 60
    live_is_relevant = minutes_away <= LIVE_ARRIVAL_WINDOW_MIN
    try:
        if not live_is_relevant:
            raise _NotNow
        fetched = await datamall.bus_arrival(board_code).get()
        services = fetched.data
        live["observed_at"] = fetched.observed_iso
        # Recorded fixtures are real responses, but they are not current (F22).
        live["stale"] = bool(fetched.stale)
        if fetched.stale:
            raise _NotNow
        row = next((s for s in services if s.get("ServiceNo") == service_no), None)
        if not services:
            # T17: nothing at all is returned outside operating hours. Absence is
            # not an error, and must not be shown as "no buses ever".
            live["not_running"] = True
        elif row and (row.get("NextBus") or {}).get("EstimatedArrival"):
            nb = row["NextBus"]
            eta = datetime.fromisoformat(nb["EstimatedArrival"])
            live["eta_min"] = max(0, round((eta - datetime.now(SGT)).total_seconds() / 60))
            live["eta_is_scheduled"] = nb.get("Monitored") == 0
            live["load"] = nb.get("Load")
            live["load_label"] = LOAD_LABELS.get(nb.get("Load", ""), (None, "info"))[0]
            live["wheelchair_accessible"] = nb.get("Feature") == "WAB"
        else:
            live["not_running"] = True
    except _NotNow:
        pass
    except Exception:
        pass

    why = f"One bus, no changes, from {chosen['board']['name']}."
    if "BLK 3" in chosen["alight"]["name"].upper():
        why += " It sets you down at Block 3, where your appointment is."
    if live["wheelchair_accessible"]:
        why += " The next bus has a wheelchair ramp."
    elif live["wheelchair_accessible"] is False:
        why += " The next bus has no wheelchair ramp; the one after may."
    if live["load_label"]:
        why += f" {live['load_label']}."
    if live["not_running"]:
        why += f" Not running now; first bus {chosen['board']['first_bus']}."

    return {
        "option_id": "bus_wab", "mode": "bus",
        "label": f"Bus {service_no} from {chosen['board']['name']}",
        "why": why,
        "duration_min": duration_min,
        # The bus is step-free only if this vehicle is wheelchair-accessible;
        # unknown is not yes (F23).
        "step_free": ("yes" if live["wheelchair_accessible"] is True
                      else "no" if live["wheelchair_accessible"] is False
                      else "unknown"),
        "severity": "info",
        "bus": {"service_no": service_no,
                "board_stop": chosen["board"]["name"], "board_stop_code": board_code,
                "alight_stop": chosen["alight"]["name"],
                "alight_stop_code": chosen["alight"]["code"],
                "stops": chosen["stops"], "distance_km": chosen["distance_km"],
                "first_bus": chosen["board"]["first_bus"],
                "last_bus": chosen["board"]["last_bus"],
                "ride_min": ride_min, "walk_min": walk_min, **live},
        "timing_basis": basis,
        "legs": [],
    }


async def _taxi_option(anchor_code: str) -> dict | None:
    """Nearest barrier-free stand to the station this leg is heading to (I7)."""
    try:
        stands = (await datamall.taxi_stands.get()).data
    except Exception:
        return None
    station = data.station_by_code().get(anchor_code)
    if not station:
        return None
    lon, lat = station["coord"]
    bfa = [s for s in stands if s.get("Bfa") == "Yes"]
    if not bfa:
        return None
    nearest = min(bfa, key=lambda s: haversine(lat, lon, s["Latitude"], s["Longitude"]))
    distance = round(haversine(lat, lon, nearest["Latitude"], nearest["Longitude"]))
    return {
        "option_id": "taxi_bfa", "mode": "taxi",
        "label": f"Barrier-free taxi from {nearest.get('Name', 'the taxi stand')}",
        "why": (f"The nearest barrier-free taxi stand to {station['name']}, "
                f"{distance} m away."),
        "step_free": "yes",
        "severity": "info",
        "taxi_stand": {"name": nearest.get("Name"), "barrier_free": True,
                       "distance_m": distance, "anchor": anchor_code,
                       "coord": [nearest["Longitude"], nearest["Latitude"]],
                       "fare_estimate": None},
        "timing_basis": "No fare or arrival estimate: we cannot verify either.",
        "legs": [],
    }


def _departure_option(plan: dict, delay_min: int | None, buffer_min: int) -> dict | None:
    """Keep her usual step-free route, and adjust when she sets off.

    D2.1 offers "leave later" when the delay fits her buffer. When it does not,
    the useful advice for a trip she has not started yet is the mirror image —
    leave earlier — so both are served here. The option_id says which, because
    the frontend words them differently.
    """
    if not delay_min:
        return None
    leave = datetime.fromisoformat(plan["summary"]["leave_by"])
    arrive_late = datetime.fromisoformat(plan["summary"]["arrival_window"][1])

    if delay_min <= buffer_min:
        return {
            "option_id": "leave_later", "mode": "rail",
            "label": "Keep your usual route",
            "why": (f"The {delay_min}-minute delay fits inside the {buffer_min} minutes you "
                    f"keep spare, so your usual step-free route still gets you there in time."),
            "delta_min": 0,
            "leave_by": leave.isoformat(timespec="seconds"),
            "leave_by_label": f"Leave at {leave:%H:%M} as planned",
            "arrival_at": (arrive_late + timedelta(minutes=delay_min)).isoformat(timespec="seconds"),
            "step_free": "yes", "severity": "ok",
            "timing_basis": f"Your planned time plus the {delay_min} minutes LTA has advised.",
            "legs": [],
        }

    # Shift by the whole delay, not by the delay less the buffer: absorbing the
    # buffer landed her within a minute of the appointment while the text said
    # "still in time" (F24).
    earlier = leave - timedelta(minutes=delay_min)
    now = datetime.now(SGT)
    if earlier < now:
        # The advice has already expired; offering it is worse than saying so.
        return {
            "option_id": "leave_earlier", "mode": "rail",
            "label": "Leaving earlier is no longer possible",
            "why": (f"Setting off early enough to absorb the {delay_min}-minute delay "
                    f"would have meant leaving at {earlier:%H:%M}, which has passed. "
                    f"The other options below still stand."),
            "delta_min": None,
            "leave_by": None,
            "leave_by_label": None,
            "arrival_at": None,
            "viable": False,
            "step_free": "yes", "severity": "warn",
            "timing_basis": (f"Your planned departure less the {delay_min} minutes LTA "
                             f"has advised, compared with the time now."),
            "legs": [],
        }
    return {
        "option_id": "leave_earlier", "mode": "rail",
        "label": f"Leave {delay_min} minutes earlier",
        "why": (f"The {delay_min}-minute delay is longer than the {buffer_min} minutes you "
                f"keep spare, so setting off at {earlier:%H:%M} keeps you on your usual "
                f"step-free route and keeps your {buffer_min} minutes spare."),
        "delta_min": 0,
        "leave_by": earlier.isoformat(timespec="seconds"),
        "leave_by_label": f"Leave at {earlier:%H:%M} instead",
        "arrival_at": arrive_late.isoformat(timespec="seconds"),
        "viable": True,
        "step_free": "yes", "severity": "info",
        "timing_basis": (f"Your planned time, shifted earlier by the full {delay_min} "
                         f"minutes LTA has advised, so your buffer stays intact."),
        "legs": [],
    }


async def build(trip: dict, disruption: dict | None) -> dict:
    plan = trip["plan"]
    buffer_min = plan["summary"].get("buffer_min", 15)
    appointment = datetime.fromisoformat(plan["appointment_at"])
    delay = (disruption or {}).get("delay_min")
    base_duration = plan["summary"]["duration_min"]
    arrive_late = datetime.fromisoformat(plan["summary"]["arrival_window"][1])

    original = {
        "label": "Your usual route",
        "duration_min": base_duration,
        "arrival_at": (arrive_late + timedelta(minutes=delay or 0)).isoformat(timespec="seconds"),
        "viable": True,
        "step_free": plan["summary"]["step_free"],
        "note": (f"Now about {delay} minutes slower." if delay
                 else "Running normally."),
    }

    options = []
    later = _departure_option(plan, delay, buffer_min)
    if later:
        options.append(later)
    bus = await _bus_option(appointment, trip["origin"]["coord"])
    if bus:
        options.append(bus)
    # I7: "the station the current leg is heading to". Before departure that is
    # her origin — she is still in Bedok, which is the main case for a
    # pre-departure disruption (F25).
    departed = datetime.now(SGT) >= datetime.fromisoformat(plan["summary"]["leave_by"])
    taxi = await _taxi_option(DEST_STATION if departed else ORIGIN_STATION)
    if taxi:
        options.append(taxi)

    # Rank and express every option against the original, signed (contract §5).
    delayed_original = base_duration + (delay or 0)
    for opt in options:
        if opt.get("duration_min") is not None:
            opt["delta_min"] = opt["duration_min"] - delayed_original
        elif "delta_min" not in opt:
            opt["delta_min"] = None
    for rank, opt in enumerate(options, start=1):
        opt["rank"] = rank

    not_offered = [{
        "label": "Free bridging bus",
        "why_not": ("These run crowded with standing room only, which is the wrong trade "
                    "for a slow walker who needs a seat."),
    }]
    if (disruption or {}).get("free_bus_available"):
        not_offered[0]["note"] = "LTA has activated free bus travel for this disruption."

    return {
        "trip_id": trip["trip_id"],
        "disruption": disruption,
        "original": original,
        "options": options,
        "not_offered": not_offered,
    }
