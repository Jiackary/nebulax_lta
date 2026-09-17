from common import *
from app.services.lifts import parse_exits
t = mk_trip(); tid = t["trip_id"]
print("default exits", exits_of(t), t["summary"]["leave_by"])
# B1
EXTRA_LIFTS[:] = [{"Line":"EWL","StationCode":"EW16","StationName":"Outram Park","LiftID":"X","LiftDesc":"Exits 5/6 Street level - Concourse"}]
s = client.get(f"/api/trips/{tid}/status").json()
a = [x for x in s["lift_alerts"] if x["station_code"]=="EW16"][0]
print("B1", a["parsed_exits"], a["exit_code"], a["resolution"], "|", s["overall"]["detail"], "| rerouted", s["rerouted"])
print("B1 plan now", exits_of(client.get(f"/api/trips/{tid}").json().get("plan", client.get(f"/api/trips/{tid}").json())))
for d in ["Exits 6 & 7 Street level", "Exit 6, 7 Street", "6, 7", "Exit6 Street level - Concourse", "EXIT NO. 6 STREET", "Exits 5/6 Street"]:
    print("  parse", repr(d), parse_exits(d))
# B2
EXTRA_LIFTS[:] = [{"Line":"EWL","StationCode":"EW16","StationName":"Outram Park","LiftID":"X","LiftDesc":"Exit6 Street level - Concourse"}]
s = client.get(f"/api/trips/{tid}/status").json()
print("B2 station_only:", s["overall"], s["rerouted"])
EXTRA_LIFTS[:] = [{"Line":"EWL","StationCode":"EW16","StationName":"Outram Park","LiftID":"X","LiftDesc":"Exit 99 Street level - Concourse"}]
s = client.get(f"/api/trips/{tid}/status").json()
print("B2 unmatched:", s["overall"]["detail"])
EXTRA_LIFTS[:] = []
# B2 second call + B3
scenario.set_state(lift_outage_outram=True)
s1 = client.get(f"/api/trips/{tid}/status").json()
print("B3 call1", s1["rerouted"], s1["overall"]["detail"], s1["overall"]["action"])
s2 = client.get(f"/api/trips/{tid}/status").json()
print("B2 call2", s2["rerouted"], s2["overall"]["detail"], s2["overall"]["action"])
scenario.set_state(enabled=False, lift_outage_outram=False)
s3 = client.get(f"/api/trips/{tid}/status").json()
print("B3 off:", s3["overall"]["headline"], s3["rerouted"])
g = client.get(f"/api/trips/{tid}").json()
st = store.get_trip(tid)
print("B3 stored", exits_of(st["plan"]), st["plan"]["summary"]["leave_by"], st["plan"].get("rerouted"))
o = client.get(f"/api/trips/{tid}/offline").json()
print("B3 offline", o["steps_plain"][0], "|", o["steps_plain"][-1], o["plan"].get("rerouted"))
# B4
t2 = mk_trip(); tid2 = t2["trip_id"]
print("B4 plan", exits_of(t2))
EXTRA_LIFTS[:] = [{"Line":"EWL","StationCode":"EW5","StationName":"Bedok","LiftID":f"L{x}","LiftDesc":f"Exit {x} Street level - Concourse"} for x in "ABC"]
r = client.get(f"/api/trips/{tid2}/status"); print("B4 status", r.status_code, r.text[:200])
r = client.get(f"/api/trips/{tid2}/offline"); j = r.json(); print("B4 offline", r.status_code, j["status_snapshot"], j["steps_plain"][0])
EXTRA_LIFTS[:] = []
