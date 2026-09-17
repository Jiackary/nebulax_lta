import json
from datetime import datetime
from app import data
from app.config import SGT, SGH
from app.services import planner, walking
wg = data.walk_graph()
print("outram entrances_for:", {k:(v['osm_id'],v['name'],v['wheelchair']) for k,v in wg.entrances_for('outram').items()})
p = planner.plan_trip({"label":"Home","coord":[103.930570,1.324782]}, datetime(2026,9,19,10,30,tzinfo=SGT))
print(json.dumps(p["summary"],indent=1, ensure_ascii=False))
for l in p["legs"]: print(l["leg_id"], l["from"], l["to"], l.get("instruction"), l["geometry"]["coordinates"][:1], l["geometry"]["coordinates"][-1:])
# block every Outram Park exit that is genuinely Outram Park
for blk in [{"4"},{"4","6"},{"4","6","8","1","2","7","3","5"}]:
    try:
        p = planner.plan_trip({"label":"Home","coord":[103.930570,1.324782]}, datetime(2026,9,19,10,30,tzinfo=SGT), blocked_exits={"EW16":blk})
        l3=p["legs"][2]; print("blocked",blk,"->",l3["from"], l3["distance_m"], l3["instruction"])
    except Exception as e: print("blocked",blk,"->",repr(e))
