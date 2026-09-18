import json, sys, os
sys.path.insert(0, os.getcwd())
from app.sources import base
base.Source._record = lambda self, v, o: None   # never write fixtures into repo
from fastapi.testclient import TestClient
from app.main import app
OUT = sys.argv[1]
def show(label, r):
    print(f"\n=== {label} -> {r.status_code}")
    try:
        j = r.json(); print(json.dumps(j, indent=1, ensure_ascii=False)[:int(os.environ.get('CAP','2500'))]); return j
    except Exception: print(r.text[:500])
with TestClient(app) as c:
    spec = c.get("/openapi.json").json()
    json.dump(spec, open(OUT+"/openapi.json","w"), indent=1)
    for p, ops in spec["paths"].items():
        for m, op in ops.items():
            params = [(x["name"], x["in"]) for x in op.get("parameters", [])]
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            print(m.upper(), p, params, body, list(op["responses"].keys()))
    print("schemas:", {k: list(v.get("properties", {}).keys()) for k, v in spec["components"]["schemas"].items()})
    show("health", c.get("/api/health"))
    show("attribution", c.get("/api/attribution"))
    t = show("POST trips README body", c.post("/api/trips", json={"appointment_at":"2026-09-19T10:30:00+08:00"}))
    tid = t["trip_id"]
    json.dump(t, open(OUT+"/plan.json","w"), indent=1)
    show("POST trips contract body", c.post("/api/trips", json={ "origin": { "label": "Blk 208B New Upper Changi Road", "coord": [103.930570, 1.324782] },
  "destination_id": "SGH", "appointment_at": "2026-09-19T10:30:00+08:00",
  "preferences": { "walking_pace": "slow", "avoid_stairs": True, "prefer_sheltered": True } }))
    show("status off", c.get(f"/api/trips/{tid}/status"))
    show("alternatives off", c.get(f"/api/trips/{tid}/alternatives"))
    show("scenario get", c.get("/api/scenario"))
    show("scenario post README", c.post("/api/scenario", json={"lift_outage_outram":True,"ewl_disruption":True}))
    show("scenario post contract shape", c.post("/api/scenario", json={"enabled": True, "scenarios": {"lift_outage_outram": False}}))
    os.environ['CAP']='6000'
    s = show("status on", c.get(f"/api/trips/{tid}/status"))
    json.dump(s, open(OUT+"/status_on.json","w"), indent=1)
    a = show("alternatives on", c.get(f"/api/trips/{tid}/alternatives"))
    json.dump(a, open(OUT+"/alts_on.json","w"), indent=1)
    t2 = c.get(f"/api/trips/{tid}").json(); json.dump(t2, open(OUT+"/plan_rerouted.json","w"), indent=1)
    o = show("offline", c.get(f"/api/trips/{tid}/offline")); json.dump(o, open(OUT+"/offline.json","w"), indent=1)
    os.environ['CAP']='1500'
    show("push test no trip id", c.post("/api/push/test"))
    show("push key", c.get("/api/push/key"))
    show("places", c.get("/api/places/search?q=bedok"))
    show("destinations", c.get("/api/destinations"))
    show("trip 404", c.get("/api/trips/nope"))
    show("bad path 404", c.get("/api/nothere"))
    show("method 405", c.put("/api/trips/x"))
    show("validation", c.post("/api/trips", json={}))
    show("bad dest", c.post("/api/trips", json={"appointment_at":"2026-09-19T10:30:00+08:00","destination_id":"X"}))
    show("bad pace", c.post("/api/trips", json={"appointment_at":"2026-09-19T10:30:00+08:00","preferences":{"walking_pace":"sprint"}}))
    show("subscribe", c.post("/api/push/subscribe", json={"subscription":{"endpoint":"https://x/1","keys":{"p256dh":"a","auth":"b"}},"trip_ids":[tid]}))
    show("unsubscribe no endpoint", c.delete("/api/push/subscribe"))
    show("trip after unsubscribe", c.get(f"/api/trips/{tid}"))
    show("delete trip", c.delete(f"/api/trips/{tid}"))
