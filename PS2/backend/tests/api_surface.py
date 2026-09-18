"""The set of JSON keys every endpoint serves, as a comparable map.

Adding `response_model=` to a FastAPI route makes the model authoritative: any
field the model does not declare is **silently dropped** from the response. A
model written from the contract prose rather than from the payload would
therefore delete fields from a working API and nothing would fail. So the key
map is captured from the code as it was before the models existed, committed as
`data/api_surface.json`, and asserted against afterwards.

Values are deliberately not compared — timestamps, trip ids and live readings
all vary. Only the shape is the contract.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

PUSH_ENDPOINT = "https://fcm.googleapis.com/fcm/send/surface-probe"
KEYS = {"p256dh": "BPb0v-probe", "auth": "k9s-probe"}
APPOINTMENT = "2026-09-21T10:30:00"


def key_map(value, prefix: str = "") -> set[str]:
    """Every path through the payload. `a.b` for nesting, `a[]` for a list."""
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            path = f"{prefix}.{k}" if prefix else k
            out.add(path)
            out |= key_map(v, path)
    elif isinstance(value, list):
        # Every element, not just the first: options[] and legs[] are
        # heterogeneous — a rail leg carries `access` and `line`, a walk leg
        # does not, and only one of them would show up otherwise.
        for item in value:
            out |= key_map(item, f"{prefix}[]")
    return out


def capture(app) -> dict[str, list[str]]:
    """Call every endpoint with the demo armed, and return each one's key map."""
    surface: dict[str, list[str]] = {}

    def record(name: str, response) -> None:
        surface[name] = sorted(key_map(response.json()))

    with TestClient(app) as c:
        # Both states. Armed is the demo shape; quiet is what she sees on an
        # ordinary day, and it is genuinely different — `disruption` is null and
        # `alternatives` refuses. Capturing only the armed one is how a model
        # ends up rejecting the common case.
        record("POST /api/scenario",
               c.post("/api/scenario", json={"lift_outage_outram": True,
                                             "ewl_disruption": True}))
        record("GET /api/scenario", c.get("/api/scenario"))

        created = c.post("/api/trips", json={"appointment_at": APPOINTMENT})
        record("POST /api/trips", created)
        trip_id = created.json()["trip_id"]

        record("GET /api/trips/{trip_id}", c.get(f"/api/trips/{trip_id}"))
        record("GET /api/trips/{trip_id}/status", c.get(f"/api/trips/{trip_id}/status"))
        record("GET /api/trips/{trip_id}/alternatives",
               c.get(f"/api/trips/{trip_id}/alternatives"))
        record("GET /api/trips/{trip_id}/offline", c.get(f"/api/trips/{trip_id}/offline"))

        record("GET /api/health", c.get("/api/health"))
        record("GET /api/attribution", c.get("/api/attribution"))
        record("GET /api/destinations", c.get("/api/destinations"))
        record("GET /api/push/key", c.get("/api/push/key"))

        record("POST /api/push/subscribe",
               c.post("/api/push/subscribe",
                      json={"subscription": {"endpoint": PUSH_ENDPOINT, "keys": KEYS},
                            "trip_ids": [trip_id]}))
        record("POST /api/push/test",
               c.post("/api/push/test", params={"trip_id": trip_id}))
        record("DELETE /api/push/subscribe",
               c.request("DELETE", "/api/push/subscribe",
                         params={"endpoint": PUSH_ENDPOINT}))

        # The error envelope is part of the surface too (§1).
        record("GET /api/trips/{trip_id} (404)", c.get("/api/trips/t_nope"))
        record("GET /api/places/search", c.get("/api/places/search", params={"q": "bedok"}))

        c.post("/api/scenario", json={"enabled": False, "lift_outage_outram": False,
                                      "ewl_disruption": False})
        quiet = c.post("/api/trips", json={"appointment_at": APPOINTMENT}).json()["trip_id"]
        record("GET /api/trips/{trip_id}/status (quiet)", c.get(f"/api/trips/{quiet}/status"))
        record("GET /api/trips/{trip_id}/alternatives (quiet)",
               c.get(f"/api/trips/{quiet}/alternatives"))
        record("GET /api/trips/{trip_id}/offline (quiet)", c.get(f"/api/trips/{quiet}/offline"))
        record("DELETE /api/trips/{trip_id}", c.delete(f"/api/trips/{quiet}"))

    return surface
