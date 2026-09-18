import os, json, copy, asyncio
from datetime import datetime, timedelta
import app.sources.base as base
base.Source._record = lambda self, v, o: None
from fastapi.testclient import TestClient
from app.main import app
from app.sources import datamall
from app import scenario, store
from app.config import SGT

EXTRA_LIFTS = []
ALERT_OVERRIDE = [None]
_orig_l = datamall.lifts.get
_orig_a = datamall.alerts.get
async def lget(*a, **k):
    f = await _orig_l(*a, **k)
    f = copy.copy(f); f.data = list(f.data) + [dict(r) for r in EXTRA_LIFTS]; return f
async def aget(*a, **k):
    f = await _orig_a(*a, **k)
    if ALERT_OVERRIDE[0] is not None:
        f = copy.copy(f); f.data = copy.deepcopy(ALERT_OVERRIDE[0])
    return f
datamall.lifts.get = lget
datamall.alerts.get = aget
store.init()
client = TestClient(app, raise_server_exceptions=False)

def mk_trip(appt=None):
    appt = appt or (datetime.now(SGT) + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
    r = client.post("/api/trips", json={"appointment_at": appt.isoformat()})
    assert r.status_code == 200, r.text
    return r.json()

def exits_of(plan):
    return [(l.get("mode"), (l.get("from") or {}).get("exit_code"), (l.get("to") or {}).get("exit_code")) for l in plan["legs"]]
