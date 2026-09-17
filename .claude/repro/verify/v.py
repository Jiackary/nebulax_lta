import asyncio, os
from fastapi.testclient import TestClient
from app.main import app
from app import scenario
from app.sources import datamall
from app.services import lifts, notify, planner
from app import data

with TestClient(app) as c:
    # V1: DELETE /push/subscribe with no endpoint wipes everyone
    r = c.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}); tid = r.json()["trip_id"]
    c.post("/api/push/subscribe", json={"subscription": {"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh":"a","auth":"b"}}, "trip_ids": [tid]})
    print("V1 delete-all:", c.delete("/api/push/subscribe").json(), "trip after:", c.get(f"/api/trips/{tid}").status_code)

    # V2: multi-exit lift "Exits 5/6" at EW16 vs plan using Exit 6
    r = c.post("/api/trips", json={"appointment_at": "2026-09-21T10:30:00"}); plan = r.json(); tid = plan["trip_id"]
    print("V2 plan exits:", [(l.get("from",{}).get("exit_code"), l.get("to",{}).get("exit_code")) for l in plan["legs"]])
    rows = [{"Line":"EWL","StationCode":"EW16","StationName":"Outram Park","LiftID":"X","LiftDesc":"Exits 5/6 Street level - Concourse"}]
    print("V2 match:", {k: lifts.match_row(rows[0])[k] for k in ("resolution","exit_code","parsed_exits")})
    orig = datamall.lifts.get
    async def fake():
        f = await orig(); f.data = rows; return f
    datamall.lifts.get = fake
    s = c.get(f"/api/trips/{tid}/status").json()
    print("V2 overall:", s["overall"]["detail"], "| rerouted:", s["rerouted"])
    # V3: unmatched lift at her station
    rows[:] = [{"Line":"EWL","StationCode":"EW16","StationName":"Outram Park","LiftID":"X","LiftDesc":"Exit6 Street level - Concourse"}]
    s = c.get(f"/api/trips/{tid}/status").json()
    print("V3 overall:", s["overall"]["detail"])
    datamall.lifts.get = orig

    # V4: scenario on -> scheduled push payload unlabelled
    scenario.set_state(ewl_disruption=True)
    p = asyncio.run(notify.check_trip({"trip_id": tid}))
    print("V4 push payload:", p)
    scenario.set_state(enabled=False, ewl_disruption=False, lift_outage_outram=False)

    # V5: fixtures labelled live
    s = c.get(f"/api/trips/{tid}/status").json()
    print("V5 lift sources:", {a["source"] for a in s["lift_alerts"]}, "stale:", s["stale"])

    # V6: outram entrances
    ents = data.entrances_for("outram") if hasattr(data, "entrances_for") else None
    print("V6 entrances:", type(ents), (list(ents.items())[:12] if isinstance(ents, dict) else ents[:12] if ents else None))
