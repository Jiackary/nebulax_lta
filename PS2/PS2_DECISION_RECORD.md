# PS2 — Decision Record: which persona we build for

**Decision.** Build for **Mdm Lim**, the accessibility-constrained occasional traveller.
**Status.** Accepted, 17 Sep 2026. All three pre-commitment checks run against live APIs and passed.
Build decisions (§7) and a draft privacy statement (§8) added the same day, after an adversarial
review of this record. Where §7 corrects an earlier section, the original text is kept and marked.
**Supersedes.** Nothing. This is the first persona decision.

This record exists so the choice is auditable: what we checked, what the APIs actually
returned, and why the evidence points where it does. Material here feeds directly into
`WRITEUP.md` at submission, which must name the persona, state assumptions, and say how
every claimed number was derived.

Companion documents: [`PS2_INDEX.md`](PS2_INDEX.md) for source provenance, and the
published comparison report for the full Mdm Lim vs Arjun analysis.

---

## 1. Context

The brief (`PS2_README.md:L24–L39`) defines three personas and requires us to name one:

| Persona | Journey | Defining need |
|---|---|---|
| Rachel | Tampines → Raffles Place, EWL, fixed 07:40 | Interrupt only when it matters, one line |
| Arjun | Punggol → one-north, cycle + LRT + bus, ~1 h flexible start | Comfort and crowding over speed |
| Mdm Lim | Bedok → Singapore General Hospital, fortnightly | Step-free, lifts, shelter, large text, advance planning |

Constraint: judging is three days out. Build time was treated as a secondary criterion at
the user's direction — the question asked was which submission scores best, not which is
cheapest to produce.

**Rachel was eliminated early.** Route planning is a mandatory capability
(`PS2_README.md:L239–L250`) and a submission missing it cannot exceed level 3 on that part
of the score. Rachel rides one route she has ridden for four years, so we would have to
build door-to-door routing to satisfy the rubric and then demo a persona who never exercises
it. Under time pressure, building something you cannot show off is the worst available
trade. The real contest was Mdm Lim vs Arjun.

---

## 2. The three checks

The comparison report identified three things that could veto Mdm Lim. All three were run
on **17 Sep 2026** against live APIs with a registered DataMall `AccountKey`.

### Check 1 — Does `v2/FacilitiesMaintenance` actually return anything?

**Why it mattered.** The brief warns the feeds are quiet most days
(`PS2_README.md:L217`). If lift outages are rare, the demo needs labelled injected data —
permitted, but weaker. This was Mdm Lim's largest risk.

```bash
curl -s -H "AccountKey: $LTA_ACCOUNT_KEY" \
  "https://datamall2.mytransport.sg/ltaodataservice/v2/FacilitiesMaintenance"
```

**Result: PASS.** `HTTP 200`, four live lift outages. Captured verbatim at
`evidence/FacilitiesMaintenance_20260917T130227Z.json` (21:02 SGT). Re-fetched minutes
after the first call and byte-identical, so the feed is stable rather than flickering.

| Line | Station | LiftID | LiftDesc |
|---|---|---|---|
| `DTL` | `DT10` Stevens | `B3L02` | `(TEL) EXIT A STREET LEVEL - PLATFORM B - PLATFORM A` |
| `NEL` | `NE14` Hougang | `B1 L01` | `Exit A Street level - Concourse` |
| `NEL` | `NE5` Clarke Quay | `B1L01` | `Exit E Street level - Concourse` |
| `BPLRT` | `BP12` Jelapang | *(empty)* | `Lift 1 (connecting concourse to Platform 1)` |

The demo can run on real outages. No replay, no labelling caveat.

> **Corrected by D1 (§7.1).** The check proves the feed is live. It does not show that an outage
> will be on her route: none of the four is at Bedok or Outram Park. The demo outage is injected
> and labelled.

### Check 2 — Is OSM step-free tagging good enough on her corridor?

**Why it mattered.** Her entire routing premise is that stairs, lifts and step-free paths
are mapped. If the tagging is thin, the product does not work and we switch to Arjun. This
was the check most likely to fail.

Queried via Overpass (no key required), results cached rather than re-queried, per the
brief's instruction not to loop on the public instance (`PS2_README.md:L57`).

```bash
# Island-wide entrance survey
curl -A "<descriptive-UA>" https://overpass-api.de/api/interpreter --data-urlencode \
 'data=[out:json][timeout:120];
  area["name"="Singapore"]["boundary"="administrative"]->.sg;
  (node(area.sg)["railway"="subway_entrance"];
   node(area.sg)["railway"="train_station_entrance"];);
  out tags;'
```

> A default `curl` User-Agent gets `406 Not Acceptable` from Overpass. Set a descriptive one.

**Result: PASS.**

Island-wide, 523 MRT/LRT entrances mapped:

| Signal | Coverage |
|---|---|
| Entrances carrying `ref` (the exit label — our join key) | **499 / 523 — 95%** |
| Entrances carrying a `wheelchair` tag | 314 / 523 — 60% (253 `yes`, 56 `no`) |
| `highway=elevator` features island-wide | 775 (326 with `level` data) |

Her corridor specifically:

| | Bedok (origin) | Outram Park (destination) | SGH walk |
|---|---|---|---|
| Entrances with `ref` | 3 / 3 — `A B C` | 9 / 9 — `1`–`8` | — |
| With `wheelchair` tag | 2 / 3 (`yes`) | 5 / 9 (one is `wheelchair=no`) | — |
| Elevators tagged | **0** | 9, most with `level` | 2 |
| Steps ways | 23 | 94 | 16 |
| Covered ways | 79 | 65 | 55 |

Two caveats worth carrying forward. **Bedok has zero elevators tagged in OSM** despite being
an aboveground station that certainly has them, so at her origin we fall back on
`wheelchair=yes` on entrances B and C plus LTA's lift feed rather than routing through a
mapped elevator node. And `wheelchair=no` on Outram Park exit 5 is a useful *negative* —
an exit to actively route her away from.

### Check 3 — Does `TrainStationExit` carry exit labels we can join on?

**Why it mattered.** `LiftDesc` says `"Exit B …"`. Without an exit-labelled geospatial
layer, that string cannot be resolved to a location and the lift feature degrades from
exit-level to station-level, which is much less interesting.

```bash
curl -s -H "AccountKey: $LTA_ACCOUNT_KEY" \
  "https://datamall2.mytransport.sg/ltaodataservice/GeospatialWholeIsland?ID=TrainStationExit"
# returns a 5-minute-expiry S3 link to a SHP zip — download immediately
```

**Result: PASS.** Layer dated `Jul2026`. 613 exits across 188 stations. Two attributes:
`stn_name` and `exit_code`.

- `exit_code` uses the **same convention as `LiftDesc`** — 468 lettered (`Exit A`), 145 numbered (`Exit 1`).
- Station name suffixes are clean: `MRT STATION` ×541, `LRT STATION` ×72 — one regex to normalise.
- **No station code in the layer**, so the join to `FacilitiesMaintenance` runs through the station *name*.

---

## 3. The join, tested end to end

Having all three sources, we ran the actual product logic rather than confirming the parts
existed separately. This is the evidence that matters most.

### 3.1 LTA exit positions vs OSM entrance nodes

Reprojected `TrainStationExit` from SVY21 to WGS84 and measured haversine distance to the
matching OSM entrance node.

**11 of 12 pairs agree within 40 m.**

| Station | Exit | Separation |
|---|---|---|
| Bedok | A / B / C | 25.9 m / 11.2 m / 15.5 m |
| Outram Park | 4 / 6 / 8 | 7.0 m / 4.7 m / 5.9 m |
| Outram Park | 1 / 2 / 3 / 5 / 7 | 38.0 / 36.0 / 24.7 / 10.6 / 12.3 m |
| Outram Park | duplicate `ref=3` in OSM | **379.9 m — mis-tag, filter on distance** |

The two datasets describe the same physical doors.

### 3.2 Live outage → exit

**2 of 4 joined cleanly.** *(Re-measured 17 Sep after the GTFS rework — see the note below.)*

| Row | Outcome |
|---|---|
| `NE14` Hougang `Exit A` | matched |
| `NE5` Clarke Quay `Exit E` | matched |
| `BP12` Jelapang | no exit in `LiftDesc` — an internal concourse-to-platform lift, correctly **not** an exit outage |
| `DT10` Stevens `EXIT A` | **mismatch** — exit layer holds only `1`–`5` for Stevens |

The Stevens failure is real and instructive: it is a DTL/TEL interchange, and the `(TEL)`
half uses exit letters the DTL-era layer does not carry. **Interchange stations served by
two operators are the failure mode.** Critically the failure is *detectable* — a parsed exit
absent from the station's known exit set — so the app degrades to a station-level warning
rather than mis-routing her silently.

Carry `2/4` into `WRITEUP.md` as a stated limitation. It is small, honest and checkable,
which the rubric rewards over a large unverifiable figure.

> **Re-measured at backend stage 4, 17 Sep 2026 — `2/4` stands, and the breakdown is the
> better number to quote.** The matcher was reworked to key on GTFS `stop_code` and resolve
> through `parent_station` (I3), and re-run against the same live feed. The figure did not move,
> because the Stevens failure was never a keying problem: GTFS lists DT10's entrances as `1`–`5`,
> exactly as the shapefile does, so the `(TEL)` lettered exits are absent from **both** LTA
> sources and nothing we can key on reaches them.
>
> What the rerun does give us is a breakdown worth stating instead of a bare fraction:
>
> | | Count | |
> |---|---|---|
> | Rows naming an exit | **3 of 4** | Jelapang is an internal concourse-to-platform lift, correctly not an exit outage |
> | Of those, resolved to a known exit | **2 of 3** | Hougang `Exit A`, Clarke Quay `Exit E` |
> | Exit-level join overall | **2 of 4** | unchanged |
>
> The single failure is **detected, not silent**: Stevens resolves to `unmatched`, which renders
> as "a lift at this station" and never names an exit we cannot confirm. Reproduce with
> `backend/scripts/score_rules.py`.

---

## 4. Findings that change how we build

Discovered during the checks, not present in the brief or the API guide.

1. **A third spelling of Bukit Panjang LRT.** `v2/FacilitiesMaintenance` returns
   `Line: "BPLRT"`. The API guide documents `BPL` for Train Service Alerts and `BPL` for
   crowd density. The canonical line table needs all three. This case is **not** in the
   guide's own line-code trap table (extends trap T1 in `PS2_INDEX.md`).
2. **`TrainStationExit` ships in SVY21, not WGS84.** The bundled `.prj` is Singapore's
   national projected grid. Reproject before overlaying on an OSM base. Verified working
   with `pyproj` straight from the `.prj`.
3. **`LiftDesc` has no fixed format.** Four rows produced ALL CAPS and Title Case, a `(TEL)`
   line prefix, and an internal-lift description with no exit at all. `LiftID` gave
   `B3L02`, `B1 L01` (with a space) and an empty string. Parse defensively; treat a failed
   parse as a station-level warning.
4. **DataMall masks unauthorized as `404 "The requested API was not found"`**, not `401`.
   During the build, suspect the key before suspecting the URL.

---

## 5. Why Mdm Lim and not Arjun

The checks removed the reasons not to build her. These are the reasons to.

### 5.1 The rubric

Weights are Problem Fit **40%**, Technical Execution **35%**, Ease of Use **25%**
(`PS2_README.md:L276–L292`).

- **Problem Fit — Mdm Lim, clearly.** The criterion asks whether a real commuter is better
  off with the app than without it. Arjun is already well served: Citymapper and Google Maps
  do multi-modal routing, crowding hints and departure-time suggestions today. Mdm Lim is
  served by essentially nothing — no consumer app in Singapore routes on lift availability
  at exit granularity. The delta is the score, and hers is far larger.
  *Corrected by D12 (§7.4): MyTransport.SG and SMRT's app do show lift availability. The gap
  is narrower than "essentially nothing".*
- **Technical Execution — close, slight edge to Arjun on visible surface area.** He touches
  more modes and more endpoints. But the criterion reads "breadth *and judgement* of the
  data brought in," and her build wins on judgement: `SilverZone` (LTA's elderly-pedestrian
  zones, mentioned nowhere in the brief), `PedestrainOverheadbridge_UnderPass` used
  *inverted* as an obstacle map because an overhead bridge means stairs, and a free-text-to-
  geometry join harder than anything in Arjun's pipeline.
  *Corrected by D10 (§7.3): both layers are dropped, and "an overhead bridge means stairs"
  does not hold.*
- **Ease of Use — Mdm Lim, decisively.** Accessibility is named inside this criterion and
  again inside the visualisation requirement. Building for her means the accessibility work
  *is* the product rather than a pass made at the end. Arjun's side-by-side comparison view
  is the hardest interface in this brief to land one-handed on a phone, and the brief warns
  twice that a visual element which does not earn its place is worse than not having it.

65% of the total sits where she leads. The brief states that weighting is deliberate:
*"a technically impressive app that a commuter would not open twice cannot score well here,
and that is deliberate."*

### 5.2 The decisive argument: what you can defend

Judges ask you to defend one claim per criterion, and a claim a judge cannot check does not
score (`PS2_README.md:L292`; `submission/README.md:L67–L85`).

| | Central claim | Checkable? |
|---|---|---|
| Mdm Lim | "This route has no stairs." | **Yes** — open the route, look for a staircase. Binary and falsifiable. |
| Arjun | "This route is more comfortable." | **No** — it resolves to weights we chose. No feed observes comfort. |

Arjun's supporting data makes this concrete. Station crowd density measures the *station*,
not the train boarded. Bus `Load` measures one arriving *bus*. There is no train-car loading
feed anywhere in DataMall. And the last clause of his persona — whether he can bring his
bike — has **no feed behind it at all**; it is operator policy, so it would be hardcoded.

This asymmetry does not close with better execution. A brilliantly built Arjun still makes
an unfalsifiable central claim; a merely competent Mdm Lim makes a falsifiable one.

> **Narrowed by D11 (§7.4).** "This route has no stairs" can only be checked against OSM, and
> station interiors are not modelled. The claim we defend is the narrower one in D11. Arjun's
> side is also overstated: "platform forecast `m` instead of `h`" is checkable against
> `PCDForecast`. Keep this comparison out of `WRITEUP.md`.

### 5.3 What we are giving up

Recorded honestly, because these are real.

- **Arjun demos better.** Four modes on a map, live crowd levels, a "leave twenty minutes
  later" recommendation. It photographs well and reads as sophisticated within ten seconds.
- **Arjun carries no demo data risk.** Crowding is present every day. Check 1 has now
  largely neutralised this advantage, but it was genuine.
- **`PCDForecast` is the single best persona-to-endpoint fit in the brief** — 30-minute
  crowd buckets published a day ahead, exactly the shape of Arjun's flexible hour. We are
  leaving that on the table.

---

## 6. Limitations to carry into `WRITEUP.md`

State all of these. The brief credits stated assumptions and known limits.

1. **The day-before lift warning reflects status at check time only.** `v2/FacilitiesMaintenance`
   carries no date fields, so we **detect rather than predict**. We check her route at 20:00 the
   evening before and again at 07:00 on the day (D3). An outage that starts after the last check
   is not caught.
2. **Exit join succeeds on 2 of 4 live rows** — re-measured 17 Sep after the GTFS rework, and
   unchanged by it. Of the 4, three name an exit at all (the fourth is an internal lift), and
   two of those three resolve. The failure is Stevens, where the `(TEL)` lettered exits are
   missing from **both** LTA exit sources, so no join key recovers them. Failures are detected
   and degrade to a station-level warning, never to silent mis-routing.
3. **Bedok has no elevators mapped in OSM.** We rely on entrance `wheelchair` tags plus the
   LTA lift feed at her origin.
4. **Walking speed is assumed, not measured.** State the figure used. This matters more than
   it looks: after the D8 correction, walking pace contributes **47–64% of the whole timing
   range**, so the largest part of our stated uncertainty rests on an assumption rather than
   on data.
5. **OSM entrance `wheelchair` coverage is 60%**, so absence of the tag is not evidence of
   inaccessibility. Treat unknown as unknown, not as unusable.
6. **The provided station GeoJSON is a 2017 planning snapshot** with no station codes and 13
   null names; we use it only for `GRND_LEVEL`. See trap T13 in `PS2_INDEX.md`.
7. **The demo lift outage and the EWL disruption are injected, not live,** and labelled as such
   on screen (D1, D2). Real outages elsewhere on the network are shown live.
8. **Station interiors are not modelled.** The step-free claim covers OSM-mapped walking legs
   and the entrances and exits used, not the route inside a station (D11).
9. **Crowding is per station, not per train,** and it does not change her route (D9).
10. **Rain is judged at the 2-hour nowcast's area resolution,** not at her street (D9).

---

## 7. Build decisions

Accepted 17 Sep 2026. Each entry says what we build, why, and what it costs. §7.5 sets what
gets cut if time runs short. Decision numbers (D1–D14) are referenced from §5 and §6.

### 7.1 Demo and evidence

**D1. The demo lift outage is synthetic and labelled.** Live outages on 17 Sep were at Stevens,
Hougang, Clarke Quay and Jelapang. None is on Bedok → Outram Park, and a real outage at either
of her stations before judging is unlikely. We inject one outage at Outram Park in the exact
`v2/FacilitiesMaintenance` shape and label it on screen and in `WRITEUP.md`. No poller.

**D2. In an EWL disruption she gets three options, before she leaves home.** The scenario is a
labelled replay of the Annex C lifecycle (S4 p.58–72). Bedok is in predefined free-shuttle area 3
(`PS2_INDEX.md` §5.3). Each option is shown against the original route with its time cost.

1. **Leave later.** Offered when the delay parsed from `Message` ("additional travelling time of
   N minutes") fits within her buffer before the appointment. She keeps her usual step-free route.
2. **Regular bus to SGH.** `v3/BusArrival` is checked for `Feature=WAB` and `Load=SEA`.
3. **Barrier-free taxi.** The nearest `TaxiStands` entry flagged `Bfa`, with a walking route to
   it. No fare estimate, because we cannot verify one.

Free bridging buses and MRT shuttles are not offered. They run crowded and standing, which is
the wrong trade for a slow walker who avoids improvising.

**D3. The day-before warning checks at 20:00 and again at 07:00.** The feed has no dates (trap
T8), so each check sees only what is broken at that moment. No figure is claimed for how often
an evening outage is still there next morning. Limitation 1 in §6 carries the wording.

### 7.2 Architecture

**D4. Warnings go out by Web Push, with an in-app banner as fallback.** This stays a pure web
app, with no app store and no native build. Android Chrome delivers push from a normal tab once
she allows notifications. On iPhone she first adds the site to her Home Screen (iOS 16.4+), and
the app walks her through it once. Without push, the warning shows as a banner when she opens
the app. A "send test warning now" button lets judges see it without waiting for 20:00.

**D5. A hosted HTTPS deployment for phones, plus a README that runs it locally.** Push and
offline caching both need HTTPS, and the 20:00 check needs a process that is always running.
Judges open the hosted link on a phone. The README runs the same code on a clean machine, with
a free tunnel (e.g. `cloudflared`) to give a phone an HTTPS address. The DataMall key lives in
the host's environment variables, never in the repository.

**D6. Underground, her whole trip is cached on the phone.** Saved when she plans or opens the
trip: the step list in large text, her exits and lifts, and map tiles for her route only.
Offline, the screen reads "No signal: plan as of HH:MM", and nothing live is presented as
current. Tiles are cached only as the tile provider's terms allow (`PS2_README.md:L57`). This is
the no-signal choice the brief asks us to state (`PS2_README.md:L215`).

### 7.3 Data

**D7. Lift outages are matched to exits automatically, with a hand-checked table for her two
stations.** The matcher from §3.2 runs island-wide, so real outages elsewhere appear correctly
and show the live path works alongside the synthetic one. Bedok and Outram Park get a
hand-checked table of every lift, the exit it serves and whether it is step-free, built from
OSM, `TrainStationExit` and a manual read of the operators' station pages. Outram Park is a
three-line, two-operator interchange, the same shape as Stevens where matching failed, and the
2/4 test in §3.2 never touched it. A row that cannot be matched becomes a station-level warning.

**D8. GTFS train timetable. Committed, not conditional.** API guide v6.9 (S4b in
`PS2_INDEX.md`) adds `GTFSScheduleTrain`. It was tested live on 17 Sep with our key: `HTTP 200`,
a 2.3 MB feed with **1,211 stops, 17,576 trips and 333,262 stop_times**. The OneMap fallback is
dropped — there is nothing left to fall back from.

We keep it for two things:

1. **The canonical station table.** `stops.txt` gives 217 `stop_code` values with names and
   coordinates, and **`parent_station` unifies 28 interchanges across line codes** — Outram Park
   is `EW16 ← {EW16, NE3, TE17}`, Stevens is `DT10 ← {DT10, TE11}`. This is the table
   `PS2_README.md:L134` tells us to build, and it is the better key for the exit matcher in D7.
2. **Headways, for the timing range.** Weekday westbound at Bedok: 2.5 min median between
   08:00–09:00, 5.0 min between 13:00–14:00.

> **Corrected by I1 (`PS2_BACKEND_PLAN.md` §2).** The original text said GTFS "supplies frequency
> and **ride-time ranges** for the EWL leg, which is how timing uncertainty is made visible". The
> ride-time half is false and a judge can disprove it from the same feed in two minutes: across
> **all 698 EW5→EW16 trips the ride time is 30.7 minutes exactly** — minimum, median and maximum
> identical. The East-West Line timetable carries no run-time variation at all. (Nor do NSL or
> NEL. DTL has 2 distinct values and TEL has 11, so do not generalise this beyond her line.)
>
> **Timing uncertainty therefore comes from wait time and walking pace, not from ride time.** For
> her trip the budget is: walk 4.5 min of spread, wait 0–5 min at her hour, ride 0.0. Total range
> 7 min at peak, 9.5 off-peak. The requirement in `PS2_README.md:L248` is still met — only its
> basis changes. `WRITEUP.md` must describe it this way, and the wording in
> `PS2_API_CONTRACT.md` (`summary.timing_basis`) is already correct.
>
> Note also that GTFS is a **schedule, not a stopwatch**. Real trains vary; LTA's timetable does
> not record it, and no feed exposes it to us (see the realtime note below). Say "scheduled 31
> minutes", not "31 minutes".

**The two GTFS realtime feeds are not used.** Verified on 17 Sep:
`GTFSRealtimeTrainTripUpdates` returned **15 bytes — a header and no entities** on a normal day,
confirming it only populates during a disruption. `GTFSRealTimeTrainServiceAlerts` did carry one
entity, but it duplicates what `TrainServiceAlerts` already gives us in JSON rather than protobuf.
Our disruption is a `TrainServiceAlerts` replay either way.

**D9. Rain changes her walking route; crowding is shown but changes nothing.** When the 2-hour
nowcast forecasts rain for her home or SGH area, walking legs keep to `CoveredLinkWay` even when
longer, and the app says why. Station crowding from `PCDRealTime` appears as one badge per
station for Bedok and Outram Park, as a word plus colour. That covers the crowding item in the
visualisation requirement (`PS2_README.md:L266`), which would otherwise risk the level-3 cap.
`PCDForecast` departure advice and `PubFloodAlerts` are out of scope.

**D10. `PedestrainOverheadbridge_UnderPass` and `SilverZone` are dropped.** The premise that an
overhead bridge means stairs does not hold. Within 1.5 km of SGH and of Bedok, 8 of 109 OSM
footbridges have a mapped lift within about 40 m (Overpass, 17 Sep 2026). OSM `highway=steps`
already keeps her off bridge stairs, and `SilverZone` changes no route we can name. `WRITEUP.md`
gets two lines on why both were considered and rejected.

### 7.4 Claims

**D11. The step-free claim is narrow and backed by a script.** The claim: no walking leg uses an
OSM-mapped staircase, and every station entrance or exit used is either `wheelchair=yes` in OSM
or has an in-service lift in `v2/FacilitiesMaintenance`. A script in the repository plans her
trip and prints the check next to a plain foot route for the same trip, and states that station
interiors are not modelled. If the plain foot route has no steps on her corridor, the comparison
half is dropped and the rest stands.

**D12. `WRITEUP.md` does not mention competitors.** Have one spoken line ready in case a judge
raises MyTransport.SG, SMRT's app or Google Maps' wheelchair-accessible option: what we add is
moving her walk to a different exit when a lift is out, and warning her the evening before.

**D13. No model.** Delay minutes in `Message` and exit references in `LiftDesc` are parsed with
rules. The rules are scored on every example we hold (the Annex C messages, the four captured
`LiftDesc` rows, and notices copied by hand from `t.me/s/sgmrt`), and `WRITEUP.md` reports the
result as n/N with the examples shipped. A short section argues why rules beat a model here: the
text is formulaic, rules run offline and instantly, and judges can check them without paying
(`PS2_README.md:L312`, `L316`).

### 7.5 Scope

**D14. Never cut:**

- Door-to-door route (step-free walks, EWL leg) on an OSM map with attribution
- Lift outage reroute (D1, D7)
- EWL disruption replay with alternatives shown against the original (D2)
- Visuals: affected route section shown by pattern and label, crowd badges, large text
- Web Push with the 20:00 and 07:00 checks and the banner (D3, D4)
- Offline trip, including map tiles (D6)
- Rain → sheltered walk (D9)
- Hosting and README (D5), step-free script (D11), measured rules and write-up (D13)

**Cut in this order if time runs short:**

1. Barrier-free taxi option (D2.3)
2. Live bus checks, keeping a plain OneMap bus route (D2.2)
3. GTFS **headways** for the timing range, falling back to published frequencies (D8).
   Note this cuts only the headway use. `stops.txt` stays regardless — it is the canonical
   station table the exit matcher keys on (D7, D8.1), and removing it breaks the matcher.

---

## 8. Privacy statement (draft for `WRITEUP.md`)

The brief requires it: *"If your app collects a user's routine or location, say in your
submission what you store, where, and for how long"* (`PS2_README.md:L208`). D3–D6 mean we store
her trips on a server, so this applies.

The draft makes promises the build must keep. Before copying it into `WRITEUP.md`, check each
item in the list after it against the code, and fill the bracketed placeholders once hosting,
tiles and routing are chosen.

> **Privacy: what we store, where, and for how long**
>
> The app has no accounts. It never asks for a name, phone number or email address.
>
> **On the phone**, in the browser's own storage: the home location she enters, her upcoming
> appointments, her text-size setting, and a saved copy of each trip with map tiles for its
> route. This stays on the phone until she deletes the trip or clears the site's data.
>
> **On our server**, only what the evening and morning checks need: each planned trip (start
> and end coordinates, appointment date and time, and the stations, exits and lifts on the
> route) and the push subscription the browser issues so we can notify her phone. A trip is
> deleted from the server 24 hours after its appointment time, or immediately when she removes
> it or turns off notifications.
>
> **What we do not collect:** her live location. The app does not use the phone's location
> service; routes start from the home location she typed in.
>
> **Who else sees what.** Routing requests send a trip's start and end points to [routing
> service]. Map tiles come from [tile provider], which can see which part of the map is being
> viewed. Notifications pass through the phone's push service (Google or Apple), which sees that
> a message was sent but not its contents, because Web Push messages are encrypted. Requests to
> LTA DataMall and data.gov.sg carry no personal data. [Hosting provider] keeps standard request
> logs for [period]; the app does not write trip details to its logs.
>
> We do not share or sell this data, and we use it only to plan her trips and warn her about them.

**Commitments the build must meet for this to be true:**

1. Server trip records are deleted 24 hours after the appointment, and immediately on removal
   or when notifications are turned off.
2. The app never calls the browser's geolocation API.
3. Server logs never include request bodies or trip details.
4. No analytics or third-party scripts beyond the map library and tile provider.
5. Placeholders filled: routing service, tile provider, hosting provider and its log period.

---

## 9. Reproducing this

```bash
cp PS2/.env.example PS2/.env     # add your free AccountKey from datamall.lta.gov.sg
set -a; . PS2/.env; set +a
```

Then re-run the three commands in §2. Note that `GeospatialWholeIsland` returns a link
valid for five minutes only — download immediately, never cache the URL.

Captured evidence lives in `PS2/evidence/`. The credential lives in `PS2/.env`, which is
gitignored; `PS2/.env.example` lists the variable name only. The rubric caps the score for
a credential committed to the repository.
