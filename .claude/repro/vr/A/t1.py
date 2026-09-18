import sys; sys.path.insert(0, sys.argv[1])
from common import *
from fastapi.testclient import TestClient
from app.main import app
from app import scenario
c = TestClient(app)
# A1
r = c.post("/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}); print("create", r.status_code)
t1 = r.json()["trip_id"]; print("legs0.from", r.json()["legs"][0].get("from"))
c.post("/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/ok1", "keys": sub_keys()}, "trip_ids": [t1]})
# CORS preflight
r = c.options("/api/push/subscribe", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "DELETE"})
print("A1 preflight", r.status_code, r.headers.get("access-control-allow-origin"), r.headers.get("access-control-allow-methods"))
r = c.delete("/api/push/subscribe"); print("A1 bare delete", r.json())
print("A1 get trip after", c.get(f"/api/trips/{t1}").status_code)
# A2
r = c.post("/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00", "origin": {"label": "Her Home 12", "coord": [103.93, 1.32]}}); t2 = r.json()["trip_id"]
c.post("/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/ok2", "keys": sub_keys()}, "trip_ids": [t2]})
r = c.post("/api/push/test"); j = r.json(); print("A2 test", r.status_code, j["payload"]["trip_id"]==t2, j["sent"], j["subscriptions"])
print("A2 leak", c.get(f"/api/trips/{j['payload']['trip_id']}").json()["legs"][0]["from"])
for _ in range(3): c.post("/api/push/test")
print("A2 hits ok2", len(HITS.get("/ok2", [])))
# A3
r = c.post("/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}); t3 = r.json()["trip_id"]
c.post("/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/fail", "keys": sub_keys()}, "trip_ids": [t3]})
r = c.post("/api/push/test", params={"trip_id": t3}); print("A3", repr(r.json()["results"]))
print("A3 auth header to attacker:", HITS["/fail"][0].get("Authorization", "")[:60])
# A5
scenario.set_state(ewl_disruption=True)
import asyncio
from app.services import notify
print("A5", asyncio.run(notify.check_trip({"trip_id": t3})))
scenario.set_state(enabled=False, ewl_disruption=False)
# A6
st = c.get(f"/api/trips/{t3}/status").json()
print("A6 sources", {a["source"] for a in st["lift_alerts"]}, "stale", st["stale"], "alert keys has stale?", [("stale" in a, "observed_at" in a) for a in st["lift_alerts"]][:2])
print("A6 crowd", st["crowd"][:1], "weather src/obs/stale", st["weather"] and (st["weather"].get("source"), st["weather"].get("observed_at"), st["weather"].get("stale")))
alt = c.get(f"/api/trips/{t3}/alternatives")
print("A6 alt", alt.status_code)
if alt.status_code == 200:
    for o in alt.json().get("options", []):
        if o.get("mode") == "bus": print(" bus", o["why"], {k: o["bus"].get(k) for k in ("eta_min","eta_is_scheduled","wheelchair_accessible","stale","observed_at")}, "keys", [k for k in o if "stale" in k or "observ" in k])
# A11
r = c.post("/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}); ta = r.json()["trip_id"]
r = c.post("/api/trips", json={"appointment_at": "2026-09-20T10:30:00+08:00"}); tb = r.json()["trip_id"]
k = sub_keys()
c.post("/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/dev", "keys": k}, "trip_ids": [ta]})
c.post("/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/dev", "keys": k}, "trip_ids": [tb]})
print("A11 subs", [s["trip_ids"] for s in store.subscriptions() if s["endpoint"].endswith("/dev")])
print("A11 del", c.delete("/api/push/subscribe", params={"endpoint": BASE+"/dev"}).json(), "A still", c.get(f"/api/trips/{ta}").status_code, "B", c.get(f"/api/trips/{tb}").status_code)
print("offline", c.get(f"/api/trips/{ta}/offline").status_code)
