"""What a scheduled check finds, and what it would say (D3, D4).

The wording matters as much as the delivery. We *detect*, we do not predict
(§6 limitation 1): the feed carries no dates, so a check sees only what is
broken at that moment, and the message says when we last looked and when we
will look again.

One line of body. If it is worth interrupting her for, it is worth saying in
one line.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from ..config import SGT
from . import lifts as lift_service
from .. import scenario
from . import disruption as disruption_service


async def check_trip(trip: dict) -> dict | None:
    """-> the push payload if something on her route changed, else None."""
    alerts, _ = await lift_service.current_alerts()
    on_route = [a for a in alerts if a["affects_route"]]

    value, fetched = await scenario.alert_value()
    disruption = disruption_service.assess(value, fetched.observed_iso)

    if not on_route and not disruption:
        return None

    if disruption:
        delay = disruption.get("delay_min")
        title = disruption["headline"]
        body = (f"About {delay} more minutes on your way to the hospital. "
                f"Tap to see your options." if delay
                else "Tap to see your options.")
    else:
        a = on_route[0]
        title = f"Lift out at {a['station_name']}"
        if a["resolution"] == "matched_exit":
            body = f"{a['exit_code']}'s lift is out. We have moved you to another exit."
        else:
            body = "A lift at this station is out. We have checked your route."

    payload = {
        "title": title,
        "body": body,
        "trip_id": trip["trip_id"],
        "severity": "critical" if disruption else "warn",
        "url": f"/trip/{trip['trip_id']}",
        "sent_at": datetime.now(SGT).isoformat(timespec="seconds"),
    }
    payload["digest"] = hashlib.sha256(
        json.dumps([title, body], sort_keys=True).encode()).hexdigest()[:16]
    return payload
