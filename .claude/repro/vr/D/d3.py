import asyncio, copy, sys
from datetime import datetime, timedelta
sys.path.insert(0, "scripts")
import verify_stepfree as vs
from app import data
from app.config import HOME_DEFAULT, SGT
from app.services import lifts as lift_service, planner
async def main():
    appt = datetime.now(SGT).replace(second=0, microsecond=0)+timedelta(days=1, hours=10)
    blocked, access = await lift_service.blocked_exits_now()
    plan = planner.plan_trip(HOME_DEFAULT, appt, blocked_exits=blocked, access=access)
    wg = data.walk_graph(); index = {tuple(v): k for k, v in wg.nodes.items()}
    for leg in plan["legs"]:
        if leg["mode"]!="walk": continue
        c = leg["geometry"]["coordinates"]; pairs=list(zip(c,c[1:]))
        res = sum(1 for a,b in pairs if index.get(tuple(a)) is not None and index.get(tuple(b)) is not None)
        print(leg["leg_id"], f"resolved {res}/{len(pairs)}")
    for leg in plan["legs"]:
        print(leg["leg_id"], leg["mode"], {e:{k:(leg.get(e) or {}).get(k) for k in ("station_code","exit_code")} for e in ("from","to")})
    # find a steps edge
    u,v = next((u,v) for u,v,d in wg.all_ways.edges(data=True) if d.get("steps"))
    a,b = list(wg.nodes[u]), list(wg.nodes[v])
    fake = {"legs":[{"mode":"walk","leg_id":"x","distance_m":1,"geometry":{"coordinates":[a,b]}}]}
    print("exact steps edge:", vs.check_no_steps(fake)[0])
    nb = [b[0]+1e-7, b[1]]  # ~1.1 cm
    fake["legs"][0]["geometry"]["coordinates"]=[a,nb]
    print("nudged 1cm:", vs.check_no_steps(fake)[0])
    p2 = copy.deepcopy(plan)
    for leg in p2["legs"]:
        for e in ("from","to"):
            if leg.get(e): leg[e].pop("station_code",None); leg[e].pop("exit_code",None)
    print("stripped:", await vs.check_entrances(p2))
    # untagged entrance: find an exit ref at Outram with no wheelchair tag
    st = data.station_by_code()["EW16"]; area = wg.area_of(*st["coord"])
    ents = wg.entrances_for(area)
    untag = [r for r,e in ents.items() if not e.get("wheelchair")]
    print("Outram untagged refs:", untag[:5], "tags:", {r:e.get("wheelchair") for r,e in ents.items()})
    if untag:
        p3 = copy.deepcopy(plan)
        for leg in p3["legs"]:
            for e in ("from","to"):
                n=leg.get(e) or {}
                if n.get("station_code")=="EW16": n["exit_code"]=f"Exit {untag[0]}"
        print("untagged:", await vs.check_entrances(p3))
asyncio.run(main())
