# PS2 — Decision Record: which persona we build for

**Decision.** Build for **Mdm Lim**, the accessibility-constrained occasional traveller.
**Status.** Accepted, 17 Sep 2026. All three pre-commitment checks run against live APIs and passed.
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

**2 of 4 joined cleanly.**

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
- **Technical Execution — close, slight edge to Arjun on visible surface area.** He touches
  more modes and more endpoints. But the criterion reads "breadth *and judgement* of the
  data brought in," and her build wins on judgement: `SilverZone` (LTA's elderly-pedestrian
  zones, mentioned nowhere in the brief), `PedestrainOverheadbridge_UnderPass` used
  *inverted* as an obstacle map because an overhead bridge means stairs, and a free-text-to-
  geometry join harder than anything in Arjun's pipeline.
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

1. **No day-before lift warning.** `v2/FacilitiesMaintenance` carries no date fields, so we
   **detect rather than predict**. We check at plan time and re-check the morning she
   travels. She has not left home, so this still satisfies "proactive" as the brief defines
   it — but it costs her the advance notice her persona asks for.
2. **Exit join succeeds on 2 of 4 live rows.** Interchange stations with two operators
   (Stevens) fail; internal lifts (Jelapang) have no exit to join to. Failures degrade to
   station-level warnings, never to silent mis-routing.
3. **Bedok has no elevators mapped in OSM.** We rely on entrance `wheelchair` tags plus the
   LTA lift feed at her origin.
4. **Walking speed is assumed, not measured.** State the figure used.
5. **OSM entrance `wheelchair` coverage is 60%**, so absence of the tag is not evidence of
   inaccessibility. Treat unknown as unknown, not as unusable.
6. **The provided station GeoJSON is a 2017 planning snapshot** with no station codes and 13
   null names; we use it only for `GRND_LEVEL`. See trap T13 in `PS2_INDEX.md`.

---

## 7. Reproducing this

```bash
cp PS2/.env.example PS2/.env     # add your free AccountKey from datamall.lta.gov.sg
set -a; . PS2/.env; set +a
```

Then re-run the three commands in §2. Note that `GeospatialWholeIsland` returns a link
valid for five minutes only — download immediately, never cache the URL.

Captured evidence lives in `PS2/evidence/`. The credential lives in `PS2/.env`, which is
gitignored; `PS2/.env.example` lists the variable name only. The rubric caps the score for
a credential committed to the repository.
