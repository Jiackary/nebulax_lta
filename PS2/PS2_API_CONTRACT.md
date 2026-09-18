# PS2 — Backend API Contract

**What this is.** Every field the backend serves, and what the screen does with it. Written so
frontend work can start before the backend exists.

**Companions:** [`PS2_BACKEND_PLAN.md`](PS2_BACKEND_PLAN.md) for how it is built,
[`PS2_DECISION_RECORD.md`](PS2_DECISION_RECORD.md) for why. Decision references are `D1`–`D14`.

**Machine truth.** FastAPI serves `/openapi.json` and `/docs`. Where this document and the
generated schema disagree, the schema wins and this file is the bug.

**Status: the backend is built and serving all of this** (`PS2_BACKEND_PLAN.md` §9, stages 1–9
`done`). §10 below lists every way the built API differs from this document as first written —
read it before wiring a screen.

**Base URL** `/api` · JSON throughout · times ISO 8601 with `+08:00` · coordinates WGS84
`[lon, lat]` (GeoJSON order).

---

## 1. Design rules

Four rules the whole contract follows. They exist because the client is a phone held in one hand
by someone who walks slowly, and because the rubric caps specific failures.

1. **The frontend renders; it does not compute.** Every value that appears on screen arrives
   ready to display. No client-side crowd-level thresholds, no duration maths, no string
   assembly from codes. If the screen shows a sentence, the backend sent that sentence.
2. **Provenance is mandatory, not decorative.** Anything that may be synthetic carries
   `source` and, when simulated, `simulated_note`. The UI **must** display the note. The rubric
   caps mocked data presented as live (`PS2_README.md:L290`).
3. **State is never colour alone.** Every state field ships a `severity` token *and* a `label`.
   Accessibility is scored inside Ease of Use, and the brief forbids relying on colour alone
   (`PS2_README.md:L272`).
4. **Staleness is explicit.** Every live-derived block carries `observed_at` and `stale`. Offline,
   the UI says "plan as of HH:MM" rather than presenting old data as current (D6).

### Shared enums

| Field | Values | Frontend meaning |
|---|---|---|
| `source` | `live` · `simulated` | `simulated` → render `simulated_note` visibly |
| `severity` | `ok` · `info` · `warn` · `critical` | Badge/banner tone. Always paired with `label`. |
| `mode` | `walk` · `rail` · `bus` · `taxi` | Leg icon and step wording |
| `crowd_level` | `low` · `moderate` · `high` · `unknown` | Mapped from raw `l`/`m`/`h`/`NA` by the backend |
| `step_free` | `yes` · `no` · `unknown` | `unknown` is not `no` — §6 limitation 5 |

### Error shape

```json
{ "error": { "code": "TRIP_NOT_FOUND", "message": "That trip no longer exists.",
             "retryable": false } }
```

`message` is shown to the user as-is. Codes: `TRIP_NOT_FOUND`, `UPSTREAM_UNAVAILABLE`,
`INVALID_REQUEST`, `PUSH_SUBSCRIPTION_INVALID`.

This is the shape on the wire. FastAPI would normally wrap errors in `detail`; exception
handlers unwrap it, so `error` is always top-level — including for validation failures.

---

## 2. Endpoint index

| Method | Path | Serves |
|---|---|---|
| `GET` | `/api/health` | Liveness + which upstreams are reachable |
| `GET` | `/api/attribution` | OSM/tile/LTA attribution strings |
| `GET` | `/api/places/search?q=` | Address autocomplete for her home |
| `POST` | `/api/trips` | Plan and store a trip |
| `GET` | `/api/trips/{id}` | The plan |
| `GET` | `/api/trips/{id}/status` | Live overlay: lifts, disruption, crowd, weather |
| `GET` | `/api/trips/{id}/alternatives` | D2 options during a disruption |
| `GET` | `/api/trips/{id}/offline` | Everything needed with no signal |
| `DELETE` | `/api/trips/{id}` | Delete trip and server copy |
| `POST` | `/api/push/subscribe` | Register for warnings |
| `DELETE` | `/api/push/subscribe` | Unregister and delete stored trips |
| `POST` | `/api/push/test` | Fire a warning now (judge-facing, D4) |
| `GET`/`POST` | `/api/scenario` | Read/toggle the labelled demo scenario (D1, D2) |
| `GET` | `/api/push/key` | VAPID **public** key, needed before subscribing |
| `GET` | `/api/destinations` | The one destination this app plans to |

---

## 3. Planning a trip

### `POST /api/trips`

```json
{ "origin": { "label": "Blk 208B New Upper Changi Road", "coord": [103.930570, 1.324782] },
  "destination_id": "SGH",
  "appointment_at": "2026-09-19T10:30:00+08:00",
  "preferences": { "walking_pace": "slow", "avoid_stairs": true, "prefer_sheltered": true } }
```

`walking_pace` ∈ `slow` (0.7 m/s) · `normal` (1.2 m/s). The figure used is echoed in
`timing.basis` — §6 limitation 4 requires stating it.

### `GET /api/trips/{id}` → `TripPlan`

```json
{
  "trip_id": "t_9fK2",
  "appointment_at": "2026-09-19T10:30:00+08:00",
  "summary": {
    "leave_by": "2026-09-19T09:24:00+08:00",
    "leave_by_label": "Leave at 09:24",
    "arrival_window": ["2026-09-19T10:05:00+08:00", "2026-09-19T10:15:00+08:00"],
    "arrival_label": "arrive 10:05–10:15",
    "appointment_label": "appointment 10:30",
    "buffer_min": 15,
    "duration_min": 46,
    "range_min": [41, 51],
    "timing_basis": "Train ride 31 min, fixed by the timetable. Wait 0–5 min at this hour. Walking at 0.7 m/s.",
    "step_free": "yes",
    "sheltered_pct": 78
  },
  "legs": [ "…see §3.1…" ],
  "map": {
    "bbox": [103.8330, 1.2780, 103.9330, 1.3280],
    "geometry": { "type": "FeatureCollection", "features": [] }
  },
  "attribution": ["© OpenStreetMap contributors", "Contains information from LTA DataMall"],
  "observed_at": "2026-09-17T22:41:00+08:00"
}
```

**`leave_by_label` is the one big number on the screen.** She has an appointment and will not
improvise on a platform, so "46 minutes" is not useful to her — "Leave at 09:24" is. Render
`leave_by_label` large, with `arrival_label` and `appointment_label` as one quiet line beneath.

**That quiet line is how the brief's uncertainty requirement is met** (`PS2_README.md:L248`,
inside mandatory capability 3.2.1). The range is not removed, only demoted: `arrival_window` is
a window, not a point, and it must stay visible. A bare point estimate risks the level-3 cap on
route planning.

**How `leave_by` is derived:** `appointment − buffer_min − range_min[1]`. The late end of the
window lands on the buffer, so following the advice means arriving in time even on a slow day.
Here: `10:30 − 15 − 51 = 09:24`, giving a window of `10:05–10:15`.

**Where the range comes from** (issue I1): GTFS ride time is a **fixed** 30.7 min for EW5→EW16
across all 698 trips — zero variation. The spread is entirely wait time (0–5 min at this hour)
plus walking pace. `timing_basis` says so in words; show it on the detail view rather than the
summary.

`sheltered_pct` is the share of walking distance under `CoveredLinkWay`. Shown only when rain is
forecast (D9).

### 3.1 `Leg`

```json
{
  "leg_id": "l2",
  "mode": "rail",
  "from": { "name": "Bedok", "station_code": "EW5", "coord": [103.9302, 1.3240] },
  "to":   { "name": "Outram Park", "station_code": "EW16", "coord": [103.8391, 1.2814] },
  "line": { "code": "EWL", "name": "East-West Line", "colour": "#189E4A" },
  "duration_min": 31,
  "headway_min": 5,
  "instruction": "Take the East-West Line towards Tuas Link. 11 stops.",
  "step_free": "yes",
  "access": {
    "board_at": { "exit_code": "Exit B", "lift_id": "B1L01", "status": "in_service" },
    "alight_at": { "exit_code": "Exit 4", "lift_id": "B2L03", "status": "in_service" }
  },
  "geometry": { "type": "LineString", "coordinates": [] }
}
```

For `mode: "walk"` the leg drops `line`/`access` and adds:

```json
{ "distance_m": 340, "covered_m": 265,
  "instruction": "Walk 340 m to Bedok MRT Exit B. Sheltered most of the way.",
  "surface_warnings": [] }
```

---

## 4. Live status

### `GET /api/trips/{id}/status` → `RouteStatus`

The screen's banner and badges.

**Fetched on demand, not polled.** Call it when she opens the app or the trip, and when she pulls
to refresh. There is no background recompute: warnings reach her by push from the 20:00 and 07:00
checks (D3, D4), which is the whole point of those checks. Because the data is therefore as old as
her last fetch, `observed_at` and `checks.label` are not optional — they are how the screen stays
honest about its own age.

```json
{
  "trip_id": "t_9fK2",
  "overall": {
    "severity": "warn",
    "headline": "A lift is out at Outram Park.",
    "detail": "Exit 4's lift is under maintenance. We've moved you to Exit 6, which adds 3 minutes.",
    "action": { "kind": "view_reroute", "label": "See the new route" }
  },
  "lift_alerts": [
    { "station_code": "EW16", "station_name": "Outram Park",
      "exit_code": "Exit 4", "lift_id": "B2L03",
      "lift_desc": "Exit 4 Street level - Concourse",
      "affects_route": true, "severity": "warn",
      "label": "Lift out of service",
      "resolution": "matched_exit",
      "source": "simulated",
      "simulated_note": "Simulated for this demo. Real outages elsewhere are shown live.",
      "observed_at": "2026-09-17T22:40:00+08:00" }
  ],
  "disruption": null,
  "crowd": [
    { "station_code": "EW5", "station_name": "Bedok", "level": "low",
      "label": "Not crowded", "severity": "ok",
      "observed_at": "2026-09-17T22:30:00+08:00", "source": "live" }
  ],
  "weather": {
    "rain_expected": false, "area": "Bedok",
    "label": "No rain forecast in the next 2 hours",
    "severity": "ok", "affects_route": false, "source": "live"
  },
  "checks": { "last_checked_at": "2026-09-17T22:40:00+08:00",
              "next_check_at": "2026-09-18T07:00:00+08:00",
              "label": "Checked 22:40. We'll check again at 07:00." },
  "stale": false
}
```

Notes for the frontend:

- **`overall` is the only thing that must be readable in one second.** Everything else is detail
  she opens if she wants it.
- **`lift_alerts[].affects_route`** decides prominence. Outages elsewhere still appear in the
  station list but never in the banner.
- **`resolution`** ∈ `matched_exit` · `station_only` · `unmatched`. `station_only` is the
  documented degradation when `LiftDesc` cannot be tied to an exit — §6 limitation 2. The UI must
  then say "a lift at this station" rather than naming an exit it does not know.
- **Mixed `source` values in one array are expected** (D7, §7 of the plan).
- **`checks.label` is pre-written** because the honest wording matters: we detect, we do not
  predict (§6 limitation 1).

---

## 5. Disruption alternatives

### `GET /api/trips/{id}/alternatives` → `Alternatives`

Populated only when `status.disruption` is non-null. Implements D2's three options, always shown
against the original so she can judge the trade-off (`PS2_README.md:L264`).

```json
{
  "disruption": {
    "line": "EWL", "severity": "critical",
    "headline": "East-West Line delays towards Tuas Link",
    "detail": "Additional travelling time of about 20 minutes between Bedok and Outram Park.",
    "delay_min": 20,
    "delay_basis": "Parsed from LTA's advisory: \"additional travelling time of 20 minutes\".",
    "affected_stations": ["EW5", "EW6", "EW7"],
    "free_bus_available": true,
    "source": "simulated",
    "simulated_note": "Replay of a real LTA advisory format. Labelled for this demo.",
    "observed_at": "2026-09-19T08:12:00+08:00"
  },
  "original": { "label": "Your usual route", "duration_min": 46,
                "arrival_at": "2026-09-19T10:00:00+08:00", "viable": true,
                "note": "Now about 20 minutes slower." },
  "options": [
    { "option_id": "leave_later", "rank": 1, "mode": "rail",
      "label": "Leave 25 minutes later",
      "why": "The delay fits inside your buffer. You keep your usual step-free route.",
      "delta_min": 0, "arrival_at": "2026-09-19T10:21:00+08:00",
      "step_free": "yes", "severity": "ok", "legs": [] },

    { "option_id": "bus_wab", "rank": 2, "mode": "bus",
      "label": "Wheelchair-accessible bus 12 from Bedok",
      "why": "Next bus has seats and a wheelchair ramp. Avoids the delayed stretch.",
      "delta_min": 14, "arrival_at": "2026-09-19T10:14:00+08:00",
      "step_free": "yes", "severity": "info",
      "bus": { "service_no": "12", "load": "SEA", "load_label": "Seats available",
               "wheelchair_accessible": true, "vehicle_type": "DD",
               "eta_min": 4, "eta_is_scheduled": false },
      "legs": [] },

    { "option_id": "taxi_bfa", "rank": 3, "mode": "taxi",
      "label": "Barrier-free taxi from Outram Rd",
      "why": "Nearest barrier-free stand to the hospital, 478 m from your interchange.",
      "delta_min": -6, "arrival_at": "2026-09-19T09:54:00+08:00",
      "step_free": "yes", "severity": "info",
      "taxi_stand": { "name": "Outram Rd outside Outram Park MRT Station",
                      "barrier_free": true, "distance_m": 478,
                      "anchor": "EW16", "fare_estimate": null },
      "legs": [] }
  ],
  "not_offered": [
    { "label": "Free bridging bus",
      "why_not": "These run crowded with standing only, which isn't a good trade for you." }
  ]
}
```

Notes:

- **`delta_min` is signed and relative to the original.** Negative is faster. Show the sign.
- **`eta_is_scheduled`** maps LTA's `Monitored` field: `true` means the time came from a
  timetable, not a tracked bus. Show it as "scheduled" rather than implying live tracking.
- **`fare_estimate` is always `null`** — D2.3 declines to claim a number we cannot verify.
  Do not render a placeholder.
- **`not_offered` is deliberate.** D2 declines free bridging buses and shuttles for this persona;
  surfacing the reason is better product *and* pre-empts a judge's question.
- `options` arrives pre-sorted by `rank`. Do not re-sort.

---

## 6. Offline

### `GET /api/trips/{id}/offline` → `OfflineBundle`

One request, cached by the service worker. Everything the underground leg needs (D6).

```json
{
  "trip_id": "t_9fK2",
  "generated_at": "2026-09-19T09:05:00+08:00",
  "plan": { "…full TripPlan…": null },
  "status_snapshot": { "…RouteStatus at generation time…": null },
  "steps_plain": [
    "Walk 340 m to Bedok MRT Exit B. Sheltered most of the way.",
    "Take the East-West Line towards Tuas Link. 11 stops, about 31 minutes.",
    "Leave by Exit 6 and take the lift to street level.",
    "Walk 210 m to Singapore General Hospital, Block 3."
  ],
  "tiles": { "style_url": null, "tile_pack_url": "/api/trips/t_9fK2/tiles.pmtiles",
             "attribution": "© OpenStreetMap contributors", "zoom_range": [13, 17] },
  "offline_notice": "No signal: plan as of 09:05. Times may have changed."
}
```

- **`steps_plain` is the offline screen.** Large text, no map needed, readable at a glance.
- **`offline_notice` must be shown whenever the bundle is used without a network.** It is the
  no-signal choice the brief requires us to state (`PS2_README.md:L215`).
- **`tiles` is blocked on an open decision** — see issue I6. `tile.openstreetmap.org` prohibits
  offline caching, so `tile_pack_url` stays `null` until a permitting provider is chosen. Build
  the UI to degrade to `steps_plain` when it is `null`; that path must work regardless.

---

## 7. Push

### `POST /api/push/subscribe`

```json
{ "subscription": { "endpoint": "https://fcm.googleapis.com/…",
                    "keys": { "p256dh": "…", "auth": "…" } },
  "trip_ids": ["t_9fK2"] }
```

→ `{ "subscribed": true, "checks": ["20:00 the evening before", "07:00 on the day"] }`

`subscription.endpoint` must be an `https` URL on a known push service
(`fcm.googleapis.com`, `*.push.apple.com`, `*.notify.windows.com`,
`updates.push.services.mozilla.com`). Anything else is `422`: the server POSTs to this
URL, so an unrestricted one is an SSRF primitive.

### `DELETE /api/push/subscribe?endpoint=…`

Unregisters **and deletes stored trips** (§8 commitment 1).

| Parameter | Required | Meaning |
|---|---|---|
| `endpoint` | yes | The subscription to remove. Only this subscription and the trips linked to it are deleted. |

`endpoint` is **required**. It was optional until F04, and omitting it deleted every
subscription on the server together with all their trips.

### `POST /api/push/test?trip_id=…`

Fires a warning immediately through the real path so judges need not wait for 20:00 (D4).
→ `{ "sent": true, "note": "Test warning sent to this device." }`

| Parameter | Required | Meaning |
|---|---|---|
| `trip_id` | yes | The trip to check and push for. |

`trip_id` is **required**. It was optional until F05, and omitting it acted on the first
trip in the database — pushing to another user's device and returning her trip id.

### Push payload

```json
{ "title": "Lift out at Outram Park",
  "body": "Use Exit 6 instead. Adds about 3 minutes.",
  "trip_id": "t_9fK2", "severity": "warn",
  "url": "/trip/t_9fK2" }
```

One line of body. Rachel's rule applies to Mdm Lim too: if it is worth interrupting for, it is
worth saying in one line.

---

## 8. Scenario control

### `GET /api/scenario` · `POST /api/scenario`

```json
{ "enabled": true,
  "scenarios": { "lift_outage_outram": true, "ewl_disruption": false },
  "note": "Simulated data is labelled in every response it appears in." }
```

Default **off**. Used by the demo, and available to judges who want to see the disruption path
on demand. It never changes whether `source`/`simulated_note` appear — those are always present
and always honest.

---

## 9. Frontend checklist

Things this contract makes possible that the rubric specifically rewards — worth confirming each
is actually rendered:

- [ ] `simulated_note` is visible wherever it appears (rubric caps mocked-as-live)
- [ ] Every `severity` is paired with its `label`; no state is colour-only
- [ ] `attribution` strings shown wherever the map or derived data appears (licence breach otherwise)
- [ ] `leave_by_label` is the largest thing on the trip screen
- [ ] `arrival_window` is shown as a window — never collapsed to one arrival time (L248, mandatory)
- [ ] `observed_at` age is visible, since nothing recomputes in the background
- [ ] `alternatives.original` rendered beside the options, not replaced by them
- [ ] `resolution: "station_only"` never names an exit
- [ ] `step_free: "unknown"` is worded as unknown, never as inaccessible
- [ ] `offline_notice` appears whenever the cached bundle is used
- [ ] `checks.label` shown near any warning, so "we detect, not predict" is visible


---

## 10. What the built API adds or changes

Written during the backend build (stages 1–9). Each entry says why, with the issue number in
`PS2_BACKEND_PLAN.md` §2 where there is one.

### Changed

| Field | Change | Why |
|---|---|---|
| `POST /api/trips` → `origin` | Example origin is now **Blk 208B New Upper Changi Road** `[103.930570, 1.324782]` | The old example's coordinate was not the address it named. Geocoded properly, "Blk 123 Bedok North St 2" is 1,364 m from the station — a 32-minute walk at her pace (**I12**). |
| `summary.timing_basis` | Wording is generated, and always says *scheduled* | GTFS is a timetable, not a stopwatch (D8). Example: `"Train ride is a scheduled 31 min, fixed by the timetable. A train every 2.5 min at this hour, so 0–2.5 min of waiting. 707 m of walking at an assumed 0.7 m/s."` |
| `options[].option_id` | Adds **`leave_earlier`** alongside `leave_later` | D2.1's rule only covered a delay that fits her buffer. The Annex C replay is 20 min against a 15 min buffer, so that option vanished. For a trip not yet begun, the useful advice is to leave earlier (**I14**). |
| `alternatives.options[].duration_min` | May be `null` | We only state a bus journey time when OneMap can time that service for that departure. Otherwise the bus is still offered and the time is left unstated rather than invented (**I15**). |
| `tiles.tile_pack_url` | `null`, and now carries `tiles.unavailable_reason` | I6 is parked. The reason is returned so the UI can explain it rather than showing an empty map. |

### Added

| Field | On | Meaning |
|---|---|---|
| `rerouted` | `RouteStatus` | `true` when a live outage blocked a door the stored plan used and the plan was rebuilt. The stored plan is updated, so `steps_plain` agrees with the banner (**I16**). |
| `summary.walk_distance_m` | `TripPlan` | Total walking metres, so the UI need not sum legs. |
| `lift_alerts[].parsed_exits`, `.line_prefix`, `.station_id`, `.detail` | `RouteStatus` | What the `LiftDesc` parser actually read. `detail` is a ready-to-show sentence; the others let a judge check the parse. |
| `disruption.on_her_route`, `.free_bus_islandwide` | `RouteStatus` | The island-wide free-bus string is matched loosely, since LTA writes it both hyphenated and not (T4). |
| `crowd[].window` | `RouteStatus` | `[StartTime, EndTime]` of the 10-minute bucket the reading covers. |
| `weather.areas[]` | `RouteStatus` | Which named forecast areas were read **and how far away they are** — the nearest to SGH is *City* at 1.66 km. Resolution is an area, never her street (§6 limitation 10). |
| `bus.stops`, `.distance_km`, `.first_bus`, `.last_bus`, `.not_running` | `Alternatives` | From LTA route data. `not_running: true` is the honest reading of an empty arrival list outside operating hours (T17) — it does not mean no bus exists. |
| `GET /api/push/key` | — | The browser needs the VAPID **public** key before it can subscribe. |
| `GET /api/destinations` | — | One entry, SGH. Keeps the destination out of the frontend as a literal. |
| `POST /api/push/test` → `payload` | — | When no browser has subscribed, the response carries the message that *would* have been sent, so a judge can read it without pairing a device. |

### Documented above but not emitted

Recorded after the PR #1 review. Each was verified against the running API on
2026-09-18, not inferred from the prose.

| Field | State | Why |
|---|---|---|
| `TripPlan.observed_at` | **Never emitted.** | A plan is derived from committed build-time data, not from an upstream read, so there is no observation time to report. The live blocks in `RouteStatus` each carry their own `observed_at`. |
| `access.lift_id` | **Absent.** | `v2/FacilitiesMaintenance` gives a `LiftID` only for a lift that is *out*. There is no roster of working lifts to name one from, so a lift is identified only when an outage names it, on `lift_alerts[].lift_id`. |
| `weather.area` | **Removed**, replaced by `weather.areas[]`. | §10 recorded the addition but not the removal. Two areas are read (home and hospital), so a single `area` could not say which one a reading came from. |
| `options[].delta_min` | `null` for taxi always, and for bus unless OneMap timed that service. | `delta_min` is derived from `duration_min`, which is only stated when measured (**I15**). Rather than invent a figure, the option is offered with the comparison left blank. |
| `options[].option_id: "leave_later"` | Never changes the leave time. | It is the "your buffer absorbs this" option: `leave_by` is the original, labelled *"Leave at HH:MM as planned"*. The name is misleading and is kept only because the frontend checklist already refers to it. |
| `GET /alternatives` | Returns bus and taxi even when `disruption` is `null`. | The options are useful on a clear day too, and suppressing them would make the screen appear broken. `disruption: null` is the signal that nothing is wrong, not an empty `options` array. |
| `/openapi.json` | No response models; the documented `422` is FastAPI's `{"detail": [...]}` shape. | Routes return plain `dict`, so the generated schema is `{}` for every 200. It is machine truth for **requests only**. The 422 body the app actually returns is the `error` envelope of §1 — `app/main.py` overrides FastAPI's handler — so the generated 422 schema is wrong. |

### Undocumented fields the API serves

Present in responses, absent from the prose above. Listed so the frontend does not
treat them as accidental.

| Field | On | Meaning |
|---|---|---|
| `leave_by`, `leave_by_label`, `timing_basis` | `options[]` | Same meaning as on `TripPlan.summary`, restated per option so a card is self-contained. |
| `preferences.buffer_min` | `POST /api/trips` request | Minutes of slack before the appointment. Appears in the response example but was never documented as a request field. Now bounded `0–120`. |
| `sent_at`, `digest` | push payload | `sent_at` is when the check ran; `digest` is the dedupe key over title+body+source, so a repeat check does not re-notify. |
| `trip_id` | `POST /api/push/test` | Required — see §7. |

### Changed by the PR #1 review fixes

Behaviour that differs from the prose above **because a finding was fixed**. The
finding IDs are those of the review on PR #1.

| Field | Now | Finding |
|---|---|---|
| `access.board_at.status`, `.alight_at.status` | `yes` when OSM tags that entrance `wheelchair=yes`, else `unknown`. It used to be hardcoded `unknown`. | F11 |
| `legs[].step_free`, `summary.step_free` | May be `unknown` where it was previously always `yes`. A walk with no staircase edge through a door nobody has tagged is not *known* to be step-free, and the rail leg cannot be stronger than its two doors, since station interiors are unmapped (§6 limitation 8). | F11 |
| `options[].step_free` (bus) | Derived from `bus.wheelchair_accessible`; `unknown` when that is `null`. Was always `yes`. | F23 |
| `lift_alerts[].blocked_exit_refs` | **Added.** Every exit an outage takes out, not just the first. `exit_code` remains the first, for the single-exit field. Anything deciding where she may walk must read this list. | F02 |
| `lift_alerts[].stale`, `crowd[].stale`, `weather.stale`, `disruption.stale`, `bus.stale` | **Added.** `source` stays `live \| simulated` as §1 requires; whether the reading is current is now its own per-block flag (§1 rule 4). Previously only the top-level `stale` said so. | F22 |
| `bus.observed_at` | **Added.** The bus block had no observation time at all. Live arrival and `not_running` are also suppressed when departure is more than ~30 min away, since they describe a bus leaving now. | F22, F23 |
| `RouteStatus.replan_failed` | **Added.** `true` when every step-free entrance we know of is out and no route could be built. `overall` is then `critical`. Previously this raised a 500. | F06 |
| `options[].viable` | Now also set on `leave_earlier`, `false` when the suggested departure has already passed. | F24 |
| Offline bundle `warnings[]` | **Added.** Never serves written steps without either a status snapshot or a warning saying it could not check. | F06 |
| `trip_id` | Now `t_` + 22 URL-safe characters (e.g. `t_nNaI_QM1R7RZQ8KQ6vS1BA`), not the 4 shown in the examples above. It is the only access control on `GET`/`DELETE`/status/offline, one of which returns her home coordinate. | F30 |
| `error.code` | Adds `NOT_FOUND`, `METHOD_NOT_ALLOWED` and `INTERNAL_ERROR`. Unknown routes, wrong methods and uncaught exceptions now use the §1 envelope instead of `{"detail": ...}` or text/plain. | F21 |
| `422` responses | `coord` must be a 2-element pair in degrees; `buffer_min` `0–120`; `walking_pace` one of `slow \| normal` (the keys of `timing.PACE`, so §3's stated pair is correct and enforced); the appointment must be in the future and within 400 days. | F15 |
| `subscription.endpoint` | Must be `https` on a known push service, else `422`. `results[].error` is a code (`PUSH_FAILED`, `ENDPOINT_NOT_ALLOWED`, `ENDPOINT_GONE`), never the upstream's response body. | F03 |

### Still not reconciled

- **§3's worked example is stale.** The origin was updated but the summary still shows
  `leave_by` 09:24, `duration_min` 46, `range_min` [41, 51] and `sheltered_pct` 78. Measured
  on 2026-09-18 for a 10:30 appointment at the API default (`prefer_sheltered=true`):
  **09:19, 50, [45, 56], 60**, arriving 10:03–10:14. The `timing_basis` string and the
  `access` block in §3.1 (`lift_id`, `status: "in_service"`) are illustrative and do not
  match what is served — see the two tables above.
- **§8's scenario shapes are wrong.** The GET/POST response shape is shown nested under
  `scenarios`, and the POST body is never documented; posting the nested shape returns 200
  and changes nothing. Only the flat body works. `{"enabled": false}` also cannot switch the
  demo off while a sub-scenario is still true.
- **`sheltered_pct` is always emitted**, not "only when rain is forecast" as §3 says.

### Behaviour worth knowing

- **Fetched on demand, never polled** — unchanged from §4, and now true of the plan too: `/status`
  is what revises a stale plan.
- **`PS2_USE_FIXTURES=1` runs the whole backend with no network**, serving recorded upstream
  responses flagged `stale` with their capture time. The app also falls back to this on its own
  when an upstream dies, so a screen must handle `stale: true` at any time.
- **With no credentials at all**, planning, status, crowd and weather still work from committed
  data and fixtures. Address search and push return `UPSTREAM_UNAVAILABLE` with a message naming
  the missing credential.
