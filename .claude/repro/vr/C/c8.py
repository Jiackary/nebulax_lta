import networkx as nx
from app import data
from app.services import walking, planner
from app.config import SGT
from datetime import datetime
wg=data.walk_graph()
for area in ['bedok','outram']:
    want=wg.main_by_area[area]
    mainnodes=[n for n,c in wg.component.items() if c==want]
    print(area,'main comp nodes (all_ways)', len(mainnodes))
    sub=wg.step_free.subgraph([n for n in mainnodes if n in wg.step_free])
    comps=sorted((len(c) for c in nx.connected_components(sub)), reverse=True)
    print(' step_free nodes in it', sub.number_of_nodes(), 'pieces', len(comps), comps[:6])
    cand=wg.candidates(area, True); print(' candidates', len(cand))
# step-free main piece for bedok
want=wg.main_by_area['bedok']
sub=wg.step_free.subgraph([n for n in wg.candidates('bedok',True)])
biggest=max(nx.connected_components(sub), key=len)
s,w,n,e=wg.corridor['bedok']
from app.services.walking import haversine
def nearest_in(nodes, lon, lat):
    return min(((haversine(lat,lon,wg.nodes[x][1],wg.nodes[x][0]),x) for x in nodes))
for N in [25]:
    bad=0; under=0; ex=[]
    for i in range(N):
        for j in range(N):
            lon=w+(e-w)*(j+0.5)/N if False else w+(e-w)*j/(N-1)
            lat=s+(n-s)*i/(N-1)
            d,node=nearest_in(sub.nodes, lon, lat)
            if d>=100: continue
            under+=1
            if node not in biggest:
                bad+=1; ex.append((round(lon,4),round(lat,4),round(d)))
    print('grid',N,'snap<100',under,'on small piece',bad, ex[:5])
# example
lon,lat=103.937,1.3197
d,node=nearest_in(sub.nodes,lon,lat); db,_=nearest_in(biggest,lon,lat)
print('example snap',round(d),'in biggest',node in biggest,'dist to biggest',round(db))
try:
    p=planner.plan_trip({"coord":[lon,lat]}, datetime(2026,9,21,10,30,tzinfo=SGT))
    print('plan ok', p['summary']['leave_by_label'])
except RuntimeError as ex: print('RuntimeError', ex)
