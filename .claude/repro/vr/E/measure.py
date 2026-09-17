import json
from app.sources import base
base.Source._record = lambda self, v, o: None
from fastapi.testclient import TestClient
from app.main import app
from app import scenario
from app.config import ONEMAP_TOKEN
print("ONEMAP_TOKEN set:", bool(ONEMAP_TOKEN))
from app.services import planner
from app.config import HOME_DEFAULT
from datetime import datetime
from app.config import SGT

def summ(p):
    s = p["summary"]
    return dict(walk=s.get("walk_distance_m"), shel=s["sheltered_pct"], rng=s["range_min"], leave=s["leave_label"] if "leave_label" in s else s["leave_by_label"], arr=s["arrival_label"], exits=(p["legs"][1]["from"].get("exit_code"), p["legs"][1]["to"].get("exit_code")), legs_m=(p["legs"][0]["distance_m"], p["legs"][2]["distance_m"]), keys=sorted(p.keys()), access=p["legs"][1]["access"])

appt = datetime(2026,9,19,10,30,tzinfo=SGT)
with TestClient(app) as c:
    scenario.set_state(enabled=False, lift_outage_outram=False, ewl_disruption=False)
    scenario._state.update(enabled=False, lift_outage_outram=False, ewl_disruption=False)
    for ps in (False, True):
        p = planner.plan_trip(HOME_DEFAULT, appt, prefer_sheltered=ps)
        print("planner ps=",ps, summ(p))
    # API default
    for body_prefs in (None, {"prefer_sheltered": False}, {"prefer_sheltered": True}):
        body = {"appointment_at": "2026-09-19T10:30:00+08:00"}
        if body_prefs is not None: body["preferences"] = body_prefs
        r = c.post("/api/trips", json=body).json()
        print("API prefs", body_prefs, summ(r), "observed_at" in r)
        tid = r["trip_id"]
        # reroute
        scenario._state.update(enabled=True, lift_outage_outram=True)
        st = c.get(f"/api/trips/{tid}/status").json()
        p2 = c.get(f"/api/trips/{tid}").json()
        print("  rerouted", st.get("rerouted"), summ(p2), "added m", p2["summary"]["walk_distance_m"]-r["summary"]["walk_distance_m"])
        print("  weather keys", sorted(st["weather"].keys()))
        scenario._state.update(enabled=False, lift_outage_outram=False)
        alt = c.get(f"/api/trips/{tid}/alternatives").json()
        print("  alt no disruption:", alt["disruption"], [(o["option_id"], o.get("delta_min"), o.get("duration_min")) for o in alt["options"]])
    # scenario bodies
    print(c.post("/api/scenario", json={"scenarios":{"lift_outage_outram":True,"ewl_disruption":True}}).status_code, c.get("/api/scenario").json())
    print(c.post("/api/scenario", json={"enabled":True, "scenarios":{"lift_outage_outram":True}}).json())
    print(c.post("/api/scenario", json={"lift_outage_outram":True}).json())
    print("disable:", c.post("/api/scenario", json={"enabled":False}).json())
    print(c.post("/api/scenario", json={"enabled":False,"lift_outage_outram":False,"ewl_disruption":False}).json())
    # disruption on: alternatives
    scenario._state.update(enabled=True, ewl_disruption=True)
    alt = c.get(f"/api/trips/{tid}/alternatives").json()
    print("alt disruption:", json.dumps(alt["options"], indent=0)[:3000])
    scenario._state.update(enabled=False, ewl_disruption=False)
    oa = c.get("/openapi.json").json()
    for path, ops in oa["paths"].items():
        for m, op in ops.items():
            r200 = op["responses"].get("200",{}).get("content",{}).get("application/json",{}).get("schema")
            print(m, path, "200schema:", r200, "422:", "422" in op["responses"])
    print(oa["components"]["schemas"].get("HTTPValidationError"))
    print(c.post("/api/trips", json={}).status_code, c.post("/api/trips", json={}).json())
    print(c.get("/api/push/key").status_code, c.get("/api/push/key").json())
