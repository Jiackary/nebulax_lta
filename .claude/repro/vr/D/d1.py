import os, sys, json, shutil, asyncio, time, pathlib
os.environ["LTA_ACCOUNT_KEY"]="FAKEKEY"; os.environ.pop("PS2_USE_FIXTURES", None)
import httpx
from app.sources import base, datamall, weather
from app import config
S=pathlib.Path(sys.argv[1]); tmp=S/"fx"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
shutil.copy(config.FIXTURES/"bus_84009.json", tmp); shutil.copy(config.FIXTURES/"weather_2hr.json", tmp)
base.FIXTURES=tmp; datamall.LTA_ACCOUNT_KEY="FAKEKEY"; base.USE_FIXTURES=False
print("before", len(json.loads((tmp/"bus_84009.json").read_text())["payload"]))
async def main():
    def h(req): return httpx.Response(200, json={"BusStopCode":"84009","Services":[]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(h)) as c:
        src=datamall.bus_arrival("84009"); f=await src.get(c)
    print("bus origin",f.origin, "data",f.data, "fixture now", json.loads((tmp/"bus_84009.json").read_text())["payload"])
    def w(req): return httpx.Response(200, json={"code":24,"data":None,"errorMsg":"x"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(w)) as c:
        f=await weather.nowcast.get(c)
    print("wx origin",f.origin,"data",f.data,"fixture payload", json.loads((tmp/"weather_2hr.json").read_text())["payload"], "cached", weather.nowcast._entry.value)
    # PermissionError
    src2=base.Source("perm", ttl=60, fetch=lambda c: asyncio.sleep(0, result={"ok":1}))
    orig=base.Source._record
    def bad(self,v,o): raise PermissionError("ro fs")
    base.Source._record=bad
    f=await src2.get(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    print("perm origin",f.origin,"stale",f.stale,"err",f.error,"data",f.data)
    f=await src2.get(); print("perm 2nd call origin", f.origin)
    base.Source._record=orig
    # truncated fixture
    (tmp/"trunc.json").write_text('{"recorded_at": "2026-09-18T00:0')
    async def boom(c): raise httpx.ConnectError("down")
    src3=base.Source("trunc", ttl=60, fetch=boom)
    try:
        await src3.get(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    except Exception as e: print("trunc escaped:", type(e).__name__)
    # concurrency
    async def hang(c):
        await asyncio.sleep(1); raise httpx.ReadTimeout("t")
    src4=base.Source("hang", ttl=60, fetch=hang)
    t0=time.monotonic(); res=[]
    async def one(i):
        try: await src4.get(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        except Exception as e: pass
        res.append(round(time.monotonic()-t0,2))
    await asyncio.gather(*[one(i) for i in range(5)])
    print("concurrent return times", sorted(res))
asyncio.run(main())
