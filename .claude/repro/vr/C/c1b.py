from app import data
from app.services import walking
from app.config import SGH
wg=data.walk_graph()
for e in wg.entrances:
    if e['area']=='outram' and e['name'] in ('Outram Park',None,'Cantonment (CCL)'):
        for sh in (False,True):
            w=walking.route(SGH['coord'], e['coord'], 'outram', prefer_sheltered=sh)
            print(e['osm_id'], e['ref'], e['name'], e['wheelchair'], sh, w and w.distance_m)
