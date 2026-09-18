import asyncio, json, shutil, sys, time, os, stat
from pathlib import Path
sys.path.insert(0, ".")
import httpx
from app.sources import base, datamall, weather

S = Path(os.environ["S"]) / "srcrev" / "fx"
shutil.rmtree(S, ignore_errors=True); shutil.copytree("data/fixtures", S)
base.FIXTURES = S; base.USE_FIXTURES = False
datamall.LTA_ACCOUNT_KEY = "FAKE-NOT-A-KEY"

handler = None
Real = httpx.AsyncClient
def patched(*a, **kw):
    kw["transport"] = httpx.MockTransport(lambda req: handler(req)); return Real(*a, **kw)
base.httpx.AsyncClient = patched

async def main():
    # A. T17: empty Services at 01:00 overwrites the good recorded fixture
    global handler
    handler = lambda r: httpx.Response(200, json={"BusStopCode": "84009", "Services": []})
    before = len(json.loads((S/"bus_84009.json").read_text())["payload"])
    src = datamall.bus_arrival("84009")
    f = await src.get()
    after = json.loads((S/"bus_84009.json").read_text())["payload"]
    print("A bus fixture services before", before, "after", len(after), "origin", f.origin, "stale", f.stale)

    # B. 404 with no key -> fixture served; what provenance?
    handler = lambda r: httpx.Response(404, text="The requested API was not found")
    f = await datamall.lifts.get()
    print("B lifts on 404: origin", f.origin, "stale", f.stale, "observed", f.observed_iso, "err", (f.error or "")[:40])

    # C. outage latency amplification: upstream hangs; 5 concurrent callers with a stale in-memory entry
    datamall.alerts._entry = base._Entry({"AffectedSegments": []}, time.monotonic() - 999, base.datetime.now(base.SGT))
    async def slow(req):
        await asyncio.sleep(1.0); raise httpx.ReadTimeout("simulated", request=req)
    handler = None
    base.httpx.AsyncClient = lambda *a, **kw: Real(*a, **{**kw, "transport": httpx.MockTransport(slow)})
    t0 = time.monotonic()
    async def one():
        r = await datamall.alerts.get(); return round(time.monotonic() - t0, 1), r.origin
    print("C concurrent waits (1s upstream hang each):", await asyncio.gather(*[one() for _ in range(5)]))
    t0 = time.monotonic(); await datamall.alerts.get(); print("C next request still retries upstream:", round(time.monotonic()-t0,1), "s")

    # D. corrupt/partial fixture + upstream down -> JSONDecodeError escapes (not stale-serve)
    (S/"crowd_ewl.json").write_text('{"recorded_at": "2026-09-18T00:07:02+08:00", "source": "crowd_ewl", "payl')
    base.httpx.AsyncClient = patched
    handler = lambda r: httpx.Response(503)
    try:
        await datamall.crowd("EWL").get(); print("D ok")
    except Exception as e:
        print("D raised", type(e).__name__)

    # E. read-only fixtures dir: successful live fetch reported as stale
    handler = lambda r: httpx.Response(200, json={"code": 0, "data": {"area_metadata": [], "items": []}})
    os.chmod(S, stat.S_IRUSR | stat.S_IXUSR); os.chmod(S/"weather_2hr.json", stat.S_IRUSR)
    f = await weather.nowcast.get()
    print("E weather live 200 but read-only fixture dir: origin", f.origin, "stale", f.stale, "err", f.error)
    os.chmod(S, 0o755); os.chmod(S/"weather_2hr.json", 0o644)

    # F. data.gov.sg error body with 200 and data null gets cached + recorded
    weather.nowcast._entry = None
    handler = lambda r: httpx.Response(200, json={"code": 24, "data": None, "errorMsg": "rate limited"})
    f = await weather.nowcast.get()
    print("F weather data", f.data, "origin", f.origin, "fixture payload now", json.loads((S/"weather_2hr.json").read_text())["payload"])
asyncio.run(main())
