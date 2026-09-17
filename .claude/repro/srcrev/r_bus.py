import sys, asyncio
sys.path.insert(0, ".")
from datetime import datetime
from app.config import SGT, HOME_DEFAULT
from app.services import alternatives as A
async def fake_pt(*a, **k):
    return {"plan": {"itineraries": [{"duration": 3000, "walkTime": 300, "legs": [{"mode": "BUS", "route": "2", "duration": 2400}]}]}}
A.onemap.pt_route = fake_pt
o = asyncio.run(A._bus_option(datetime(2026, 9, 19, 10, 30, tzinfo=SGT), HOME_DEFAULT["coord"]))
print({k: o["bus"][k] for k in ("service_no","eta_min","eta_is_scheduled","load","wheelchair_accessible","not_running")}); print(o["why"]); print("timing_basis:", o["timing_basis"])
