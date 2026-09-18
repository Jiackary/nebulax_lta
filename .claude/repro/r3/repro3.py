from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.sources import datamall
from app.sources.base import Fetched
from app.config import SGT
def with_rows(rows):
    async def g(client=None): return Fetched(rows, datetime.now(SGT))
    datamall.lifts.get = g
with TestClient(app, raise_server_exceptions=False) as c:
    appt = (datetime.now(SGT)+timedelta(hours=14)).replace(minute=0, second=0, microsecond=0)
    tid = c.post("/api/trips", json={"appointment_at": appt.isoformat()}).json()["trip_id"]
    with_rows([{"Line":"EWL","StationCode":"EW5","LiftID":"","LiftDesc":f"Exit {x} Street level - Concourse"} for x in "ABC"])
    r = c.get(f"/api/trips/{tid}/status"); print("status all Bedok exits out:", r.status_code, r.text[:200])
    o = c.get(f"/api/trips/{tid}/offline"); j=o.json(); print("offline:", o.status_code, "snapshot", j.get("status_snapshot"), j["steps_plain"][0])
    with_rows([{"Line":"EWL","StationCode":"EW16","LiftID":"","LiftDesc":f"Exit {x} Street level - Concourse"} for x in "12345678"])
    r = c.get(f"/api/trips/{tid}/status"); print("status all Outram numbered exits out:", r.status_code)
    t = c.get(f"/api/trips/{tid}").json(); print("plan now alights at", t["legs"][2]["from"].get("exit_code"), t["legs"][2]["instruction"])
