import json
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app, raise_server_exceptions=False); c.__enter__()
H={"label":"Home","coord":[103.930570,1.324782]}
def post(body, raw=None):
    r = c.post("/api/trips", json=body) if raw is None else c.post("/api/trips", content=raw, headers={"content-type":"application/json"})
    t = r.text
    try:
        j=r.json(); 
        if "summary" in j: t = json.dumps({k:j["summary"][k] for k in ("leave_by","arrival_window","buffer_min")})+" id="+j["trip_id"]
    except Exception: pass
    return r.status_code, t[:300]
A="2026-09-21T10:30:00"
cases = {
 "ok": {"appointment_at":A},
 "coord len1": {"origin":{"coord":[103.93]},"appointment_at":A},
 "coord len3": {"origin":{"coord":[103.930570,1.324782,5]},"appointment_at":A},
 "coord empty": {"origin":{"coord":[]},"appointment_at":A},
 "latlon swapped": {"origin":{"coord":[1.324782,103.930570]},"appointment_at":A},
 "buffer negative": {"appointment_at":A,"preferences":{"buffer_min":-120}},
 "buffer huge": {"appointment_at":A,"preferences":{"buffer_min":10**12}},
 "pace bogus": {"appointment_at":A,"preferences":{"walking_pace":"sprint"}},
 "avoid_stairs false": {"appointment_at":A,"preferences":{"avoid_stairs":False}},
 "past": {"appointment_at":"2001-01-01T10:30:00"},
 "year1": {"appointment_at":"0001-01-01T00:10:00"},
 "year9999": {"appointment_at":"9999-12-31T23:59:00"},
 "Z offset": {"appointment_at":"2026-09-21T02:30:00Z"},
 "unix int": {"appointment_at":1790000000},
 "date only": {"appointment_at":"2026-09-21"},
 "dest other": {"appointment_at":A,"destination_id":"TTSH"},
 "origin null": {"origin":None,"appointment_at":A},
 "bedok bbox edge far": {"origin":{"coord":[103.943,1.335]},"appointment_at":A},
 "snap just in": {"origin":{"coord":[103.9315,1.3255]},"appointment_at":A},
}
for k,b in cases.items(): print(k, post(b))
print("NaN", post(None, raw='{"origin":{"coord":[NaN,1.32]},"appointment_at":"2026-09-21T10:30:00"}'))
print("Infinity", post(None, raw='{"origin":{"coord":[Infinity,1.32]},"appointment_at":"2026-09-21T10:30:00"}'))
print("bad json", post(None, raw='{'))
print("404 route", c.get("/api/nope").status_code, c.get("/api/nope").text)
print("405", c.put("/api/trips").status_code, c.put("/api/trips").text)
print("trip 404", c.get("/api/trips/t_zzzz").text)
print("places short", c.get("/api/places/search?q=ab").text)
print("places missing", c.get("/api/places/search").status_code, c.get("/api/places/search").text)
r=c.get("/api/places/search?q=bedok"); print("places", r.status_code, r.text[:200])
print("cors", c.options("/api/trips", headers={"Origin":"https://evil.example","Access-Control-Request-Method":"POST"}).headers)
import sys; print("done")
