# PS2 — Backend Implementation Plan

**Source of truth:** [`PS2_DECISION_RECORD.md`](PS2_DECISION_RECORD.md) — persona in §5, limitations
in §6, build decisions D1–D14 in §7, privacy commitments in §8. This plan implements those
decisions and does not reopen them. Where it found a decision to be factually wrong, §2 says so
rather than quietly working around it.

**Frontend contract:** [`PS2_API_CONTRACT.md`](PS2_API_CONTRACT.md) — every field the backend
serves and what the screen does with it.

**Written** 17 Sep 2026, against branch `ps2-build-decisions` (`a37409c`).
All API behaviour below was verified live with our `AccountKey` on 17 Sep, not read off the guide.

---

## 1. What the backend has to do

From D14's never-cut list, the backend owes the frontend seven things:

| # | Capability | Decisions |
|---|---|---|
| 1 | A door-to-door step-free plan, Bedok → SGH, with visible timing uncertainty | D8, D11 |
| 2 | Lift-outage detection on her route, and a reroute to a different exit | D1, D7 |
| 3 | EWL disruption replay with three alternatives scored against the original | D2 |
| 4 | Crowd badges for her two stations | D9 |
| 5 | Rain → sheltered walking route | D9 |
| 6 | Evening and morning checks that fire a Web Push | D3, D4 |
| 7 | An offline bundle for the underground leg | D6 |

---

## 2. Issues found in the decision record

Raised rather than worked around. Four are factual corrections; four are gaps to close.

**Status as of 17 Sep 2026:** I1 and I2 are **resolved** — D8 was amended in the decision record
(see D8 in its §7.3). I3 is **applied but partly falsified** — see the measurement appended to it
below; the 2/4 join figure is re-measured at stage 4, not here. I6 is **parked** at the team's
direction. I7 is resolved by I9's decision to keep OneMap. I4, I5 and I8 are open.
I9–I11 were added during stage 1 and are all resolved.

### I1 — D8 is wrong that GTFS gives "ride-time ranges" · ~~correction needed~~ **RESOLVED**

D8 says `GTFSScheduleTrain` "supplies frequency and ride-time ranges for the EWL leg, which is
how timing uncertainty is made visible."

Measured from the real feed: **ride time is a single fixed value.** Across all 698 EW5→EW16
trips, ride time is `30.7 min` — minimum, median and maximum identical. The timetable carries no
run-time variation at all.

**Frequency does vary and is usable:** weekday westbound headway at Bedok is 2.5 min median
between 08:00–09:00 and 5.0 min between 13:00–14:00.

*Recommended amendment:* timing uncertainty comes from **headway (wait) + walking-speed band**,
not ride time. The honest range is `ride 30.7 fixed + wait 0–headway + walk at her assumed pace`.
This is still fully defensible and still satisfies `PS2_README.md:L248` — but D8's stated basis
must change or the write-up will claim something the data does not support.

### I2 — D8's condition is resolved: GTFS works · ~~firm up~~ **RESOLVED**

D8 is written conditionally ("if it returns usable data with our key") and time-boxed to an hour.
`GET /GTFSScheduleTrain` returns `HTTP 200` and a 2.3 MB feed: **1,211 stops, 17,576 trips,
333,262 stop_times, 19 routes**, with weekday/weekend/holiday calendars. The OneMap fallback is
not needed. Recommend promoting D8 from conditional to committed.

### I3 — GTFS `stops.txt` supersedes the name-join, and `parent_station` fixes the Stevens failure · **material improvement**

§3.2 records the exit join succeeding on only 2 of 4 live rows, with Stevens failing because
`LiftDesc` said `EXIT A` while the exit layer held only `1`–`5`. Trap T21 records that
`TrainStationExit` has no station code, forcing a name-based join.

GTFS supplies both missing pieces:

- **`stops.txt` is a canonical station table** — 217 `stop_code` values with names and
  coordinates. This is the table `PS2_README.md:L134` tells us to build, available free.
- **`parent_station` unifies 28 interchanges across line codes.** Stevens is exactly
  `DT10 ← {DT10, TE11}`. The `(TEL) EXIT A` row is a TEL-side exit; GTFS says TE11 shares parent
  DT10. Outram Park is `EW16 ← {EW16, NE3, TE17}` — the same shape, and the station D7 worried
  about most.

*Recommended amendment:* D7's hand-checked table for her two stations stays (it is cheap
insurance for the demo path), but the automatic matcher should key on GTFS `stop_code` and
resolve through `parent_station` before falling back to names. Re-measure the 2/4 figure after
this change and update §3.2, §6 limitation 2 and trap T21 with whatever it becomes.

> **Measured at stage 1, 17 Sep — the Stevens half of this is wrong.** `parent_station` does
> unify the interchanges exactly as claimed (28 of them, `EW16 ← {EW16, NE3, TE17}`,
> `DT10 ← {DT10, TE11}`), and that is what decides whether an outage is on her route. But it does
> **not** recover Stevens' `(TEL) EXIT A`: GTFS lists DT10's entrances as `1`–`5`, which is
> precisely what the shapefile holds. The lettered TEL-side exits are absent from *both* LTA
> sources, so no keying strategy available to us resolves that row. It stays a station-level
> warning, and §6 limitation 2 stands as written. The real win from GTFS is different and still
> large: it keys on `stop_code` (kills the name join, T21) and ships WGS84 (kills the SVY21
> reprojection, T19).

### I9 — OneMap needs a token, and the DataMall key is not it · **resolved, token supplied**

Plan §4 lists `sources/onemap.py` but nothing said where the credential comes from. Measured
17 Sep: `common/elastic/search` returns `200` with results *and* an `"Authentication token
missing"` error; `routingsvc/route` returns a hard **401**. The DataMall `AccountKey` does not
work on OneMap — different agency. A token was supplied and is in `.env` as `ONEMAP_TOKEN`
(JWT, expires **20 Sep 23:09 SGT** — after judging, but re-mint via `POST /api/auth/post/getToken`
if it lapses).

*How it is used:* geocoding for `/api/places/search`, and as the independent "plain foot route"
baseline in `verify_stepfree.py` (D11). **Walking legs still route on our own OSM graph** —
OneMap's walk router does not exclude `highway=steps` or know which lift is out, so D11's claim
cannot rest on it. This also fills §8's `[routing service]` placeholder: OneMap sees her typed
address at search time, and trip endpoints only in the offline verification script.

### I10 — GTFS and `TrainStationExit` are the same survey, not two sources · **claim correction**

Worth knowing before anyone writes "corroborated by two independent LTA datasets": of 585 exits
present in both, **572 (97.8%) sit within 0.5 m of each other** and the median separation is
exactly 0.00 m. They are one survey published twice.

The shapefile still earns its place, for *coverage* rather than corroboration: it carries exits
GTFS omits at 6 stations (Bugis 8 vs 4, Paya Lebar 6 vs 4, Telok Ayer 5 vs 3, Bukit Panjang,
Choa Chu Kang, Tai Seng). `exits.geojson` is therefore the **union** — 603 exits, 591 from GTFS
and 12 shapefile-only — with `source` on every feature.

### I11 — A bbox OSM extract is not one connected graph · **routing trap**

The corridor extract yields 198 components: Bedok (12,872 nodes) and Outram (5,873) as expected
from two bboxes, but also **112 fragments of two nodes**. Snapping a trip to its nearest node
lands on one of these — the nearest node to Outram Exit 4 is a 2-node stub, which made an
existing 795 m walk look like "no path".

`stepfree_graph.json` therefore ships a `components` map and `main_component_by_area`. The
planner must snap only to nodes in the area's main component. Verified after the fix: home →
Bedok Exit B is 1,351 m unrestricted with one staircase, **1,364 m step-free with none — a 13 m
detour** — and Outram Exit 4 → SGH is 795 m, 66% sheltered, step-free either way.

### I4 — The GTFS response field is `link`, not `Link` · **parser trap**

Guide v6.9 p.56 documents the attribute as `Link`. The live response returns lowercase `link`,
plus an **undocumented `timestamp`**. A parser written from the documentation returns `KeyError`.
Add to `PS2_INDEX.md` as a trap.

### I5 — "No poller" (D1) reads as contradicting the 20:00/07:00 checks (D3) · **wording**

D1 ends "No poller." D3 requires scheduled checks at 20:00 and 07:00, which is a scheduled
process. These are different things — D1 means no historical accumulation of outage data — but
the bare phrase invites a judge's question. Suggest D1 read "No historical poller; the scheduled
checks in D3 are unaffected."

### I6 — D6's offline tiles depend on an unmade decision · **PARKED** by the team

D6 caches map tiles for her route offline, "only as the tile provider's terms allow".
`tile.openstreetmap.org` **prohibits bulk downloading and offline caching** outright
(`PS2_README.md:L57`). So D6 is unbuildable until the `[tile provider]` placeholder in §8 is
filled with a provider whose terms permit offline caching. This also blocks the privacy
statement. **Decide this before any frontend map work.**

### I7 — "Nearest" barrier-free taxi stand is undefined · **small spec gap**

D2.3 offers "the nearest `TaxiStands` entry flagged `Bfa`". Nearest to what? She has no live
location (§8 commitment 2). It must mean nearest to the station she is at or heading to.

Verified this works: of 316 taxi stands, **293 are `Bfa=Yes`**, and the nearest to SGH is
`Outram Rd outside Outram Park MRT Station` at **478 m** — the right answer, directly outside her
interchange. Specify the anchor explicitly as "her current leg's station".

### I8 — §9's "five minutes" link expiry is now partly stale · **minor**

§9 says `GeospatialWholeIsland` links are "valid for five minutes only". Under v6.9 several
download links are documented at 15 minutes, and GTFS is confirmed at 15. Harmless (downloading
immediately is correct either way) but worth a footnote.

**None of these change the persona decision or D14's never-cut list.** I1, I3 and I6 change what
gets built; the rest are documentation fixes.

---

## 3. Stack

**Python 3.11 + FastAPI + SQLite.** Recommended for three reasons specific to this build:

1. **The data layer is geospatial and heavy.** GTFS parsing, SVY21→WGS84 reprojection, shapefile
   reading, OSM graph work and spatial joins. `pyproj`, `shapely` and `networkx` make this
   ordinary; in Node it is a fight. The checks in §2 of the decision record were already done in
   this stack.
2. **FastAPI generates the API record automatically.** `/openapi.json` and `/docs` come free and
   cannot drift from the code — `PS2_API_CONTRACT.md` is the human-readable companion, but the
   generated schema is the machine truth the frontend can codegen against.
3. **Web Push is a solved problem** via `pywebpush`.

SQLite over Postgres: the only persistent state is trips and push subscriptions (§8), both tiny,
and a single file is one less thing for a judge to install.

```
requirements: fastapi uvicorn[standard] httpx pydantic pyproj shapely networkx
              pywebpush apscheduler python-dotenv
```

---

## 4. Module layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, attribution middleware
│   ├── config.py            # env only — never a literal key (§8, rubric cap)
│   ├── api/
│   │   ├── trips.py         # plan, fetch, delete, offline bundle
│   │   ├── status.py        # live overlay for a trip
│   │   ├── alternatives.py  # D2 disruption options
│   │   ├── push.py          # subscribe, unsubscribe, test-send
│   │   └── scenario.py      # D1/D2 labelled injection toggle
│   ├── sources/             # one thin module per upstream, all cached
│   │   ├── datamall.py      # FacilitiesMaintenance, TrainServiceAlerts, PCDRealTime,
│   │   │                    #   BusArrival, TaxiStands, GTFSScheduleTrain
│   │   ├── weather.py       # data.gov.sg 2-hour nowcast
│   │   └── onemap.py        # geocoding
│   ├── services/
│   │   ├── planner.py       # step-free door-to-door plan
│   │   ├── lifts.py         # LiftDesc → exit matcher (I3)
│   │   ├── disruption.py    # TrainServiceAlerts → advice (D2, D13 rules)
│   │   ├── weather_policy.py# rain → sheltered walk (D9)
│   │   ├── crowd.py         # PCDRealTime → badge (D9)
│   │   └── timing.py        # headway + walk band → uncertainty (I1)
│   ├── scenario.py          # the ONLY place synthetic data enters
│   ├── jobs.py              # APScheduler: 20:00 and 07:00 (D3)
│   └── store.py             # SQLite: trips, push subs, retention (§8 commitment 1)
├── data/
│   ├── derived/             # build-pipeline outputs, committed
│   └── handchecked/         # EW5 + EW16 lift↔exit table (D7)
├── scripts/
│   ├── build_data.py        # the build-time pipeline (§5)
│   └── verify_stepfree.py   # D11 claim script
└── tests/
```

---

## 5. Build-time data pipeline

Run once, commit the outputs. Keeps request latency low and makes the demo independent of
upstream availability. `scripts/build_data.py` produces:

| Output | Built from | Purpose |
|---|---|---|
| `stations.json` | GTFS `stops.txt` | 217 station codes → name, coords, `parent_station`, platforms. **The canonical table** (I3). |
| `line_codes.json` | GTFS `routes.txt` + `PS2_INDEX.md` T1 | Maps every spelling — `BPL`/`BPLRT`/`BP`, `STL`/`SLRT`/`SK`, `PTL`/`PLRT`/`PG`, `CCL`/`CEL`, `EWL`/`CGL` — to one canonical id. |
| `exits.geojson` | `TrainStationExit` SHP, reprojected SVY21→WGS84 | 613 exits with `exit_code`, joined to `stop_code` via `stations.json`. |
| `headways.json` | GTFS `stop_times.txt` + `calendar.txt` | Per station, per direction, per hour, per day-type headway. Feeds `timing.py` (I1). |
| `ridetimes.json` | GTFS `stop_times.txt` | Fixed station-pair ride times. EW5→EW16 = 30.7 min. |
| `stepfree_graph.json` | OSM extract, her corridor | Foot graph with `highway=steps` excluded, `CoveredLinkWay` weighted, entrances tagged with `ref` + `wheelchair`. |
| `covered_ways.geojson` | `CoveredLinkWay` layer | Shelter weighting for D9. |

Cache the Overpass and DataMall pulls to disk; the brief forbids looping on the public Overpass
instance (`PS2_README.md:L57`).

---

## 6. Live sources and cache policy

Cache TTL matches each endpoint's real refresh rate, from the v6.8/v6.9 guides and confirmed live.
Every adapter must survive the upstream being down by serving stale-with-timestamp rather than
failing the request.

| Source | Endpoint | TTL | Verified 17 Sep |
|---|---|---|---|
| Lift outages | `v2/FacilitiesMaintenance` | 60 s | 200, 4 rows |
| Disruptions | `TrainServiceAlerts` | 60 s | 200, `value` is an **object** (trap T2), `Status=1`, `AffectedSegments=[]`, `Message` has 1 planned-works entry |
| Station crowding | `PCDRealTime?TrainLine=EWL` | 10 min | 200, 33 stations, levels `l`×32 `m`×1 |
| Bus arrivals | `v3/BusArrival?BusStopCode=` | 20 s | 200, `Load`/`Feature=WAB`/`Type`/`Monitored` all present |
| Taxi stands | `TaxiStands` | 24 h | 200, 316 stands, 293 `Bfa=Yes` |
| Rain nowcast | data.gov.sg `two-hr-forecast` | 5 min | no key needed |
| GTFS schedule | `GTFSScheduleTrain` | build-time only | 200, 2.3 MB, `link` is lowercase (I4) |

**Never** put the `AccountKey` in a URL or log line. It goes in the `AccountKey` header, read from
the environment (§8; the rubric caps the score for a committed credential).

---

## 7. The scenario layer — keeping synthetic data honest

D1 and D2 inject a lift outage and an EWL disruption. The rubric caps the score for *"mocked data
presented as live"* (`PS2_README.md:L290`), so the injection must be structurally impossible to
confuse with the real feed.

Three rules:

1. **One entry point.** `app/scenario.py` is the only module that can produce synthetic records.
   No service composes its own.
2. **Every affected payload carries provenance.** Any object that may be synthetic gets
   `"source": "live" | "simulated"` and, when simulated, `"simulated_note"` with the text the UI
   must display. The frontend renders the note — it is not optional styling.
3. **Mixed responses are normal and correct.** With the scenario on, her Outram Park outage is
   `simulated` while Stevens, Hougang, Clarke Quay and Jelapang remain `live` in the same array.
   That is D7 working: it shows the real path running beside the demo one.

Scenario state is a server-side flag toggled via `POST /api/scenario`, default **off**.

---

## 8. Scheduled checks and push

`jobs.py` (APScheduler, `Asia/Singapore`):

- **20:00 daily** — for every stored trip with an appointment in the next 36 h, re-run the lift
  and disruption check. On a change that affects her route, send a push.
- **07:00 daily** — same, for trips with an appointment today.
- **03:00 daily** — retention sweep: delete trips more than 24 h past their appointment
  (§8 commitment 1).

A push carries a title, one line of body, and the `trip_id` to deep-link into. `POST /api/push/test`
fires the same path on demand so judges see it without waiting (D4).

Per §6 limitation 1 and D3, an outage starting after the last check is not caught, and the app
must not imply otherwise. Wording: *"Checked 20:00. We'll check again at 07:00."*

---

## 9. Build order and status

Roughly two days of backend work with a half-day of margin. Stages are ordered by dependency,
not by day.

**Whoever implements a stage updates its row here in the same commit as the code.** Status is one
of `not started` · `in progress` · `done` · `cut`. A stage is only `done` when it runs and has been
exercised at least once against real data — not when the file exists. Put anything a later stage
needs to know in the Notes column.

| # | Stage | Delivers | Status | Notes |
|---|---|---|---|---|
| 1 | **Data pipeline** (§5) — `scripts/build_data.py` | `stations.json`, `line_codes.json`, `exits.geojson`, `ridetimes.json`, `headways.json`, `stepfree_graph.json`, `covered_ways.geojson` | `done` | Run 17 Sep against live feeds; outputs committed under `backend/data/derived/`. Reproduces both recorded figures exactly: EW5→EW16 is 30.67 min across all 698 trips (I1/T24), EW5 weekday headway 2.5 min at 08h / 5.0 off-peak (D8). **For later stages:** exits are a 603-row union, `source` per feature (I10); snap walking legs via `components` + `main_component_by_area` or you will land on one of 112 two-node stubs (I11); shelter is LTA `CoveredLinkWay` ∪ OSM tags. |
| 2 | **Sources + cache** (§6) | `app/sources/*` with recorded fixtures | `done` | All five adapters exercised live 17 Sep. Fixtures auto-record to `backend/data/fixtures/` on every successful fetch; `PS2_USE_FIXTURES=1` runs the whole backend with no network. Verified three degradation paths: fixtures-only, upstream-unreachable→fixture, and both auth failures. **T18 was re-measured and corrected** — a wrong key gives 401, a missing key gives the ambiguous 404. |
| 3 | **Planner** | Capability 1 — step-free Bedok → SGH, `leave_by`, `timing.py` | `not started` | Everything else decorates this. Timing range from headway + pace, never ride time (I1). |
| 4 | **Lift matcher + reroute** | Capability 2 | `not started` | The product's whole point. Re-measure the §3.2 join rate here and report the new figure. |
| 5 | **Scenario layer** (§7) | Labelled injection for D1/D2 | `not started` | Must exist before the demo path is built on top of it. |
| 6 | **Disruption alternatives** | Capability 3 | `not started` | Biggest single service. Three options per D2, shown against the original. |
| 7 | **Push + scheduler** | Capability 6 — 20:00 / 07:00 checks | `not started` | Include `POST /api/push/test` so judges need not wait. |
| 8 | **Offline bundle + crowd + weather** | Capabilities 4, 5, 7 | `not started` | Smallest and most cuttable. Offline tiles are parked (I6) — ship `tile_pack_url: null`. |
| 9 | **Claim scripts** | `verify_stepfree.py` (D11), `score_rules.py` (D13) | `not started` | These produce the write-up's numbers. Must run **before** submission, not after. |

D14's cut order if time runs short: taxi option → live bus checks → GTFS headways (but keep
`stations.json` — see D14 note).

---

## 10. Testing what the write-up claims

Two scripts produce numbers that go into `WRITEUP.md`. They are deliverables, not chores.

- **`scripts/verify_stepfree.py`** (D11) — plans her trip, asserts no walking leg uses an
  OSM-mapped staircase and every entrance used is `wheelchair=yes` or has an in-service lift,
  prints the result beside a plain foot route, and states that station interiors are not modelled.
- **`scripts/score_rules.py`** (D13) — runs the `LiftDesc` and delay-minute parsers over every held
  example (Annex C messages, the four captured `LiftDesc` rows, hand-copied `t.me/s/sgmrt`
  notices) and reports `n/N`. Ship the examples alongside.

Re-run the §3.2 join measurement after I3 lands and update the record with the new figure.
