import asyncio, pathlib, sys, httpx
from app.sources import base, datamall
tmp=pathlib.Path(sys.argv[1])/"fx2"; tmp.mkdir(exist_ok=True); base.FIXTURES=tmp
print("USE_FIXTURES", base.USE_FIXTURES)
hits=[]
def h(r): hits.append(str(r.url)); return httpx.Response(200, json={"value":[1]})
async def main():
    src=base.Source("nofixture", ttl=60, fetch=lambda c: c.get("https://example.invalid/x"))
    await src.get(httpx.AsyncClient(transport=httpx.MockTransport(h)))
    print("network hits with USE_FIXTURES and missing fixture:", len(hits))
    f=datamall._fetch_crowd("EWL"); print("_fetch_crowd returns", type(f).__name__, "callable:", callable(f)); f.close()
asyncio.run(main())
