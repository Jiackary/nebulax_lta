import json
from datetime import datetime
from app import data
from app.config import SGT, HOME_DEFAULT
from app.services import planner, timing
h=data.headways()
print(list(h.keys())[:5])
t=h['EWL']['EW5']
for dt,v in t.items():
    for d,hrs in v.items():
        print(dt,d,sorted((int(k),x) for k,x in hrs.items()))
o={"label":"Home","coord":HOME_DEFAULT["coord"]}
for (y,m,d,H,M) in [(2026,9,21,8,40),(2026,9,21,1,30),(2026,9,21,5,30),(2026,12,25,8,40),(2026,9,21,0,30)]:
    a=datetime(y,m,d,H,M,tzinfo=SGT)
    p=planner.plan_trip(o,a)
    s=p['summary']
    print(a, a.strftime('%a'), 'hw',p['legs'][1]['headway_min'], s['leave_by_label'], s['range_min'], s['timing_basis'])
    lb=datetime.fromisoformat(s['leave_by'])
    print('  headway at leave hour', timing.headway_min('EWL','EW5','1',lb), 'boarding ~', lb)
