import asyncio, json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app import scenario, store
from app.sources import datamall
from app.sources.base import Fetched
from app.config import SGT
from app.services import lifts, disruption

for d in ["Exit6 Street level - Concourse", "EXIT NO. 6 STREET LEVEL", "Exits 6 & 7 Street level", "Exits 6, 7 Street level",
          "Exit 6/7/8 Street level", "Exits A/B Street level - Concourse", "Exit B (Street level - Concourse)", "(EWL) EXIT B STREET LEVEL", "Lift at Exit B",
          "Exit A1 Street level"]:
    r = lifts.match_row({"StationCode": "EW16" if any(ch.isdigit() for ch in d) else "EW5", "LiftDesc": d, "Line": "EWL"})
    print(repr(d), r["parsed_exits"], r["resolution"], r["exit_code"])

orig_get = datamall.lifts.get
def with_rows(rows):
    async def g(client=None):
        return Fetched(rows, datetime.now(SGT))
    datamall.lifts.get = g

with TestClient(app) as c:
    appt = (datetime.now(SGT)+timedelta(hours=14)).replace(minute=0, second=0, microsecond=0)
    for desc, code in [("Exits A/B Street level - Concourse", "EW5"), ("Exits 5/6 Street level - Concourse", "EW16"), ("Exit6 Street level - Concourse", "EW16"), ("EXIT NO. 6 STREET LEVEL - CONCOURSE", "TE17")]:
        tid = c.post("/api/trips", json={"appointment_at": appt.isoformat()}).json()["trip_id"]
        with_rows([{"Line": "EWL", "StationCode": code, "LiftID": "X", "LiftDesc": desc}])
        s = c.get(f"/api/trips/{tid}/status").json()
        t = c.get(f"/api/trips/{tid}").json()
        print(f"{desc!r}@{code}: rerouted={s['rerouted']} overall={s['overall']['detail']!r} plan exits={t['legs'][0]['to'].get('exit_code')},{t['legs'][2]['from'].get('exit_code')}")

# T6: bundled content, and wrong-line message
v = {"Status": 2, "AffectedSegments": [{"Line": "EWL", "Direction": "Tuas Link", "Stations": "EW5,EW6,EW7", "FreePublicBus": "", "FreeMRTShuttle": ""},
      {"Line": "NSL", "Direction": "Jurong East", "Stations": "NS1,NS2", "FreePublicBus": "", "FreeMRTShuttle": ""}],
     "Message": [{"Content": "1820hrs : NSL - Additional travelling time of 30 minutes towards Jurong East. EWL - Additional travelling time of 10 minutes towards Tuas Link.", "CreatedDate": "x"}]}
print("T6 bundled:", disruption.assess(v, "now")["delay_min"])
v2 = {**v, "Message": [{"Content": "1830hrs : NSL - Additional travelling time of 25 minutes towards Jurong East.", "CreatedDate": "b"},
                       {"Content": "1800hrs : EWL - Additional travelling time of 10 minutes towards Tuas Link.", "CreatedDate": "a"}]}
print("T6 separate msgs, NSL newest:", disruption.assess(v2, "now")["delay_min"])
# opposite direction
v3 = {"Status": 2, "AffectedSegments": [{"Line": "EWL", "Direction": "Pasir Ris", "Stations": "EW5,EW6", "FreePublicBus": ""},
                                          {"Line": "EWL", "Direction": "Tuas Link", "Stations": "EW5,EW6"}], "Message": []}
print("direction:", disruption.assess(v3, "now")["headline"])
# test broadcast with populated segment
v4 = {"Status": 2, "AffectedSegments": [{"Line": "EWL", "Direction": "Tuas Link", "Stations": "EW5,EW6"}],
      "Message": [{"Content": "Test : 1457hrs: EWL - Additional travelling time of 15 minutes"}]}
print("test-only:", disruption.assess(v4, "now"))
