import sys; sys.path.insert(0, sys.argv[1])
from common import *
import asyncio, secrets
from datetime import datetime, timedelta
from app import store, jobs
from app.config import SGT
from app.services import notify
from app.api import push
# A3 header
push.send_push({"endpoint": BASE+"/fail", "keys": sub_keys()}, {"a":1})
h = HITS["/fail"][0]; print("A3 headers", {k: v[:50] for k, v in h.items() if k.lower() in ("authorization","crypto-key")})
# A7 duplicates
HITS.clear()
appt = datetime.now(SGT) + timedelta(hours=10)
tid = store.save_trip(appt, {"label":"x","coord":[0,0]}, {}, {"legs": []})
store.save_subscription(BASE+"/ok", sub_keys(), [tid])
store.save_subscription(BASE+"/fail", sub_keys(), [tid])
async def fake(trip): return {"title":"T","body":"B","trip_id":trip["trip_id"],"digest":"d1"}
notify.check_trip = fake
for _ in range(3): print("A7 run", asyncio.run(jobs.run_check("20:00", 36)))
print("A7 ok hits", len(HITS.get("/ok", [])), "fail hits", len(HITS.get("/fail", [])))
store.delete_trip(tid); print("A7 subs after trip delete", len(store.subscriptions()))
# A8 windows via trips_between
def win(now, h): return now, now + timedelta(hours=h)
mon20 = datetime(2026, 9, 21, 20, 0, tzinfo=SGT)
for label, ap in [("wed0730", datetime(2026,9,23,7,30,tzinfo=SGT)), ("tue1030", datetime(2026,9,22,10,30,tzinfo=SGT))]:
    s, e = win(mon20, 36); print("A8 Mon20:00 36h includes", label, s <= ap <= e)
tue07 = datetime(2026,9,22,7,0,tzinfo=SGT); s,e = win(tue07,24); print("A8 Tue07:00 24h includes Wed06:30", s <= datetime(2026,9,23,6,30,tzinfo=SGT) <= e)
# A9 sweep
for t in store.all_trips(): store.delete_trip(t["trip_id"])
tid = store.save_trip(datetime(2026,9,21,3,30,tzinfo=SGT), {"label":"x","coord":[0,0]}, {}, {"legs": []})
print("A9 sweep D+1 03:00", store.sweep(now=datetime(2026,9,22,3,0,tzinfo=SGT)), "D+2 03:00", store.sweep(now=datetime(2026,9,23,3,0,tzinfo=SGT)))
# A10
N = 1_000_000; short = 0; seen=set(); chars=set()
for _ in range(N):
    x = store.new_trip_id()[2:]
    if len(x) < 4: short += 1
    chars.update(x)
print("A10 short frac %", 100*short/N, "alphabet", len(chars), "62^4", 62**4)
