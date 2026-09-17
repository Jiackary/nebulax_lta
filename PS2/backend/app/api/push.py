"""Web Push subscribe/unsubscribe/test (API contract §7, D4)."""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from .. import store
from ..config import VAPID_CLAIM_EMAIL, VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
from ..services import notify

router = APIRouter()
log = logging.getLogger("ps2.push")

# The server POSTs to whatever URL was subscribed, so an unvalidated endpoint is
# an SSRF primitive — and pywebpush's exception text carries the upstream
# response body, which handed the caller the result (F03). Only the real push
# services are accepted, and the caller never sees the upstream's answer.
PUSH_HOSTS = {"fcm.googleapis.com", "updates.push.services.mozilla.com"}
PUSH_HOST_SUFFIXES = (".push.apple.com", ".notify.windows.com")

# pywebpush passes timeout=None, so requests waits forever. With an
# attacker-chosen endpoint that is a way to hang a worker (F14).
PUSH_TIMEOUT_S = 10


def is_allowed_endpoint(endpoint: str) -> bool:
    try:
        parsed = urlparse(endpoint)
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return host in PUSH_HOSTS or host.endswith(PUSH_HOST_SUFFIXES)


class Subscription(BaseModel):
    endpoint: str
    keys: dict

    @field_validator("endpoint")
    @classmethod
    def endpoint_is_a_push_service(cls, value: str) -> str:
        if not is_allowed_endpoint(value):
            raise ValueError("endpoint must be an https URL on a known push service")
        return value


class SubscribeRequest(BaseModel):
    subscription: Subscription
    trip_ids: list[str] = []


def send_push(subscription: dict, payload: dict) -> tuple[bool, str | None]:
    """Deliver one notification. Returns (sent, error).

    The error is a code, not the upstream's words: pywebpush puts the response
    body into its exception text, and this value is returned to the caller.
    """
    if not VAPID_PRIVATE_KEY:
        return False, "PUSH_NOT_CONFIGURED"
    if not is_allowed_endpoint(subscription.get("endpoint", "")):
        return False, "ENDPOINT_NOT_ALLOWED"
    try:
        from pywebpush import webpush
        webpush(subscription_info=subscription, data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
                timeout=PUSH_TIMEOUT_S)
        return True, None
    except Exception as exc:
        # Full detail to the server log, a bare code to the caller.
        log.warning("push to %s failed: %s", subscription.get("endpoint", "")[:60], exc)
        return False, "PUSH_FAILED"


async def send_push_async(subscription: dict, payload: dict) -> tuple[bool, str | None]:
    """`webpush` is synchronous requests, so it must not run on the event loop."""
    return await asyncio.to_thread(send_push, subscription, payload)


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
def unsubscribe(endpoint: str):
    """Unsubscribing also deletes her stored trips (privacy commitment 1).

    `endpoint` is required. It used to be optional, and omitting it deleted
    every subscription on the server and every trip linked to them, unauthenticated
    (F04).
    """
    result = store.delete_subscription(endpoint)
    return {"unsubscribed": True, **result,
            "note": "Your saved trips have been deleted from the server."}


@router.post("/push/test")
async def push_test(trip_id: str):
    """Fire the real check-and-send path now, so judges need not wait for 20:00.

    If no browser has subscribed we still return the payload that *would* have
    been sent, rather than a bare success that shows nothing.

    `trip_id` is required. Falling back to `all_trips()[0]` meant an anonymous
    caller acted on whichever trip happened to be first — pushing to its owner's
    phone and returning its id, which is enough to read her home coordinate (F05).
    """
    trip = store.get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail={"error": {
            "code": "TRIP_NOT_FOUND", "message": "Plan a trip first.", "retryable": False}})

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
        sent, error = await send_push_async(
            {"endpoint": sub["endpoint"], "keys": sub["keys"]}, payload)
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
