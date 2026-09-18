import json
from app import data
from app.services.walking import haversine
st=data.station_by_code()['EW16']; print('EW16', st['name'], st['coord'], st['station_id'])
print('LTA exits', [e['exit_code'] for e in data.exits_by_station()[st['station_id']]])
wg=data.walk_graph()
sx,sy=st['coord']
for e in wg.entrances:
    if e['area']=='outram':
        print(e['ref'], e['name'], e['wheelchair'], round(haversine(sy,sx,e['coord'][1],e['coord'][0])))
print('chosen map:')
for r,e in sorted(wg.entrances_for('outram').items()):
    print(r, e['osm_id'], e['name'], e['wheelchair'], round(haversine(sy,sx,e['coord'][1],e['coord'][0])))
