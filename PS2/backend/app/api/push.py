"""Web Push subscribe/unsubscribe/test (API contract §7, D4)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import store
from ..config import VAPID_CLAIM_EMAIL, VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
from ..services import notify

router = APIRouter()


class Subscription(BaseModel):
    endpoint: str
    keys: dict


class SubscribeRequest(BaseModel):
    subscription: Subscription
    trip_ids: list[str] = []


def send_push(subscription: dict, payload: dict) -> tuple[bool, str | None]:
    """Deliver one notification. Returns (sent, error)."""
    if not VAPID_PRIVATE_KEY:
        return False, "VAPID_PRIVATE_KEY is not set"
    try:
        from pywebpush import webpush
        webpush(subscription_info=subscription, data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL})
        return True, None
    except Exception as exc:
        return False, str(exc)


@router.get("/push/key")
def push_key():
    """The browser needs the public key to subscribe. Never the private one."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail={"error": {
            "code": "UPSTREAM_UNAVAILABLE",
            "message": "Push is not configured on this server.", "retryable": False}})
    return {"public_key": VAPID_PUBLIC_KEY}


@router.post("/push/subscribe")
def subscribe(req: SubscribeRequest):
    store.save_subscription(req.subscription.endpoint, req.subscription.keys, req.trip_ids)
    return {"subscribed": True,
            "checks": ["20:00 the evening before", "07:00 on the day"]}


@router.delete("/push/subscribe")
def unsubscribe(endpoint: str | None = None):
    """Unsubscribing also deletes her stored trips (privacy commitment 1)."""
    result = store.delete_subscription(endpoint)
    return {"unsubscribed": True, **result,
            "note": "Your saved trips have been deleted from the server."}


@router.post("/push/test")
async def push_test(trip_id: str | None = None):
    """Fire the real check-and-send path now, so judges need not wait for 20:00.

    If no browser has subscribed we still return the payload that *would* have
    been sent, rather than a bare success that shows nothing.
    """
    trips = [store.get_trip(trip_id)] if trip_id else store.all_trips()
    trips = [t for t in trips if t]
    if not trips:
        raise HTTPException(status_code=404, detail={"error": {
            "code": "TRIP_NOT_FOUND", "message": "Plan a trip first.", "retryable": False}})
    trip = trips[0]
    trip.setdefault("trip_id", trip_id or trip["trip_id"])

    payload = await notify.check_trip(trip)
    if not payload:
        payload = {
            "title": "Your usual route is clear",
            "body": "No lift outages or delays on your way to the hospital.",
            "trip_id": trip["trip_id"], "severity": "ok",
            "url": f"/trip/{trip['trip_id']}",
        }

    subs = [sub for sub in store.subscriptions()
            if trip["trip_id"] in sub["trip_ids"]]
    results = []
    for sub in subs:
        sent, error = send_push({"endpoint": sub["endpoint"], "keys": sub["keys"]}, payload)
        results.append({"endpoint": sub["endpoint"][:48] + "…", "sent": sent, "error": error})

    return {
        "sent": any(r["sent"] for r in results),
        "subscriptions": len(subs),
        "results": results,
        "payload": payload,
        "note": ("Test warning sent to this device." if any(r["sent"] for r in results)
                 else "No push subscription registered yet — this is the message that "
                      "would be sent."),
    }
