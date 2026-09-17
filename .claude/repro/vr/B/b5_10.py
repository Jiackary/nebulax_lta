from common import *
from app.services import disruption, alternatives
import app.services.alternatives as alt
STN = "EW5,EW6,EW7,EW8,EW9,EW10,EW11,EW12,EW13,EW14,EW15,EW16"
def val(msgs, direction="Tuas Link", status=2):
    return {"Status": status, "AffectedSegments":[{"Line":"EWL","Direction":direction,"Stations":STN,"FreePublicBus":"","FreeMRTShuttle":"","MRTShuttleDirection":""}],
            "Message":[{"Content":c,"CreatedDate":"2026-09-19 08:12:00"} for c in msgs]}
# B5
bundle = "1820hrs : NSL - Additional travelling time of 30 minutes towards Jurong East. EWL - Additional travelling time of 10 minutes towards Pasir Ris."
d = disruption.assess(val([bundle]), "x"); print("B5 bundle", d["delay_min"], d["delay_basis"])
d = disruption.assess(val(["0830hrs : NSL - Additional travelling time of 25 minutes between A and B.", "0812hrs : EWL - Additional travelling time of 10 minutes between Bedok and Outram Park towards Tuas Link."]), "x"); print("B5 newer NSL", d["delay_min"])
# B6
d = disruption.assess(val(["0812hrs : EWL - Additional travelling time of 20 minutes between Bedok and Outram Park towards Pasir Ris."], direction="Pasir Ris"), "x"); print("B6 dir", d["headline"], d["delay_min"], d["on_her_route"])
d = disruption.assess(val(["Test : 1457hrs: EWL - Additional travelling time of 15 minutes"]), "x"); print("B6 test", d and (d["severity"], d["headline"], d["delay_min"]))
# via API: leave-earlier with Pasir Ris direction
t = mk_trip(); tid = t["trip_id"]
ALERT_OVERRIDE[0] = val(["0812hrs : EWL - Additional travelling time of 20 minutes between Bedok and Outram Park towards Pasir Ris."], direction="Pasir Ris")
r = client.get(f"/api/trips/{tid}/alternatives"); j = r.json()
print("B6 api", r.status_code, j.get("disruption",{}).get("headline"), [(o["option_id"], o.get("leave_by_label")) for o in j.get("options",[])])
# B9 arrival
for o in j.get("options", []):
    if o["option_id"] == "leave_earlier": print("B9", o["arrival_at"], o["why"], "appt", t["appointment_at"], "arr_window", t["summary"]["arrival_window"])
    if o["option_id"] == "taxi_bfa": print("B8", o["why"], o["taxi_stand"]["anchor"])
    if o["option_id"] == "bus_wab": print("B7", o["step_free"], o["why"], {k:o["bus"][k] for k in ("eta_min","not_running","wheelchair_accessible")})
ALERT_OVERRIDE[0] = None
# B7: wheelchair False
import app.sources.datamall as dm
class F: pass
async def run_bus(services):
    src = dm.bus_arrival("84009"); orig = src.get
    for code in ("84009","84039"):
        s = dm.bus_arrival(code)
        async def g(*a, _s=services, **k):
            f = base.Fetched(_s, datetime.now(SGT)); return f
        s.get = g
    return await alt._bus_option(datetime.now(SGT)+timedelta(hours=14), [103.93, 1.32])
from app import data
print("bus options", [(o["service_no"], o["board"]["code"]) for o in data.bus_options()["direct"]])
eta = (datetime.now(SGT)+timedelta(minutes=4)).isoformat()
svc = [{"ServiceNo": s, "NextBus": {"EstimatedArrival": eta, "Monitored": 1, "Load":"SEA", "Feature": ""}} for s in [o["service_no"] for o in data.bus_options()["direct"]]]
o = asyncio.run(run_bus(svc)); print("B7 nofeature", o["step_free"], o["why"], o["bus"]["wheelchair_accessible"])
o = asyncio.run(run_bus([])); print("B7 empty", o["step_free"], o["why"])
