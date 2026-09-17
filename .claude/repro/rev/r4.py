import json, asyncio
from datetime import datetime
import networkx as nx
from app import data
from app.config import SGT
from app.services import planner, walking
wg=data.walk_graph()
H={"label":"Home","coord":[103.930570,1.324782]}
p = planner.plan_trip(H, datetime(2026,9,19,10,30,tzinfo=SGT), blocked_exits={"EW16":{"4","6"}})
print("exit7 fallback step_free:", p["summary"]["step_free"], p["legs"][2]["step_free"], p["legs"][1]["access"])
# snap of default home & walk
w=walking.route(H["coord"], [103.929668, 1.324168], "bedok")
print("home snap_m", w.snap_m)
# step-free islands within main component
cand=wg.candidates("bedok", True)
sub=wg.step_free.subgraph(cand)
comps=sorted(nx.connected_components(sub), key=len, reverse=True)
print("bedok step-free comps within main:", len(comps), [len(c) for c in comps[:5]])
# grid sample of origins
import itertools
res={}
ex=[]
for i,j in itertools.product(range(25),range(25)):
    lat=1.318+ (1.335-1.318)*(i+0.5)/25; lon=103.923+(103.943-103.923)*(j+0.5)/25
    a,da=walking._snap(wg,[lon,lat],"bedok",True)
    try:
        planner.plan_trip({"coord":[lon,lat]}, datetime(2026,9,19,10,30,tzinfo=SGT)); k="ok"
    except RuntimeError as e: k=str(e)
    if k.startswith("no step-free") and da<=100: ex.append(([lon,lat],round(da),next(n for n,c in enumerate(comps) if a in c)))
    res[k]=res.get(k,0)+1
print(res); print("no-route but snap<=100:", ex[:5], len(ex))
