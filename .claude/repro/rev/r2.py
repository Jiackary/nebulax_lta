import json
from datetime import datetime
from app.config import SGT
from app.services import planner
H={"label":"Home","coord":[103.930570,1.324782]}
for blk in [{"4","6","7","8","1"},{"4","6","7","8","1","2"},{"4","6","7","8","1","2","3"}]:
    try:
        p = planner.plan_trip(H, datetime(2026,9,19,10,30,tzinfo=SGT), blocked_exits={"EW16":blk})
        l3=p["legs"][2]; print("blocked",sorted(blk),"->",l3["from"]["exit_code"], l3["from"]["coord"], l3["distance_m"])
    except Exception as e: print("blocked",blk,"->",repr(e))
for ts in ["2026-09-21T05:30","2026-09-21T06:00","2026-09-21T00:30","2026-09-20T06:10","2026-09-21T09:05","2026-09-21T08:40","2026-12-25T06:15","2026-09-21T01:30"]:
    dt=datetime.fromisoformat(ts).replace(tzinfo=SGT)
    p=planner.plan_trip(H, dt)
    s=p["summary"]; print(ts, dt.strftime("%a"), "leave", s["leave_by"], "range", s["range_min"], "headway", p["legs"][1]["headway_min"])
