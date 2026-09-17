import asyncio, sys, copy
sys.path.insert(0, ".")
sys.path.insert(0, "scripts")
import verify_stepfree as V
from app import data
from app.config import HOME_DEFAULT
from app.services import planner, lifts as L
from datetime import datetime, timedelta
from app.config import SGT

wg = data.walk_graph()
appt = datetime.now(SGT).replace(second=0, microsecond=0) + timedelta(days=1, hours=10)
blocked, access = asyncio.run(L.blocked_exits_now())
plan = planner.plan_trip(HOME_DEFAULT, appt, blocked_exits=blocked, access=access)
index = {tuple(v): k for k, v in wg.nodes.items()}
for leg in plan["legs"]:
    if leg["mode"] != "walk": continue
    c = leg["geometry"]["coordinates"]
    hit = sum(1 for a,b in zip(c,c[1:]) if index.get(tuple(a)) is not None and index.get(tuple(b)) is not None and wg.all_ways.get_edge_data(index[tuple(a)], index[tuple(b)]))
    print(leg["leg_id"], "pairs", len(c)-1, "resolved edges", hit)
print("dup coords in graph:", len(wg.nodes) - len(index))
# 1) inject a real staircase edge into leg geometry -> should FAIL
u, v, d = next((u, v, d) for u, v, d in wg.all_ways.edges(data=True) if d["steps"])
p = copy.deepcopy(plan)
leg = next(l for l in p["legs"] if l["mode"] == "walk")
leg["geometry"]["coordinates"] = [wg.nodes[u], wg.nodes[v]]
print("staircase exact coords:", V.check_no_steps(p)[0])
# 2) same staircase, coords as floats nudged by 1e-7 deg (1 cm) -> vacuous
leg["geometry"]["coordinates"] = [[x + 1e-7 for x in wg.nodes[u]], [x + 1e-7 for x in wg.nodes[v]]]
print("staircase nudged 1cm:", V.check_no_steps(p)[0])
# 3) entrance check: untagged entrance, no lift exists at all
orig = wg.entrances
wg.entrances = [dict(e, wheelchair=None) for e in orig]
print("entrances all untagged, no outage:", asyncio.run(V.check_entrances(plan))[0])
# 4) legs with no station_code keys at all -> vacuous
p2 = copy.deepcopy(plan)
for l in p2["legs"]:
    for end in ("from","to"): (l.get(end) or {}).pop("station_code", None)
print("no station_code on legs:", asyncio.run(V.check_entrances(p2)))
print([ (l["leg_id"], l["mode"], {k: (l.get(k) or {}).get("exit_code") for k in ("from","to")}) for l in plan["legs"]])
