import json, sys, os
sys.path.insert(0, os.getcwd())
from datetime import datetime
from app.sources import base
base.Source._record = lambda self, v, o: None
from app.services import planner
from app.config import HOME_DEFAULT, SGT
from app import data, scenario
def p(label, when, **kw):
    pl = planner.plan_trip(dict(HOME_DEFAULT), when, **kw)
    s = pl["summary"]
    print(label, when.strftime("%a %H:%M"), kw.get("prefer_sheltered"), s["leave_by_label"], s["arrival_label"], s["range_min"], s["walk_distance_m"], s["sheltered_pct"], [l.get("distance_m") for l in pl["legs"]], pl["legs"][1]["to"]["exit_code"], pl["legs"][1]["headway_min"])
    return pl
for d in (datetime(2026,9,19,10,30,tzinfo=SGT), datetime(2026,9,21,10,30,tzinfo=SGT), datetime(2026,9,21,8,30,tzinfo=SGT), datetime(2026,9,17,10,30,tzinfo=SGT)):
    for ps in (False, True):
        p("plain", d, prefer_sheltered=ps)
        p("block6", d, prefer_sheltered=ps, blocked_exits={"EW16": {"6"}})
ex = data.exits(); print("exits features", len(ex["features"]), {k: sum(1 for f in ex["features"] if f["properties"].get("source")==k) for k in ("gtfs","shapefile","GTFS","TrainStationExit")})
rt = data.ridetimes(); print("pair", rt["_pairs"]["EWL"].get("EW5>EW16"))
print("stations", len(data.stations()) if not isinstance(data.stations(), dict) else list(data.stations().keys())[:5])
print(scenario.set_state(lift_outage_outram=True))
print("disable via enabled false:", scenario.set_state(enabled=False))
