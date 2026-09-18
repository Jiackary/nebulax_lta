import networkx as nx
from app import data
from app.services import walking, planner
from app.services.walking import haversine
wg=data.walk_graph()
cand=wg.candidates('bedok',True)
sub=wg.step_free.subgraph(cand)
biggest=max(nx.connected_components(sub), key=len)
s,w,n,e=wg.corridor['bedok']
def near(lon,lat):
    return min(((haversine(lat,lon,wg.nodes[x][1],wg.nodes[x][0]),x) for x in cand))
for mode in ['linspace','centers']:
    under=bad=0
    for i in range(25):
        for j in range(25):
            if mode=='linspace': lon=w+(e-w)*j/24; lat=s+(n-s)*i/24
            else: lon=w+(e-w)*(j+.5)/25; lat=s+(n-s)*(i+.5)/25
            d,x=near(lon,lat)
            if d<100:
                under+=1
                if x not in biggest: bad+=1
    print(mode,'snap<100',under,'small piece',bad)
from datetime import datetime
from app.config import SGT
fails=0; ok=0; other=0
for i in range(25):
    for j in range(25):
        lon=w+(e-w)*(j+.5)/25; lat=s+(n-s)*(i+.5)/25
        d,x=near(lon,lat)
        if d>=100: continue
        small = x not in biggest
        try:
            planner.plan_trip({"coord":[lon,lat]}, datetime(2026,9,21,10,30,tzinfo=SGT)); r='ok'
        except RuntimeError as ex: r=str(ex)
        if small: 
            if 'no step-free' in r: fails+=1
            else: ok+=1
        elif r!='ok': other+=1
print('small-piece 400 no-route',fails,'small-piece ok',ok,'big-piece failures',other)
