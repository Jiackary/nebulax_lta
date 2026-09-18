import asyncio, json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app import scenario, store
from app.sources import datamall
from app.sources.base import Fetched
from app.config import SGT
from app.services import notify, lifts, disruption

with TestClient(app) as c:
    appt = (datetime.now(SGT)+timedelta(hours=14)).replace(minute=0, second=0, microsecond=0)
    r = c.post("/api/trips", json={"appointment_at": appt.isoformat()})
    print("create", r.status_code); tid = r.json()["trip_id"]
    legs = r.json()["legs"]; print("exits", legs[0]["to"].get("exit_code"), legs[2]["from"].get("exit_code"), r.json()["summary"]["leave_by"])

    # --- 1: global scenario leaks into push job
    print("POST scenario (no auth):", c.post("/api/scenario", json={"lift_outage_outram": True, "ewl_disruption": True}).status_code)
    trip = store.get_trip(tid)
    p = asyncio.run(notify.check_trip(trip))
    print("push payload under scenario:", json.dumps(p))

    # --- 2: reroute persists after scenario off
    c.post("/api/scenario", json={"enabled": False, "lift_outage_outram": False, "ewl_disruption": False})
    c.post("/api/scenario", json={"lift_outage_outram": True})
    s1 = c.get(f"/api/trips/{tid}/status").json()
    print("status1 rerouted", s1["rerouted"], s1["overall"])
    s2 = c.get(f"/api/trips/{tid}/status").json()
    print("status2 rerouted", s2["rerouted"], s2["overall"])
    c.post("/api/scenario", json={"enabled": False, "lift_outage_outram": False})
    s3 = c.get(f"/api/trips/{tid}/status").json()
    t = c.get(f"/api/trips/{tid}").json()
    print("after scenario off: status rerouted", s3["rerouted"], s3["overall"]["headline"], "| stored plan exit", t["legs"][2]["from"].get("exit_code"), "rerouted flag", t.get("rerouted"), t["summary"]["leave_by"])

    # alternatives under disruption
    c.post("/api/scenario", json={"ewl_disruption": True})
    a = c.get(f"/api/trips/{tid}/alternatives").json()
    for o in a["options"]:
        print("opt", o["option_id"], o.get("label"), o.get("leave_by"), o.get("arrival_at"), o.get("source"), o.get("step_free"), o.get("why"))
    print("appt", t["appointment_at"], "orig arrival", a["original"]["arrival_at"])
    c.post("/api/scenario", json={"enabled": False, "ewl_disruption": False})
