import json, asyncio, collections, secrets
from fastapi.testclient import TestClient
from app.main import app
from app.sources import onemap
from app import store
with TestClient(app, raise_server_exceptions=False) as c:
    o=c.get("/openapi.json").json()
    for path in ("/api/trips","/api/trips/{trip_id}"):
        for m,v in o["paths"][path].items():
            print(m,path,json.dumps(v["responses"])[:200])
    print(json.dumps(o["components"]["schemas"]["Preferences"]))
    onemap.ONEMAP_TOKEN="x"; onemap.ONEMAP="http://127.0.0.1:9"
    r=c.get("/api/places/search?q=bedok"); print("places conn error", r.status_code, r.text[:120])
    j=c.post("/api/trips", json={"appointment_at":"2026-09-21T10:30:00"}).json()
    print("TripPlan keys", sorted(j.keys()), "observed_at" in j)
# id space
ids=[store.new_trip_id() for _ in range(200000)]
lens=collections.Counter(len(i) for i in ids); print("id lengths", lens)
print("alphabet", len(set("".join(i[2:] for i in ids))))
