import networkx as nx
from app import data
from app.config import SGH
from app.services import walking
wg=data.walk_graph()
for area in ("bedok","outram"):
    cand=wg.candidates(area, True); sub=wg.step_free.subgraph(cand)
    main=max(nx.connected_components(sub), key=len)
    for e in wg.entrances:
        if e["area"]!=area: continue
        n,d=walking._snap(wg,e["coord"],area,True)
        md=min(walking.haversine(e["coord"][1],e["coord"][0],wg.nodes[m][1],wg.nodes[m][0]) for m in main)
        print(area,e["ref"],e["name"],e["wheelchair"],"snap",round(d),"in_sf_main",n in main,"nearest_sf_main",round(md))
    if area=="outram":
        n,d=walking._snap(wg,SGH["coord"],area,True); print("SGH snap",round(d), n in main)
for c in ([103.9362, 1.31902],[103.937, 1.3197]):
    cand=wg.candidates("bedok", True); sub=wg.step_free.subgraph(cand); main=max(nx.connected_components(sub), key=len)
    print(c, "nearest node in step-free main:", round(min(walking.haversine(c[1],c[0],wg.nodes[m][1],wg.nodes[m][0]) for m in main)))
