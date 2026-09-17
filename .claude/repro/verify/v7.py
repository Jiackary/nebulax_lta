from app import data
from collections import defaultdict
wg = data.walk_graph()
st = data.station_by_code()["EW16"]
import math
def d(a,b): return math.hypot((a[0]-b[0])*111320*math.cos(math.radians(1.28)), (a[1]-b[1])*110574)
by = defaultdict(list)
for e in wg.entrances:
    if e["area"]=="outram" and e["ref"]: by[e["ref"]].append((round(d(e["coord"], st["coord"])), e.get("name") or e.get("station"), e.get("wheelchair")))
for k,v in sorted(by.items()): print(k, v)
print("chosen by entrances_for:", {k:(round(d(v["coord"],st["coord"])), v.get("wheelchair")) for k,v in wg.entrances_for("outram").items()})
