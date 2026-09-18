import sys; sys.path.insert(0, sys.argv[1])
from common import *
import uvicorn, httpx, threading, time
from app.main import app
from app import data
data.walk_graph()
cfg = uvicorn.Config(app, host="127.0.0.1", port=0, lifespan="off", log_level="warning")
server = uvicorn.Server(cfg)
th = threading.Thread(target=server.run, daemon=True); th.start()
while not server.started: time.sleep(0.05)
port = server.servers[0].sockets[0].getsockname()[1]; U = f"http://127.0.0.1:{port}"
c = httpx.Client(timeout=60)
tid = c.post(U+"/api/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}).json()["trip_id"]
c.post(U+"/api/push/subscribe", json={"subscription": {"endpoint": BASE+"/slow", "keys": sub_keys()}, "trip_ids": [tid]})
t0=time.time(); print("health baseline", c.get(U+"/api/health").status_code, round(time.time()-t0,2))
res = {}
def fire():
    s=time.time(); r = httpx.post(U+"/api/push/test", params={"trip_id": tid}, timeout=60); res["t"]=round(time.time()-s,2)
threading.Thread(target=fire).start(); time.sleep(0.5)
t0=time.time(); r = c.get(U+"/api/health"); print("health during slow push", r.status_code, round(time.time()-t0,2))
time.sleep(6); print("push/test took", res)
