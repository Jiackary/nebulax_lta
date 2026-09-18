import sys, json
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app
from app import scenario
with TestClient(app) as c:
    tid = c.post("/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}).json()
    tid = tid.get("trip_id") or tid
    s = c.get(f"/api/trips/{tid}/status").json()
    print("status.stale", s["stale"], "observed_at", s["observed_at"])
    print("lift_alerts", [(a.get("source"), a.get("observed_at")) for a in s["lift_alerts"]])
    print("disruption", s["disruption"] and {k: s["disruption"].get(k) for k in ("source","observed_at")})
    c.post("/api/scenario", json={"enabled": True, "ewl_disruption": True})
    alt = c.get(f"/api/trips/{tid}/alternatives").json()
    txt = json.dumps(alt)
    for o in alt.get("options", []):
        if o.get("mode") == "bus": print("bus", {k: o["bus"].get(k) for k in ("eta_min","load_label","wheelchair_accessible","not_running")}, "| stale/observed keys present:", any(k in o["bus"] for k in ("stale","observed_at")), "|", o["why"])
    print(sorted(alt.keys()))
