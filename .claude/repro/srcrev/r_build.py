import sys, os, json
from pathlib import Path
sys.path.insert(0, "scripts")
os.environ["LTA_ACCOUNT_KEY"] = "FAKE-NOT-A-KEY"
import httpx, build_data as B
S = Path(os.environ["S"]) / "srcrev"
Real = httpx.Client
def h(req):
    if "datamall2" in str(req.url):
        return httpx.Response(200, json={"value": [{"link": "https://ltafarecard.s3.amazonaws.com/x.zip?X-Amz-Security-Token=SECRETTOKENabc&X-Amz-Signature=deadbeef"}]})
    return httpx.Response(403, text="Request has expired")
B.httpx.Client = lambda *a, **kw: Real(*a, **{**kw, "transport": httpx.MockTransport(h)})
try:
    B._download_link("GTFSScheduleTrain", S / "g.zip")
except Exception as e:
    print(type(e).__name__, "->", str(e)[:200])
# fetch_bus: BusStops failing after BusRoutes written
B.CACHE = S / "cache"; B.CACHE.mkdir(exist_ok=True)
for p in B.CACHE.glob("*"): p.unlink()
def h2(req):
    if "BusRoutes" in str(req.url): return httpx.Response(200, json={"value": [{"x": 1}]})
    return httpx.Response(500)
B.httpx.Client = lambda *a, **kw: Real(*a, **{**kw, "transport": httpx.MockTransport(h2)})
try: B.fetch_bus()
except Exception as e: print("fetch_bus 1st run:", type(e).__name__)
B.fetch_bus()
try: B.build_bus_options()
except Exception as e: print("build_bus_options:", type(e).__name__, e)
