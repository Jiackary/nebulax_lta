# PS2 — Backend API Contract

**What this is.** Every field the backend serves, and what the screen does with it. Written so
frontend work can start before the backend exists.

**Companions:** [`PS2_BACKEND_PLAN.md`](PS2_BACKEND_PLAN.md) for how it is built,
[`PS2_DECISION_RECORD.md`](PS2_DECISION_RECORD.md) for why. Decision references are `D1`–`D14`.

**Machine truth.** FastAPI serves `/openapi.json` and `/docs`. Where this document and the
generated schema disagree, the schema wins and this file is the bug.

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

---

## 3. Planning a trip

### `POST /api/trips`

```json
{ "origin": { "label": "Blk 123 Bedok North St 2", "coord": [103.9312, 1.3271] },
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

`DELETE /api/push/subscribe` unregisters **and deletes stored trips** (§8 commitment 1).

### `POST /api/push/test`

Fires a warning immediately through the real path so judges need not wait for 20:00 (D4).
→ `{ "sent": true, "note": "Test warning sent to this device." }`

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
