import sys, os, httpx, pathlib, json, re
sys.path.insert(0,"scripts")
os.environ["LTA_ACCOUNT_KEY"]="FAKEKEY"
import build_data as bd
S=pathlib.Path(sys.argv[1])
LINK="https://s3.ap-southeast-1.amazonaws.com/bucket/f.zip?X-Amz-Algorithm=AWS4&X-Amz-Security-Token=FAKETOKEN123&X-Amz-Signature=abc"
def h(req):
    if "datamall" in req.url.host: return httpx.Response(200, json={"value":[{"link":LINK}]})
    return httpx.Response(403)
Orig=httpx.Client
class C(Orig):
    def __init__(self,*a,**k): k["transport"]=httpx.MockTransport(h); super().__init__(*a,**k)
bd.httpx.Client=C
try: bd._download_link("GTFSScheduleTrain", S/"x.zip")
except Exception as e: print(type(e).__name__, "|", str(e).replace("\n"," / "))
# D5
bd.CACHE=S/"cache"; import shutil; shutil.rmtree(bd.CACHE, ignore_errors=True); bd.CACHE.mkdir()
calls={"n":0}
def h2(req):
    if "BusRoutes" in req.url.path: return httpx.Response(200, json={"value":[{"ServiceNo":"1"}]})
    return httpx.Response(500)
def mk(handler):
    class C2(Orig):
        def __init__(self,*a,**k): k["transport"]=httpx.MockTransport(handler); super().__init__(*a,**k)
    return C2
bd.httpx.Client=mk(h2)
try: bd.fetch_bus()
except BaseException as e: print("first fetch_bus:", type(e).__name__)
print("cache files:", sorted(p.name for p in bd.CACHE.iterdir()))
bd.fetch_bus()
try: bd.build_bus_options()
except BaseException as e: print("build_bus_options:", type(e).__name__)
