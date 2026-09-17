# PS2 — Information Index

**Purpose.** A provenance map for Problem Statement 2 (Smart Commuter Companion). Every
fact below carries a pointer to where it came from, so a future session can jump straight
to the source instead of re-reading the pack. Nothing here is a design decision — this is
what the organisers said, plus what was measured directly from the provided files.

**Status:** exploration/brainstorming only. No implementation started.
**Compiled:** 2026-09-17, against repo commit `16526c0` (clean tree).
**Repo root:** `/home/zachary/Projects/nebulax_lta/NebulaX-Hackathon-ProblemStatement`
All paths below are relative to `PS2/` unless prefixed with `../`.

---

## 1. Source map — where everything lives

| # | Source | What it authoritatively contains | Notes for reading it |
|---|---|---|---|
| S1 | `PS2_README.md` (336 lines) | **The participant brief.** The most complete and most current statement of the problem. Includes the data architecture the PDF only summarises. | Plain markdown. **Primary source — prefer this over S2/S3 on any conflict.** |
| S2 | `references/Problem_Statement_2_Specification.pdf` (5 pages) | Same brief, formatted. Adds two sentences not in S1 (see §7.2). | Text-extractable. Cover-page-free; printed page ≡ PDF page. |
| S3 | `references/Problem_Statement_2_Specification.docx` | Same content as S2. Verified 98.6% character-identical after normalising whitespace; the only deltas are page headers/footers and smart quotes. | **Redundant with S2** — no need to open both. |
| S4 | `references/LTA_DataMall_API_User_Guide.pdf` (80 pages, v6.8, 21 Apr 2026) | **The API contract.** 30 endpoints, full request/response schemas, plus Annexes A–G. | Text-extractable *except* Annex C, whose sample JSON is **screenshots** (see §9). Byte-identical to `../LTA_DataMall_API_User_Guide.pdf` (md5 `c3971c56…`). |
| S4b | `references/LTA_DataMall_API_User_Guide_v6.9.pdf` (83 pages, v6.9, 3 Aug 2026) *(ours)* | **Newer than the pack.** Downloaded from DataMall on 17 Sep 2026 (md5 `fdcec562…`). Adds three GTFS endpoints: `GTFSScheduleTrain`, `GTFSRealTimeTrainServiceAlerts`, `GTFSRealtimeTrainTripUpdates`. `v2/FacilitiesMaintenance` is unchanged (still no date fields). | Page numbers shift from S4 after p.54, so S4 citations in this index do not apply to it. Several download links are documented as 15-minute expiry here, not 5. |
| S5 | `data/AmendmenttoMP2014RailStation.geojson` (498 KB) | 208 rail-station **footprint polygons**, Master Plan 2014 amendment. | Profiled in §4.1. Lower value than it looks. |
| S6 | `data/UsefulWebsites.txt` (106 lines) | Every external source named in the brief, with URL + purpose. | A condensed S1 §2.4. Section starts at lines 9, 28, 47, 56, 74, 94, 102. |
| S7 | `references/24hourWeatherForecast.json` | OpenAPI 3.0.3 spec for `GET /twenty-four-hr-forecast`. **Interface doc, not data.** | Schema in §4.4. |
| S8 | `references/4dayWeatherForecast.json` | OpenAPI 3.0.3 spec for `GET /four-day-outlook`. **Interface doc, not data.** | Schema in §4.4. |
| S9 | `submission/README.md` (119 lines) | **How to package and hand in.** Repo layout, README requirements, credential rules, claims rules, pre-submission checklist. | Logistics (where/when to submit) are still `TBC` — see §8. |
| S10 | `../README.md` | Repo-wide overview covering PS1/PS2/PS3 + DataMall quick start. | Contains three broken references — see §7.1. |
| S11 | `PS2_DECISION_RECORD.md` *(ours)* | **Why we build for Mdm Lim.** The three pre-commitment checks, their live-API results, the end-to-end join validation, the limitations to carry into `WRITEUP.md`, the build decisions D1–D14 (§7) and a draft privacy statement (§8). | Written 17 Sep 2026. Read this before re-litigating the persona choice. |
| S13 | `PS2_BACKEND_PLAN.md` *(ours)* | **How the backend gets built**, plus eight issues found in the decision record (I1–I8) — including that GTFS ride time is fixed, not a range. | Written 17 Sep 2026. Read §2 before acting on D7 or D8. |
| S14 | `PS2_API_CONTRACT.md` *(ours)* | **Every field the backend serves the frontend**, with worked JSON. FastAPI's `/openapi.json` is the machine truth. | Frontend can start against this before the backend exists. |
| S12 | `evidence/` *(ours)* | Timestamped captures backing claims in S11 — currently the `v2/FacilitiesMaintenance` snapshot. | Ship these: the brief requires captured data for any live-feed claim. |

**Not in the repo but named as required reading:** the DataMall portal's static master lists
(§4.3), and the SG MRT Updates Telegram archive (§4.6).

---

## 2. The brief in one screen

All line numbers are `PS2_README.md`.

| Thing | Where | One-line version |
|---|---|---|
| Mandate | L5 | Build a smart commuter companion **mobile web app** giving **proactive decision support** during **planned and unplanned** events, **tailored** to the commuter. |
| The four scored words | L7–L10 | *Proactive* = reaches them before the problem. *Decision support* = recommends an action, not a status. *Planned* events are first-class. *Tailored* = persona-specific. |
| Personas (pick one, say which) | L24–L39 | Rachel (fixed schedule, EWL Tampines→Raffles Pl, interrupt only when it matters); Arjun (multi-modal Punggol→one-north, cycle+bus, optimises comfort/crowding/shelter); Mdm Lim (accessibility, Bedok→SGH, step-free, large text, day-before lift warning). Own persona allowed if justified; "generic commuter" explicitly penalised. |
| Geospatial base | L41–L59, L252 | **OpenStreetMap is mandatory.** ODbL attribution required; public tile/Overpass servers must not be hammered. |
| Scope | L225–L233 | Web app, **mobile-first**. Judged in a **real phone browser**. Not an operator dashboard. |
| Mandatory capability 1 | L239–L250 | **Route planning** — door-to-door incl. walking legs, multi-modal, re-routes on live conditions **and says why**, timing with **visible uncertainty**. |
| Mandatory capability 2 | L252–L256 | **GIS on OpenStreetMap.** |
| Mandatory capability 3 | L258–L274 | **Visualisation** — route on map with affected vs unaffected portion distinguished; alternative shown *against* the original; crowding readable in one second; time/delay cost obvious. Accessibility is part of this. |
| Rubric | L276–L292 | Problem Fit **40%** · Technical Execution **35%** · Ease of Use **25%**. Each 0–5, weighted. |
| Caps | L288–L292 | Missing a mandatory capability → max level 3 on that part. Also capped: feature in pitch but not running; mocked data presented as live; unverifiable claim; committed credential; **OSM without attribution (a licence breach, not a style point)**. |
| Judging protocol | L292 | Judges follow your README on a clean machine → open on a real phone → you walk one real journey end to end → **you defend one claim per criterion**. "It's in the slides" is not evidence. |
| Beyond the brief | L294–L324 | Optional. AI must **earn its place** and be **shown to work with a measurement**. A reasoned decision *not* to use a model is also creditable. Open innovation needs stated assumptions, known limits, a path to production. |
| GCP credits | L314–L316 | "Expected to be available", details TBC. Tell organisers early if depending on a specific service. Anything a judge must pay for **does not count**. |
| Deliverables | L326–L336 | 1) runnable app 2) `WRITEUP.md` (persona, architecture, assumptions, limitations, how every number was derived) 3) demo of one real journey through one real disruption. |

---

## 3. Submission mechanics — `submission/README.md`

| Topic | Line | Content |
|---|---|---|
| What to hand in | L12–L21 | One repository: source + `README.md` + `WRITEUP.md` + linked demo recording. No zip of a build without source. |
| Suggested layout | L23–L34 | `README.md`, `WRITEUP.md`, `.env.example`, `src/`. Not enforced. |
| README must state | L36–L55 | Prerequisites · exact copy-pasteable install+run commands · configuration (env var names, where to get keys) · **what to click** and which journey to try first. Test by cloning into a fresh directory and following your own README literally. |
| Credentials | L57–L65 | Never commit a key/`AccountKey`/`.env`. Ship `.env.example` with names only. If a judge must register for a key, say so and link the page. |
| Claims | L67–L85 | No results file, no required numbers. But **an unbacked number is treated as unverified, not as evidence**. Judges must reproduce anything claimed **without paying**. |
| Quiet-feed allowance | L82–L85 | If a feature depends on a feed that may be quiet, say so and **ship the captured data that reproduces it**. Replay/injected data is fine **if labelled as such**. |
| Demo | L87–L94 | One real journey, one real disruption, chosen persona. ~5 min. **Record an actual phone screen** (or phone-sized window). Link it; don't commit the video. |
| Checklist | L96–L106 | 7 items — the last is "opened on a real phone browser, not devtools emulation". |
| Logistics | L108–L119 | **TBC by organisers:** where to submit, deadline+timezone, whether private repos are acceptable. |

---

## 4. Data inventory

### 4.1 `data/AmendmenttoMP2014RailStation.geojson` — measured, not assumed

Brief's description: `PS2_README.md:L65`. Profiled directly from the file:

| Property | Measured value |
|---|---|
| Collection name | `UP_G_MP14_RAIL_STN_PL` |
| Features | 208, **all `Polygon`** (station footprints, not points). 2 have multiple rings. |
| Property keys | `OBJECTID`, `GRND_LEVEL`, `TYPE`, `NAME`, `INC_CRC`, `FMEL_UPD_D`, `SHAPE_1.AREA`, `SHAPE_1.LEN` |
| `TYPE` | `MRT` 149 · `LRT` 46 · `CCL` 13 — **not line codes**, and `CCL` sits in the same field as the two mode values |
| `GRND_LEVEL` | `UNDERGROUND` 120 · `ABOVEGROUND` 88 — the one genuinely useful attribute for the accessibility persona |
| `NAME` | 175 unique across 208 features; **13 features have `NAME: null`**; includes placeholders (`THOMSON LINE`, `TSL Station`, `NSLE Station`) and a typo (`King Abert Park`) |
| `crs` | `null` **but coordinates are plain WGS84 lon/lat** — verified: bbox lon `103.63628…103.98947`, lat `1.25143…1.44955`, which is Singapore in EPSG:4326. Safe to treat as 4326. |
| `FMEL_UPD_D` | `20170509160126` for **every** feature — the whole layer is a **2017 vintage** planning snapshot |
| **No station codes at all** | So it cannot be joined to `TrainServiceAlerts.Stations`, `PCDRealTime.Station` or `PV/*Train` without a name-matching step against the DataMall master list (§4.3) |

**Practical read:** this is a Master Plan *amendment* layer, not an operational station list.
Use it for footprint geometry and the underground/aboveground flag; get the real network from
DataMall's `TrainStation` / `TrainStationExit` geospatial layers (§4.5) or OSM.

### 4.2 LTA DataMall — access basics

Source: `PS2_README.md:L70–L72`; S4 PDF p.8–9 (printed 7–8).

- Base: `https://datamall2.mytransport.sg/ltaodataservice/<endpoint>`
- Auth: free `AccountKey` header, registered at `https://datamall.lta.gov.sg`
- Default response format JSON; `accept: application/atom+xml` for XML (S4 p.8)
- **500 records per call**, page with `?$skip=500`, `?$skip=1000`, … (S4 p.9)
- Paging exceptions (S4 p.9, Table 1): **Bus Arrival**, **Train Service Alerts**, **Passenger Volume** (one record per request), **Taxi Stands**

### 4.3 The static master lists that are *not* in this repo

S4 p.32 (printed 31), note under Train Service Alerts, and Annexes A/B (p.56–57):

> This API relies on the static master list of **Train Station Codes**, **Train Line Codes** and
> **Train Shuttle Service Direction**, obtainable on the **DataMall Portal** — Train Station Codes
> and Train Line Codes are under the *Public Transport* section; Train Shuttle Service Direction
> is inside the Train Line Codes file. Annexes A/B also name `Train Station Codes and Chinese Names.csv`.

This is the canonical source for the "one canonical line table" the brief tells you to build
(`PS2_README.md:L134`). **It is a portal download, not an API, and it is not in this repo.**
Fetching it should be an early task.

### 4.4 Endpoint reference (S4 page numbers)

PDF page = printed page + 1 (one cover page). Endpoints marked ★ are the ones the brief
singles out.

| Endpoint | PDF p. | Key fields / notes |
|---|---|---|
| ★ `TrainServiceAlerts` | 31–32 | Full treatment in §5. |
| ★ `PCDRealTime?TrainLine=` | 46 | `Station`, `StartTime`, `EndTime`, `CrowdLevel ∈ {l,m,h,NA}`. 10 min. 11 line codes. |
| ★ `PCDForecast?TrainLine=` | 47 | `Date`, `Station`, `Start`, `CrowdLevel`. **30-min intervals, published once/24h** — this is the endpoint that makes *proactive* advice possible (`PS2_README.md:L144–L146`). |
| ★ `v3/BusArrival?BusStopCode=[&ServiceNo=]` | 14–20 | Per-bus `NextBus`/`NextBus2`/`NextBus3`. Fields: `EstimatedArrival` (ISO8601 +08:00), **`Monitored`** (0 = from operator schedule, 1 = from live bus position), `Latitude`/`Longitude` (`"0.0"` when `Monitored=0`), `Load ∈ {SEA, SDA, LSD}`, `Feature = WAB`, `Type ∈ {SD, DD, BD}`. 20 s refresh. |
| `BusServices[?ServiceNo=]` | 21–22 | `Category`, `OriginCode`, `DestinationCode`, `AM_Peak_Freq` / `AM_Offpeak_Freq` / `PM_Peak_Freq` / `PM_Offpeak_Freq` (minute ranges), `LoopDesc`. Peaks defined as 0630–0830 and 1700–1900. |
| `BusRoutes` | 21–22 | `StopSequence`, `BusStopCode`, `Distance` (km from origin), `WD/SAT/SUN_FirstBus`/`LastBus` (HHMM). |
| `BusStops[?BusStopCode=]` | 24 | `BusStopCode`, `RoadName`, `Description`, `Latitude`, `Longitude`. |
| ★ `PlannedBusRoutes` | 49 | Same shape as `BusRoutes` **plus `EffectiveDate`**. "Data to be released only ON/AFTER the Effective Date." The planned-event half of the brief. |
| ★ `v2/FacilitiesMaintenance` | 45 | `Line`, `StationCode`, `StationName`, `LiftID`, `LiftDesc` (e.g. `"Exit B Street level - Concourse"`). **No date fields** — see §6, trap T8. |
| `EstTravelTimes` | 34 | Expressway segments, `EstTime` in minutes. 5 min. |
| `v4/TrafficSpeedBands` | 40–41 | `LinkID`, `RoadName`, `RoadCategory` 1–6/8, `SpeedBand` 1–8 (10 km/h bands), `Min/MaximumSpeed`, `StartLon/Lat`, `EndLon/Lat`. 5 min. |
| `TrafficIncidents` | 39 | 13 `Type` values incl. `Weather`, `Diversion`, `Heavy Traffic`. Lat/Lon + free-text `Message`. 2 min. |
| `RoadWorks` / `RoadOpenings` | 36–37 | `EventID`, `StartDate`, `EndDate` (YYYY-MM-DD), `SvcDept`, `RoadName`, `Other`. **24 h refresh**, not ad hoc. |
| `VMS` | 42 | `EquipmentID`, Lat/Lon, `Message` (EMAS signboard text). 2 min. |
| `PubFloodAlerts` | 54–55 | CAP-style: `alertId`, `msgType ∈ {Alert, Cancel}`, `severity ∈ {Extreme, Severe, Moderate, Minor}`, `urgency`, `responseType`, `headline`, `description`, `instruction`, `areaDesc`, `circle` (`lat,long radius_km` — **radius is the broadcast radius, not the flood extent**), `expires` (auto 24 h). **3 min refresh.** |
| `Taxi-Availability` | 28 | Lat/Lon only, available taxis. 1 min. |
| `TaxiStands` | 29 | `TaxiCode`, Lat/Lon, **`Bfa` (barrier-free)**, `Ownership`, `Type ∈ {Stand, Stop}`, `Name`. **Monthly**, not 1 min. |
| `CarParkAvailabilityv2` | 33 | HDB/LTA/URA, `AvailableLots`, `LotType ∈ {C,H,Y}`, `Agency`. 1 min. |
| `BicycleParkingv2?Lat=&Long=[&Dist=]` | 43 | `RackType`, `RackCount`, **`ShelterIndicator`**. Default radius 0.5 km. **Monthly.** |
| `PV/Bus`, `PV/ODBus`, `PV/Train`, `PV/ODTrain` | 25–28 | Return a **5-minute-expiry download link** to a monthly ZIP. `Date=YYYYMM`, up to last 3 months, previous month generated **by the 10th**. CSV schemas in Annex A (p.56) and Annex B (p.57). |
| `GeospatialWholeIsland?ID=<layer>` | 44 | Returns a **5-minute-expiry link to a SHP zip**. Layer IDs in Annex E (p.77) — see §4.5. ID is **case-sensitive, spaces omitted**. |
| `Traffic-Imagesv2` | 38 | Live expressway camera stills, 5-min-expiry links. Camera-ID→location map in Annex G (p.79–80). *Not mentioned in the brief — possible open-innovation material.* |
| `FaultyTrafficLights` | 35 | `Type` 4 (blackout) / 13 (flashing yellow), `StartDate`, `EndDate` (empty unless scheduled). *Not in the brief.* |
| `TrafficFlow` | 48 | Quarterly hourly-average volumes, 0700–0900. Road categories in Annex F (p.78). |
| `EVChargingPoints?PostalCode=` / `EVCBatch` | 50–53 | EV charging availability. Irrelevant to this brief. |

Bus-app front-end advisement worth reading before building the bus leg — S4 p.18–20:
round arrival durations **down** to the minute and show `< 1 min` as `"Arr"`; suggested
`Load` colours green/amber/red; the `"No Est. Available"` vs `"Not In Operation"` decision
table; and loop services split by direction suffix (`225G/225W`, `243G/243W`, `410G/410W`).

### 4.5 Geospatial Whole Island layer IDs — Annex E, S4 p.77

34 layers. Verbatim IDs, case-sensitive. The ones the brief flags (`PS2_README.md:L153–L160`) in **bold**:

`ArrowMarking` · `Bollard` · **`BusStopLocation`** · `ControlBox` · `ConvexMirror` ·
**`CoveredLinkWay`** · **`CyclingPath`** · `DetectorLoop` · `ERPGantry` · **`Footpath`** ·
`GuardRail` · `KerbLine` · `LampPost` · `LaneMarking` · `ParkingStandardsZone` ·
`PassengerPickupBay` · **`PedestrainOverheadbridge_UnderPass`** *(LTA's spelling — use verbatim)* ·
`RailConstruction` · `Railing` · `RetainingWall` · `RoadCrossing` · `RoadHump` ·
`RoadSectionLine` · `SchoolZone` · `SilverZone` · `SpeedRegulatingStrip` · `StreetPaint` ·
**`TaxiStand`** · `TrafficLight` · `TrafficSign` · **`TrainStation`** · **`TrainStationExit`** ·
`VehicularBridge_Flyover_Underpass` · `WordMarking`

`SilverZone` and `SchoolZone` are not called out by the brief but are directly relevant to
the Mdm Lim persona and to school-term demand respectively.

### 4.6 Weather — data.gov.sg

Brief: `PS2_README.md:L170–L185`. No key required. Base `https://api-open.data.gov.sg/v2/real-time/api/`.

| Endpoint | In repo? | Shape |
|---|---|---|
| `two-hr-forecast` | ✗ no spec provided | Per-area nowcast (the ~47 named areas) |
| `twenty-four-hr-forecast` | ✓ S7 | See below |
| `four-day-outlook` | ✓ S8 | See below |
| `rainfall` | ✗ | Readings by weather station |
| air temp / humidity / wind / PM2.5 | ✗ | Same `/v2/real-time/api/` base |

Both provided specs are **OpenAPI 3.0.3, version 1.0.11**, single GET, optional
`date` (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`, SGT), optional `paginationToken`,
optional `x-api-key` header **for higher rate limits only**. Responses: `200/400/404/429`.

- **24-hour** (`data.records[]`): `general` block (`validPeriod{start,end,text}`, `temperature{low,high}`, `relativeHumidity{low,high}`, `forecast{code,text}`, `wind{speed{low,high},direction}`) plus `periods[]`, each with a `timePeriod` and **`regions`: only `west/east/central/north/south`**. There is also a top-level `area_metadata[]` giving named areas with `label_location{latitude,longitude}` — **but the forecast itself is only 5 coarse regions**, so per-area resolution needs the 2-hour nowcast.
- **4-day** (`data.records[].forecasts[]`): per-day `timestamp`, `temperature`, `relativeHumidity`, `forecast{summary,code,text}`, `day` (weekday name), `wind`.
- `forecast.text` is a **closed 23-value enum** in both — usable as a direct lookup key for walk/cycle penalties: `Fair`, `Fair (Day)`, `Fair (Night)`, `Fair and Warm`, `Partly Cloudy`, `Partly Cloudy (Day)`, `Partly Cloudy (Night)`, `Cloudy`, `Hazy`, `Slightly Hazy`, `Windy`, `Mist`, `Fog`, `Light Rain`, `Moderate Rain`, `Heavy Rain`, `Passing Showers`, `Light Showers`, `Showers`, `Heavy Showers`, `Thundery Showers`, `Heavy Thundery Showers`, `Heavy Thundery Showers with Gusty Winds`.

### 4.7 Other named sources

| Source | Where | Why it's named |
|---|---|---|
| **OneMap** `https://www.onemap.gov.sg/apidocs/` | `PS2_README.md:L193–L195`, S6 L47 | Free with registration. Geocoding, reverse geocoding, and a **routing API covering walk / drive / cycle / public transport**. Explicitly "worth looking at before you build your own routing engine". |
| **OSM bulk** | `PS2_README.md:L47`, S6 L56 | Geofabrik `https://download.geofabrik.de/asia/malaysia-singapore-brunei.html` |
| **Overpass** | `PS2_README.md:L48` | `https://overpass-api.de`, build at `https://overpass-turbo.eu`. **Cache what you fetch; do not query in a loop.** |
| **Routing engines** | `PS2_README.md:L49` | OSRM `https://project-osrm.org`, GraphHopper, Valhalla — all self-hostable, all consume OSM. |
| **Rendering** | `PS2_README.md:L50` | Leaflet `https://leafletjs.com`, MapLibre GL JS `https://maplibre.org`. |
| **SG MRT Updates Telegram** | `PS2_README.md:L162–L168`, S6 L74 | `https://t.me/s/sgmrt`. **Reference archive, not a feed.** The only practical way to assemble historical disruption-notice examples, because `AffectedSegments` is empty on a normal day. Two caveats: the same notice is reposted with small wording changes as it updates, and **the web view shows times but not dates**. |
| **data.gov.sg catalogue** | `PS2_README.md:L181–L185` | Search for: public holidays, school terms, HDB/population, historical ridership. |
| **NEA** | `PS2_README.md:L189` | Weather, air quality, heat — feeds the walking/cycling legs. |
| **SG Gov Design System** | `PS2_README.md:L190` | `https://designsystem.tech.gov.sg` |

---

## 5. `TrainServiceAlerts` — the endpoint the brief says to read first

Brief's summary: `PS2_README.md:L97–L120`. Contract: S4 p.31–32. **Worked examples: Annex C,
S4 p.58–73 — these are embedded screenshots, so text extraction silently loses them**; they
were read as images and are transcribed below.

### 5.1 Envelope

```jsonc
{
  "odata.metadata": "…/$metadata#TrainServicesAlerts",
  "value": {                      // ← an OBJECT, not an array
    "Status": 1,                  // 1 = normal / minor delays, 2 = disrupted / major delays
    "AffectedSegments": [ … ],    // list, one entry per affected segment
    "Message": [ … ]              // separate list: {Content, CreatedDate}, NEWEST FIRST
  }
}
```

`AffectedSegments[]` entry: `Line`, `Direction` (`"Both"` or a station name),
`Stations` (comma-separated codes), `FreePublicBus`, `FreeMRTShuttle`, `MRTShuttleDirection`.
During an actual disruption, `Status` / `Line` / `Direction` / `Stations` are mandatory (S4 p.32).

**The mitigation is in the feed** (`PS2_README.md:L120`): when LTA activates free bus boarding or
a shuttle, the endpoint says where. The work is not detecting the disruption — it is deciding
what *this* commuter should do and when to say it.

### 5.2 Documented `Line` enum (S4 p.30)

`EWL` (incl. Changi Extension — Expo, Changi Airport) · `NSL` · `NEL` ·
`CCL` (incl. Circle Line Extension — Bayfront, Marina Bay) · `DTL` · `TEL` ·
`BPL` · `STL` (Sengkang LRT) · `PTL` (Punggol LRT)

### 5.3 Free-shuttle encoding (S4 p.32)

`FreeMRTShuttle` normally lists affected stations, but when shuttles run along the four
predefined areas instead it carries a compound string:

`EW21|CC22,EW23,EW24|NS1,EW27;NS9,NS13,NS16,NS17|CC15;EW8|CC9,EW5,EW2;NS1|EW24,NS4|BP1`

- `|` delimits **interchange** station codes for one station
- `;` delimits **end of an area**
- The four predefined areas: (1) Buona Vista, Clementi, Jurong East, Boon Lay (2) Woodlands, Yishun, Ang Mo Kio, Bishan (3) Paya Lebar, Bedok, Tampines (4) Jurong East, Choa Chu Kang

`FreePublicBus` is either a station-code list or the literal island-wide string (see trap T4).

### 5.4 Lifecycle, transcribed from Annex C

**Scenario 1 — single line (NEL, Boon Keng↔Dhoby Ghaut towards HarbourFront), S4 p.58–64:**

| Step | PDF p. | `Status` | `AffectedSegments` | Notable |
|---|---|---|---|---|
| Normal day | 58 | `1` | `[]` | `Message: []` |
| Contingency activated | 59 | `2` | 1 entry, `Stations:"NE9,NE8,NE7,NE6"`, free-bus/shuttle fields `""` | `Message: []` — **segment appears before any message** |
| Message published | 60 | `2` | same | `Content: "1657hrs : NEL - Additional travelling time of 20 minutes…"` |
| Mitigation added | 60 | `2` | `FreePublicBus` + `FreeMRTShuttle` now populated, `MRTShuttleDirection:"HarbourFront"` | |
| Second message | 61 | `2` | same | Two `Message` entries, **1711hrs above 1657hrs** |
| Service recovers | 62 | **`1`** | **still 1 entry**, `Stations:""` but free-bus/shuttle **still populated** | `Status:1` ≠ nothing happening |
| Recovery message | 63 | `1` | same | `"1714hrs : NEL - Train service resumes. Free bus rides available…"` |
| Free rides cease | 64 | `1` | `[]` | back to the normal-day shape |

**Scenario 2 — three lines (NSL + EWL + DTL), S4 p.65–72:** one `AffectedSegments` entry
**per line**, all sharing the same four-area `FreeMRTShuttle` string; `FreePublicBus` flips to
`"Free bus service island-wide"` on every entry once island-wide free travel is activated.
On the way down, an entry can appear with **`Line:""`, `Direction:""`, `Stations:""`** while
free bus/shuttle remain live (S4 p.71). A single `Message.Content` can concatenate advisories
for several lines in one string (S4 p.70).

**Also seen (S4 p.73):** `Status:1`, `AffectedSegments:[]`, but a non-empty `Message`
containing `"Test : 1457hrs: SWL - Additional travelling time of 15 minutes on Seng Kang West
LRT (West Loop)."` — a test message, referencing a line code (`SWL`) that is **not in the
documented `Line` enum**.

---

## 6. Traps — consolidated, with provenance

| # | Trap | Source |
|---|---|---|
| T1 | **Line codes differ between endpoints.** Sengkang LRT `STL`/`SLRT`; Punggol LRT `PTL`/`PLRT`; Circle Line Extension folded into `CCL` in alerts but a separate `CEL` in crowd density; Changi Extension folded into `EWL` but a separate `CGL`. **And a third Bukit Panjang spelling found live: `v2/FacilitiesMaintenance` returns `BPLRT`, not the documented `BPL`** — this case is in neither the brief's table nor the guide's. Build one canonical line table and map everything through it. | `PS2_README.md:L122–L134`; S4 p.30 vs p.46; `BPLRT` observed live 17 Sep 2026, see S11 §4 |
| T2 | **`value` is an object, not an array,** on `TrainServiceAlerts` — unlike most DataMall endpoints. Parsers written generically will break. | S4 Annex C screenshots |
| T3 | **`Status:1` does not mean "all clear".** On recovery the segment persists with `Stations:""` while free bus/shuttle stay active, and `Message` keeps flowing. Test emptiness of `AffectedSegments`, don't switch on `Status`. | S4 p.62, p.71 |
| T4 | **`FreePublicBus` island-wide string is inconsistent.** Spec table says `Free bus service island wide`; every sample renders `Free bus service island-wide` (hyphen). Match loosely. | S4 p.31 vs p.69/71 |
| T5 | **Undocumented line codes appear in `Message` text** (e.g. `SWL`), and messages may be test broadcasts prefixed `"Test :"`. | S4 p.73 |
| T6 | **`Message` is ordered newest-first** and one `Content` can bundle several lines' advisories. Times are `hhmm hrs` inside the text; the machine-readable timestamp is `CreatedDate`. | S4 p.61, p.63, p.70 |
| T7 | **The feeds are quiet most days.** Don't build a demo that needs a live disruption. Replay/injected data is fine **if labelled**. Everything except `AffectedSegments` — including the `Message` stream of bus diversions — is populated daily. | `PS2_README.md:L217` |
| T8 | **`v2/FacilitiesMaintenance` has no date fields** — it's a snapshot of what's under maintenance *now*. Mdm Lim's "warn me the day before" therefore requires polling and storing your own history; it cannot be read off the endpoint. | S4 p.45 vs `PS2_README.md:L38` |
| T9 | **Crowding is three different signals, not one.** Station real-time (10 min, per station) · station forecast (30-min buckets, daily publish) · bus `Load` (per arriving bus, not per stop). `PV/*` gives the historical baseline needed to tell an unusual crowd from a Tuesday. | `PS2_README.md:L136–L151` |
| T10 | **`Monitored=0` means the bus ETA is a timetable, not a position** — and `Latitude`/`Longitude` come back as `"0.0"`. This is the free, honest input for the rubric's "uncertainty made visible" requirement. | S4 p.13, p.16 |
| T11 | **Several endpoints return a 5-minute-expiry S3 link, not data**: `PV/*`, `GeospatialWholeIsland`, `Traffic-Imagesv2`, `TrafficFlow`, `EVCBatch`. Download immediately; never cache the URL. | S4 p.24–28, 37, 44, 48, 53 |
| T12 | **`GeospatialWholeIsland` returns SHP zips**, not GeoJSON, and the `ID` is case-sensitive with spaces omitted. | S4 p.44, Annex E |
| T13 | **The station GeoJSON has no station codes, 13 null names, placeholder names and a 2017 vintage** — it will not join to any DataMall feed as-is. | Measured, §4.1 |
| T14 | **24-hour weather forecast is only 5 regions**, despite shipping per-area lat/lon metadata. Per-area resolution needs the 2-hour nowcast, whose spec is *not* in this repo. | S7 schema |
| T15 | **Underground = no signal.** Decide explicitly what the app does between stations (cache / degrade / say it's stale) **and state the choice in the write-up** — it is a scored decision, not an edge case. | `PS2_README.md:L215` |
| T16 | **Loop bus services carry direction suffixes** (`225G`/`225W`, `243G`/`243W`, `410G`/`410W`) and must be displayed individually. | S4 p.20 |
| T17 | **Bus Arrival returns nothing at all — not even empty tags — outside operating hours or during maintenance.** Absence is not an error. | S4 p.14, p.18 |
| T18 | **DataMall masks unauthorized as `404 "The requested API was not found"`**, not `401`. A missing or wrong `AccountKey` looks exactly like a wrong URL. Suspect the key first. | Observed 17 Sep 2026 across three endpoints, see S11 §4 |
| T19 | **`GeospatialWholeIsland` layers ship in SVY21, not WGS84.** `TrainStationExit`'s bundled `.prj` is Singapore's national projected grid — reproject before overlaying on an OSM base. `pyproj` reads the `.prj` directly. | Verified 17 Sep 2026, see S11 §4 |
| T20 | **`v2/FacilitiesMaintenance.LiftDesc` has no fixed format.** ALL CAPS and Title Case both occur, some rows carry a `(TEL)`-style line prefix, and internal lifts carry no exit reference at all. `LiftID` varies too (`B3L02`, `B1 L01` with a space, empty string). Parse defensively. | Observed live, see S11 §2 |
| T21 | **`TrainStationExit` carries no station code** — only `stn_name` and `exit_code` — so joining it to `FacilitiesMaintenance` runs through the station *name*. Suffixes are clean (`MRT STATION` ×541, `LRT STATION` ×72). | Measured from the Jul2026 layer, see S11 §2 |
| T22 | **`GTFSScheduleTrain` returns lowercase `link`, not the documented `Link`** — plus an undocumented `timestamp`. A parser written from guide v6.9 p.56 raises `KeyError`. | Verified live 17 Sep 2026; see `PS2_BACKEND_PLAN.md` I4 |
| T23 | **GTFS `stops.txt` is the canonical station table the brief asks you to build** — 217 `stop_code` values with names and coordinates — and **`parent_station` unifies 28 interchanges across line codes** (`EW16 ← {EW16, NE3, TE17}`, `DT10 ← {DT10, TE11}`). Prefer it over name-matching `TrainStationExit`. | Measured from the live feed 17 Sep 2026; see `PS2_BACKEND_PLAN.md` I3 |
| T24 | **GTFS train ride times are fixed, not ranges.** All 698 EW5→EW16 trips are 30.7 min exactly. Timing uncertainty must come from headway (2.5 min peak / 5.0 off-peak) and walking pace. | Measured 17 Sep 2026; see `PS2_BACKEND_PLAN.md` I1 |

---

## 7. Gaps and discrepancies found in the pack

### 7.1 Files referenced but absent

`../README.md` points at three PS2 files that are **not in the repository** (confirmed against `git ls-files PS2`):

| Referenced as | Status |
|---|---|
| `PS2/references/PS2_scoring_rubric.md` — "the full rubric: every dimension broken into sub-axes with a description at each of the five levels, plus caps and judging protocol" | **Missing.** This matters: it is the only place the per-level descriptors would live. The rubric in `PS2_README.md:L276–L292` is the criterion/weight table only. |
| `PS2/generate_ps2_docx.py` | **Missing.** |
| `PS2/generate_ps2_pdf.py` | **Missing.** |

Also missing but implied: the DataMall portal master lists (§4.3) and a spec for the 2-hour nowcast.

### 7.2 Content differences between the brief (S1) and the spec PDF (S2)

S2 is a condensed restatement, but carries **two sentences with no S1 equivalent** — both in §2.5:

- *"Data obtained in breach of [a site's terms] **caps the data dimension at 1** and is referred to the organisers before scoring continues."* (S2 p.2) — the only reference anywhere in the pack to a scored "data dimension", which points back at the missing rubric file.
- S2 §2.4 names the crowding endpoints as `PlatformCrowdDensityRealTime` / `PlatformCrowdDensityForecast`. **The real URL paths are `PCDRealTime` / `PCDForecast`** — S1 L149–L151 explains why (renamed Platform→Station, paths unchanged), S4 p.46–47 confirms.

Conversely S1 has substantial material S2 omits entirely: the full endpoint table, the
`TrainServiceAlerts` field-by-field schema, the line-code table, the three crowding signals,
the Annex E layer picks, the Telegram archive rationale, and all of §2.5's bullet-level rules.

**Branding inconsistency:** S2/S3 page headers read **"LTA HACKATHON 2027"** while `../README.md`
and the repo title say **"NebulaX 2026"**. Cosmetic, but worth not copying into a submission.

### 7.3 Refresh rates: brief vs API guide

`PS2_README.md:L74–L95` compresses refresh rates; S4 is authoritative. Differences worth knowing:

| Endpoint | Brief says | Guide says (S4) |
|---|---|---|
| `TaxiStands` | 1 min (grouped with `Taxi-Availability`) | **Monthly** (p.29) |
| `PubFloodAlerts` | Ad hoc | **3 minutes** (p.53) |
| `RoadWorks` / `RoadOpenings` | Ad hoc | **24 hours** (p.35–36) |
| `BicycleParkingv2` | Ad hoc | **Monthly** (p.42) |
| `v3/BusArrival` | Real-time | **20 seconds** (p.13) |
| `PV/*` | Monthly | By the **10th** of each month for the previous month; **only last 3 months** retrievable (p.24–27) |

---

## 8. Open questions for the organisers

Things the pack explicitly leaves TBC, or that we cannot resolve from the documents:

1. **Submission logistics** — where to submit, deadline + timezone, whether private repos are acceptable (`submission/README.md:L108–L119`).
2. **The scoring rubric file** — is `PS2_scoring_rubric.md` meant to be released? It changes how much detail the write-up needs (§7.1). The "caps the data dimension at 1" line (§7.2) implies sub-dimensions we cannot currently see.
3. **GCP credits** — confirm availability, and flag early if we plan to depend on a named service (`PS2_README.md:L314–L316`).
4. **Telegram archive use** — S1 calls `t.me/s/sgmrt` reference material and simultaneously says scraping is generally unacceptable (`PS2_README.md:L162–L168` vs `L207`). If we want to pull a corpus of notices programmatically rather than by hand, `PS2_README.md:L207` says to **ask before building on it**. Worth asking explicitly.
5. **Any non-obvious data source** we bring in — the brief repeats "ask rather than guess" three times (L211, L219, L335–L336).

---

## 9. Reproducing the extractions

The two PDFs are not directly greppable from the shell here — `pdftotext`, `pypdf` and
`pymupdf` are all absent from system Python, and `pip install` is blocked by PEP 668.
What worked:

```bash
SP=<scratchpad>
python3 -m venv "$SP/venv"
"$SP/venv/bin/pip" install pypdf pillow
```

- **Text**: `PdfReader(path).pages[i].extract_text()` → both PDFs extract cleanly.
- **Annex C is the exception.** Pages 58–73 of S4 hold their sample JSON as **embedded PNG screenshots**; `extract_text()` returns only the captions, so a text-only read silently misses the entire worked example. Extract with `page.images` (requires `pillow`) and read the PNGs as images. Anything in §5.4 above came from that path.
- **`.docx`**: `unzip` it and strip tags from `word/document.xml`.
- **Page numbering for S4**: PDF page = printed page + 1 (one unnumbered cover). All S4 citations in this index are **PDF page numbers**.

---

## 10. Quick pointers

| I need… | Go to |
|---|---|
| What we're being asked to build | `PS2_README.md:L1–L12`, §2 above |
| Which persona, and what they need | `PS2_README.md:L24–L39` |
| What is mandatory | `PS2_README.md:L235–L274` (three capabilities) |
| How it's scored and what caps the score | `PS2_README.md:L276–L292`, §2 above |
| What we must hand in and how | `submission/README.md`, §3 above |
| Which endpoint gives me X | §4.4 above → S4 page |
| The disruption feed's real shape | §5 above (transcribed from screenshots) |
| Things that will bite us | §6 above |
| What's missing / inconsistent in the pack | §7 above |
| What to ask the organisers | §8 above |
| Why we chose Mdm Lim, and the evidence | `PS2_DECISION_RECORD.md` |
| What we decided to build, and what gets cut | `PS2_DECISION_RECORD.md` §7 |
| What the privacy statement says | `PS2_DECISION_RECORD.md` §8 |
| How the backend is built, and what's wrong with the record | `PS2_BACKEND_PLAN.md` |
| What the API serves the frontend | `PS2_API_CONTRACT.md` |
