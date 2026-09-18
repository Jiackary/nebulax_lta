import json
from datetime import datetime
from app.config import SGT, HOME_DEFAULT, SGH
from app.services import planner, walking
from app import data
appt=datetime(2026,9,21,10,30,tzinfo=SGT)
o={"label":"Home","coord":HOME_DEFAULT["coord"]}
for blk in [None, {"EW16":{"6"}}, {"EW16":{"4","6"}}, {"EW16":{"1","2","3","4","6","7","8"}}]:
    for sh in (False, True):
        p=planner.plan_trip(o, appt, blocked_exits=blk, prefer_sheltered=sh)
        l3=p['legs'][2]
        print(blk, sh, l3['from'].get('exit_code'), p['summary']['step_free'], p['legs'][1]['step_free'], p['legs'][1]['access'], l3['instruction'][:60], l3['distance_m'])
# C3 geometry direction
p=planner.plan_trip(o, appt)
l3=p['legs'][2]; g=l3['geometry']['coordinates']
wg=data.walk_graph()
h=walking.haversine
print('l3 from', l3['from']['coord'], 'to', l3['to']['coord'])
print('geom first', g[0], 'last', g[-1])
print('first->SGH', h(g[0][1],g[0][0],SGH['coord'][1],SGH['coord'][0]), 'first->exit', h(g[0][1],g[0][0],l3['from']['coord'][1],l3['from']['coord'][0]))
l1=p['legs'][0]['geometry']['coordinates']
print('l1 first->home', h(l1[0][1],l1[0][0],o['coord'][1],o['coord'][0]))
