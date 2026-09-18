import json
B = "PS2/backend/"
C = []
def c(path, line, body): C.append({"path": B + path, "line": line, "side": "RIGHT", "body": body})

c("app/services/lifts.py", 75, """**[P0] A lift that serves more than one exit only blocks the first exit it names.** This is a false negative, the dangerous direction for this persona.

`match_row` keeps only `next(e for e in exits if e in known)`, and `blocked_exits` (L143) blocks only that one exit.

Reproduced with `LiftDesc: "Exits 5/6 Street level - Concourse"` at EW16, while the default plan alights at Exit 6:
- `parsed_exits=['5','6']`, `exit_code='Exit 5'`
- `/status` → *"Exit 5's lift is under maintenance. Your route does not use it."*, `rerouted: false`
- The plan still sends her to Exit 6.

The regex on L32 also misses `Exits 6 & 7`, `6, 7`, `Exit6` (no space → `station_only`) and `EXIT NO. 6` (→ `['NO']`).

**Fix:** keep every parsed exit the station knows and block all of them. Widen the regex, and add these variants to `data/handchecked/lift_desc_examples.json`.""")

c("app/api/status.py", 127, """**[P0] "Your route does not use it." is shown for alerts where we can't know that.**

Every on-route alert that didn't trigger a re-plan gets this sentence, including:
- `unmatched` rows ("we could not tell which exit")
- `station_only` rows. A concourse↔platform lift at her station is on *every* step-free path.

Reproduced: `LiftDesc: "Exit6 Street level - Concourse"` at EW16 → *"An internal lift at Outram Park is under maintenance. Your route does not use it."* The plan still uses Exit 6.

The sentence is also wrong on the second `/status` call after a reroute. `refresh_plan` returns False because the stored plan already avoids the exit, so the reply pairs "does not use it" with a "See the new route" action.

**Fix:** only say "does not use it" for a `matched_exit` the plan provably avoids. For `unmatched` and `station_only` at EW5/EW16, raise a check-before-you-go warning.""")

c("app/data.py", 130, """**[P1] Outram "entrances" include other stations' exits, and exits with the same ref overwrite each other.**

`entrances_for("outram")` returns every entrance in the Outram bbox, keyed by the bare `ref`, so the last one wins. Measured against the committed graph:
- Outram Park **Exit 2** (16 m from the station, `wheelchair=yes`) is replaced by **Cantonment (CCL) Exit 2**, 884 m away, untagged.
- Outram Park **Exit 3** (107 m) is replaced by an unnamed Exit 3 at 462 m.
- `A`, `C`, `D`, `E`, `G` are **Chinatown's** exits.

Consequences:
- The real, tagged-accessible Exit 2 can never be chosen.
- When a reroute runs out of Outram exits, the plan says "Outram Park, Exit C", which is a Chinatown door about 560 m away.
- An LTA outage can't block those refs, because they come out `unmatched` against LTA's 1–8.

**Fix:** tag each entrance with its station at build time (by `name`, or nearest station within about 250 m). Filter on that, and key by `(station, ref)`.""")

c("app/api/push.py", 60, """**[P1] `DELETE /api/push/subscribe` with no `endpoint` deletes every subscription and all their linked trips.** It has no auth, and CORS is `*`.

Reproduced: one bare `DELETE` → `subscriptions_removed: 1, trips_removed: 1`, and the other user's trip then returns 404. Any web page she visits could do this.

The `endpoint` query parameter is also missing from `PS2_API_CONTRACT.md`.

**Fix:** require `endpoint`, remove the delete-all branch (`store.py:133-135`), and document the parameter.""")

c("app/api/push.py", 72, """**[P1] `/api/push/test` with no `trip_id` acts on someone else's trip.**

It takes `all_trips()[0]`, whoever planned it, pushes to that trip's subscribers, and returns `payload.trip_id`.
- With that ID, `GET /api/trips/{id}` returns `legs[0].from`, which is her home label and coordinates. `DELETE` also works.
- Repeated calls spam her phone; there is no rate limit.

**Fix:** require `trip_id` (or a per-device secret issued at subscribe time), and rate-limit or gate this endpoint to demo mode. See also the trip-ID length in `store.py:60`.""")

c("app/api/push.py", 52, """**[P1] SSRF: the subscription `endpoint` is never validated, and the upstream response is shown to the caller.**

`send_push` POSTs to whatever URL was subscribed, and `str(exc)` goes back in `results[].error` (L94). pywebpush's exception text includes the upstream response body.

Reproduced against a local server: `"Push failed: 404 Not Found\\nResponse body:INTERNAL-ADMIN-PAGE-CONTENT"`. The server's VAPID-signed JWT also goes to that host.

**Fix:** accept only `https` endpoints on known push-service hosts (`fcm.googleapis.com`, `*.push.apple.com`, `*.notify.windows.com`, `updates.push.services.mozilla.com`). Return a generic error code.""")

c("app/api/push.py", 32, """**[P2] A push send blocks the event loop, and there is no timeout.**

`webpush()` is synchronous (it uses requests, and pywebpush passes `timeout=None`). It is called directly from `async def push_test` and `async def run_check`.

Reproduced: `/api/health` took 5.5 s while `/push/test` waited on a slow endpoint. An endpoint that never answers hangs the whole server, and with the SSRF above, an attacker chooses that endpoint.

**Fix:** `await asyncio.to_thread(webpush, ..., timeout=10)`.""")

c("app/scenario.py", 18, """**[P1] The scenario flag is global, and it leaks into real scheduled pushes with no simulated label.**

`POST /api/scenario` needs no auth and flips a process-wide `_state`. `jobs.run_check → notify.check_trip` reads the same flag, and the push payload (`notify.py:48-57`) has no `source` or `simulated_note`.

Reproduced with `ewl_disruption` on, `check_trip` returns:
```
{'title': 'East-West Line delays towards Tuas Link', 'body': 'About 20 more minutes on your way to the hospital. …', 'severity': 'critical', …}
```
If the demo is left armed at 20:00, every real subscriber gets that as a genuine alert. `mark_sent` then stops any correction being sent. This is exactly the "mocked data presented as live" cap.

**Fix:** have the scheduled jobs ignore the scenario, or scope it to a demo trip or session. Carry `source` and `simulated_note` into the push payload whenever it is used.""")

c("app/scenario.py", 86, """**[P1] Recorded fixtures are labelled `source: "live"`.**

`_source: "live"` is stamped regardless of `fetched.origin`. With `PS2_USE_FIXTURES=1`, or on the automatic fallback when upstream fails, every lift row shows `source: "live"`. Only the top-level `stale` flag says otherwise. Verified in fixture mode: sources `{'live'}` with `stale: true`.

The same applies to:
- `crowd.py:31` and `weather_policy.py:38`, which hardcode `"live"`.
- `alternatives.py:91`: a day-old `bus_*` fixture gives `eta_min: 0` and "The next bus has a wheelchair ramp", with no `stale` or `observed_at`.

**Fix:** set `source` from `fetched.origin` (`live` / `stale` / `fixture`), add `stale` and `observed_at` to each block (contract rule 4), and don't compute a bus ETA from a fixture.""")

c("app/api/status.py", 55, """**[P1] A reroute is saved permanently and never undone.**

`refresh_plan` overwrites the stored plan with `rerouted: True`. Nothing ever re-plans back.

Reproduced: arm the Outram lift scenario, call `/status`, then turn the scenario off.
- `/status` says "Your usual route is clear".
- The stored and offline plan still use Exit 7, leave-by stays 5 min earlier, and `rerouted` stays `true`.

**Fix:** keep the original plan (or its inputs) and derive the effective plan from current alerts on each call. Base "moved you" on the diff from the original, not on whether *this* call re-planned.""")

c("app/api/status.py", 48, """**[P1] If re-planning fails, `/status` returns 500 and `/offline` hides the outage.**

`planner.plan_trip` raises `RuntimeError("no step-free walking route…")` and nothing here catches it.

Reproduced with Bedok exits A, B and C all out:
- `/status` → 500.
- `/offline` catches it and returns 200 with `status_snapshot: null`. `steps_plain[0]` is still "Walk … to Bedok MRT Exit B", a door whose lift is out, with no warning.

**Fix:** catch the error, keep the alerts, and set a critical "no step-free entrance available" overall. `/offline` should never serve steps with neither a snapshot nor a warning.""")

c("app/jobs.py", 46, """**[P1] Marking a trip sent is all-or-nothing, so one bad subscription causes duplicate pushes. There is also no real retry.**

- **Duplicates:** if one of her subscriptions fails (an old browser, or a 404/410 expired endpoint), the digest is never marked. Every later run with the same label re-sends to the subscriptions that *did* succeed. Reproduced: 3 runs gave 3 identical pushes to the working endpoint.
- **Expired endpoints:** 404/410 subscriptions are never removed (`WebPushException.response.status_code` is never checked). They keep this failing forever and stay stored past trip deletion.
- **No real retry:** the only retry is the next run with the same label, 24 h later, which for a 10:30 appointment is after the appointment. So "failures remain retryable" from the fix comment doesn't hold in practice.
- **One error stops the run:** there is no try/except around `check_trip`.

**Fix:** record sent state per `(trip, label, endpoint)`, delete subscriptions on 404/410, and wrap each trip's check. Add a short retry (for example a one-off job +10 min) if retry matters. Also claim the send atomically (`INSERT … ON CONFLICT DO NOTHING`) so two workers don't both send.""")

c("app/jobs.py", 53, """**[P3] The check windows don't match D3's wording.**

- The "07:00 today" run uses `now+24h`, so it includes tomorrow's 06:30 appointment.
- The "20:00 evening before" run uses 36 h, so it reaches 08:00 two days ahead: a 07:30 appointment gets a push two evenings before.

**Fix:** compute calendar windows in SGT (07:00 → today until midnight; 20:00 → tomorrow).""")

c("app/jobs.py", 70, """**[P2] Retention can run to about 48 h, not the 24 h promised in §8 commitment 1.**

- The sweep runs only at 03:00 (not on startup) and removes trips more than 24 h past the appointment. A 03:30 appointment survives the next day's sweep at 23.5 h and is removed at 47.5 h (reproduced with `sweep(now=…)`).
- `push_subs` rows are never swept, and keep dangling `trip_ids`.

**Fix:** sweep hourly and on startup, and drop subscriptions whose trips are all gone. Or reword the privacy statement.""")

c("app/store.py", 60, """**[P2] Trip IDs are 4 characters and act as the only access control.**

`token_urlsafe(4)` with `-` and `_` stripped, cut to 4 characters: about 14.8M values, and about 0.03% come out as 3 characters.
- GET, DELETE, status and offline need nothing but the ID, and they return her home coordinate.
- A collision raises `IntegrityError` → 500.

**Fix:** use `secrets.token_urlsafe(16)` and retry on collision.""")

c("app/store.py", 113, """**[P2] Turning notifications off can leave trips on the server (privacy commitment 1).**

`INSERT OR REPLACE` overwrites `trip_ids`, and the default is `[]`. If she subscribes for trip A and later re-subscribes with trip B:
- A is unlinked and gets no warnings.
- `DELETE /push/subscribe` leaves A in place.

Reproduced.

**Fix:** merge `trip_ids` on upsert, or link trips to the subscription or device when they are created.""")

c("app/services/disruption.py", 73, """**[P1] The delay figure can come from a different line's advisory (trap T6).**

The loop takes the first `additional travelling time of N min` found in any non-test message, whichever line it is about.

Reproduced:
- Content `"NSL - … 30 minutes … EWL - … 10 minutes"` → `delay_min=30` for her EWL trip.
- A newer separate NSL message also wins.

That wrong figure drives the push body and leave-earlier.

`score_rules.py` message example #6 expects 30 for the bundled NSL/EWL content, so the check locks this bug in.

**Fix:** split `Content` on `<LINE> -` prefixes and only parse EWL clauses.""")

c("app/services/disruption.py", 66, """**[P2] Direction is ignored, and an all-test-broadcast state is still reported as a disruption.**

- A segment with `Direction: "Pasir Ris"` (eastbound; she rides towards Tuas Link) is treated as hers: "… delays towards Pasir Ris", plus leave-earlier advice.
- When every message is a `Test :` broadcast but the segment is populated, a critical disruption is still returned.

Both reproduced.

**Fix:** only keep segments whose direction is `Tuas Link` or `Both`. Also, when `_messages()` is empty but raw messages exist and every one is a test, return None.""")

c("app/services/planner.py", 104, """**[P1] `step_free: "yes"` is claimed for exits whose accessibility is unknown.**

- The rail leg is hardcoded `"yes"`.
- The walk legs and the summary (L144) check only `steps_used == 0`.
- `access` is always `status: "unknown"`.

Reproduced: with Outram exits 4 and 6 blocked she is sent to Exit 7 (`wheelchair=None`). The summary still says step-free `"yes"` and "take the lift to street level".

The contract enum has `unknown` for exactly this (§6 limitation 5, D11).

**Fix:** return `"unknown"` (and soften the lift sentence) unless the chosen entrance is `wheelchair=yes`.""")

c("app/services/planner.py", 123, """**[P3] The last walk leg's geometry runs backwards.**

`walk_out` is routed SGH → exit (L53), but the leg says `from` exit, `to` SGH. A frontend animating or snapping progress along the line will run backwards.

**Fix:** reverse `walk_out.coords`.""")

c("app/services/timing.py", 52, """**[P2] Headway is looked up at the appointment hour, not the boarding hour. The nearest-hour fallback also invents service when no trains run.**

- **Wrong hour:** a Monday 08:40 appointment uses the 08h headway (2.5 min), but she boards around 07:39, when it is 5.0. The slow end is under-estimated by about 3 min, which breaks "plan against the slow end".
- **No trains running:** a 01:30 or 05:30 appointment returns a normal plan ("leave 00:20" / "04:20") using the nearest hour's headway.
- **Holidays:** public holidays use the weekday table.

**Fix:** estimate the boarding time, then look up that hour and day type (one iteration is enough). Reject or warn when that hour has no service, and add a PH list mapped to `sunday_ph`.""")

c("app/api/trips.py", 26, """**[P2] Request validation gaps.**

All reproduced:
- `coord: []`, `[103.93]` or `[x, y, z]` → TypeError → plain-text 500.
- `buffer_min: -120` → leave 11:34 for a 10:30 appointment (200). `buffer_min: 1e12` → OverflowError 500.
- Appointments in 2001 or 9999 are accepted and stored. A date-only `"2026-09-21"` silently means midnight.
- `walking_pace: "sprint"` is accepted, stored and echoed back, but planned as slow.

**Fix:** `conlist(float, min_length=2, max_length=2)` with finite values, `buffer_min: int = Field(15, ge=0, le=120)`, `walking_pace: Literal[...]`, and reject past or far-future appointments.""")

c("app/api/trips.py", 102, """**[P2] Address search returns 500 on network errors, and ignores fixtures mode.**

Only `OneMapAuthError` is caught. A connection error, timeout or 5xx from `raise_for_status` gives a 500 rather than `UPSTREAM_UNAVAILABLE`. With a token set, it also calls OneMap even when `PS2_USE_FIXTURES=1`, and so does `onemap.pt_route` in alternatives.

**Fix:** also catch `httpx.HTTPError`, and short-circuit OneMap in fixtures mode.""")

c("app/main.py", 41, """**[P2] The error shape isn't always top-level, as the contract promises.**

This handler is registered for FastAPI's `HTTPException`, but routing raises Starlette's. Reproduced:
- Unknown routes return `{"detail":"Not Found"}`.
- A wrong method returns `{"detail":"Method Not Allowed"}`.
- Uncaught exceptions (see trips/status) return a text/plain 500.

**Fix:** register for `starlette.exceptions.HTTPException`, and add a catch-all `Exception` handler returning `{"error": {..., "retryable": true}}`.""")

c("app/data.py", 125, """**[P2] Snapping uses the main component of the graph *with* stairs, not of the step-free graph (I11 is half done).**

`self.component` / `main_by_area` were built on the stairs-included graph. With stairs removed, Bedok's main component splits into 105 separate pieces (largest 12,077 nodes; the next 235, 77, …).

29 of 625 grid origins with a snap under 100 m land on a small piece and get 400 "no step-free walking route". Example: `[103.937, 1.3197]`, 42 m from the main step-free network.

**Fix:** compute components on `step_free` for `step_free=True`, or try the k nearest candidates until one routes.""")

c("app/sources/base.py", 97, """**[P1] Every 200 is recorded to the fixture, even if empty or invalid, and a write failure throws away a good fetch.**

- **Empty replies overwrite fixtures:** one live run after midnight turns `bus_84009.json` (10 services) into `[]`, because BusArrival returns nothing outside hours (T17). The offline demo then says "Not running now" forever. data.gov.sg `{"code":24,"data":null}` caches and records `None` the same way. Both reproduced with `httpx.MockTransport`.
- **Write failures discard good data:** `_record` is inside the `try`, so a `PermissionError` (read-only or container filesystem) turns a good 200 into `origin: "stale"`.
- **Runtime writes into the repo:** the bus fixture is rewritten every 20 s, which dirties the git tree during the demo.
- **Not atomic:** `write_text` is not atomic, and `_from_fixture` (L74) doesn't guard `json.loads`, so a truncated file turns the fallback into a 500.

**Fix:** record fixtures only behind an explicit flag or script, and only when the payload passes a per-source check. Write to a temp file then `os.replace`, and keep recording out of the `try`.""")

c("app/sources/base.py", 88, """**[P2] During an outage, callers queue behind the lock and every request re-hits upstream.**

- The lock is held for the whole upstream call (20 s timeout).
- A failure doesn't update `_entry.at`, so the next request retries immediately.

Reproduced: with a 1 s hang, 5 concurrent callers returned at 1, 2, 3, 4 and 5 s. `/status` makes 4 source calls in a row, so a real outage can take a single request past 80 s. That's the opposite of "serve stale".

Also, `asyncio.Lock()` is created at import (L58) and shared across event loops.

**Fix:** on failure, back off before the next retry. Serve the stale value to waiters instead of queuing, and shorten the timeout to about 5 s.""")

c("app/services/alternatives.py", 127, """**[P2] The bus option always says `step_free: "yes"`, and its live data is measured against now, not her departure.**

- `step_free` is `"yes"` even when `wheelchair_accessible` is `False` or `None`.
- At the 20:00 or 01:00 check, "Not running now; first bus 0530" and `eta_min` describe *now*, not tomorrow's departure. Reproduced for a 15:00 trip checked at 01:03.

**Fix:** derive `step_free` from `wheelchair_accessible` (`unknown` when `None`). Suppress live ETA and not-running when departure is more than about 30 min away.""")

c("app/services/alternatives.py", 245, """**[P2] The taxi stand is always the one at Outram Park.**

`_taxi_option(DEST_STATION)` is hardcoded. For a trip she hasn't started (she's still in Bedok, which is the main case for a pre-departure disruption), she is offered "Outram Rd outside Outram Park MRT Station, 32 m away". Reproduced.

I7's "the station the current leg is heading to" doesn't fit here.

**Fix:** anchor on the origin station before departure.""")

c("app/services/alternatives.py", 202, """**[P2] Leave-earlier has no slack and can suggest a time that has already passed.**

- **No slack:** `arrival_at = arrive_late + shortfall`, which is exactly the appointment time. Reproduced: arrival 14:59:03 for a 15:00 appointment, while the text says "still in time".
- **Already past:** `earlier` is never compared with now. An 08:12 advisory for an 08:30 departure gives "Leave at 08:10 instead".

**Fix:** keep the buffer (shift by the full delay), and drop or reword the option when `earlier < now`.""")

c("app/services/weather_policy.py", 25, """**[P2] Rain never changes the route, but the label says it does.**

The planner never reads the weather; shelter comes only from `preferences.prefer_sheltered`. This label, D9, contract §3 and plan §1.5 all say rain gives a sheltered walk. A judge testing "rain → sheltered route" will find it isn't wired in.

**Fix:** make `rain_expected` force `prefer_sheltered` when planning or re-planning, or change the claim and this sentence.""")

c("scripts/verify_stepfree.py", 51, """**[P1] `verify_stepfree.py` can PASS without checking anything. Its output is a claim going into WRITEUP.md.**

- **L50-51:** coordinate pairs that don't match a graph node are skipped with `continue`. A real staircase edge FAILs with exact coordinates, but PASSes when nudged by 1 cm.
- **L72-73:** legs without `station_code` / `exit_code` are skipped. With them stripped, the result is `('PASS', [])`.
- **L80:** `ok = tag == "yes" or not lift_out` passes any untagged entrance, including one with no lift at all. `station_only` / `unmatched` outages are ignored (L65).
- The steps check reads the same OSM edges the step-free router was built from, so it mostly checks itself.

Today's run does resolve 17/17 and 27/27 edges, so the current PASS is real, but nothing guards it.

**Fix:** FAIL on any unresolved pair or when zero entrances are checked, and print the checked counts. Require `wheelchair=yes` or (a lift near the exit and no matched or station-level outage).""")

c("scripts/build_data.py", 100, """**[P2] A failed download puts the presigned S3 URL, with its token, in the error message.**

`raise_for_status()` includes the full URL, `X-Amz-Security-Token=…`, which contradicts the comment on L99. Reproduced with a 403: *"Client error '403 Forbidden' for url 'https://…X-Amz-Security-Token=…'"*. Tracebacks get pasted into chat and CI logs.

**Fix:** check `blob.status_code` and `sys.exit(f"{endpoint}: download failed ({blob.status_code})")`.""")

c("scripts/build_data.py", 151, """**[P3] One failed BusStops fetch breaks every later build.**

`bus_routes.json` is written before BusStops is fetched, and the skip check only looks at `bus_routes.json`. If BusStops fails once, every later `--all` run skips the fetch and `build_bus_options` crashes with `FileNotFoundError`. Reproduced.

**Fix:** check both files, and write both only after both fetches succeed. The Overpass and GTFS cache writes have the same non-atomic pattern.""")

body = r"""## Review of `6405e32`: correctness, security and docs

I split this review across five parallel passes: push/scheduler, planner/timing, lifts/disruption/alternatives, sources/pipeline, and docs vs code. The headline findings were re-run against the PR head in fixture mode with a scratch DB. Inline comments carry the file:line detail and repro notes. **No code changes were made.**

### Were the previous four findings fixed?
| Prior finding | Status |
|---|---|
| Push sent to every subscription | ✅ Fixed. `jobs.py:37` and `push.py:89` filter by `trip_ids`. |
| Digest marked before delivery | ⚠️ Fixed narrowly. Nothing is marked on failure, but one bad subscription now causes **duplicate** pushes, and there is no retry before the appointment (inline on `jobs.py:46`). |
| Naive timestamps depend on the server TZ | ✅ Fixed. Naive → SGT, and aware → converted. |
| Origin silently snapped to Bedok | ✅ Fixed (bbox + 100 m haversine). Remaining gaps: snapping uses the stairs-included component, and coords aren't validated (inline). |

Tests pass (9), `score_rules.py` gives 16/16, `verify_stepfree.py` gives PASS. **No secrets are committed** (searched the diff, history and fixtures).

### Must fix before merge
**P0: route safety** (false "all clear" for a step-free persona)
- [ ] A lift serving two exits (`Exits 5/6`) only blocks the first exit. Her Exit 6 stays in the plan (`lifts.py:75`).
- [ ] "Your route does not use it" is shown for `unmatched` and `station_only` outages at her own station (`status.py:127`).

**P1**
- [ ] Outram entrances mix in Chinatown and Cantonment exits. The real accessible Exit 2 is overwritten by Cantonment's (`data.py:130`).
- [ ] `DELETE /api/push/subscribe` with no endpoint wipes every subscription and trip (`push.py:60`).
- [ ] `/push/test` with no `trip_id` acts on another user's trip and leaks its ID, and through it her home coordinate (`push.py:72`).
- [ ] SSRF via the subscription endpoint, with the upstream response returned to the caller (`push.py:52`).
- [ ] Scenario flag is global. An armed demo sends unlabelled simulated disruptions to real subscribers at 20:00 (`scenario.py:18`).
- [ ] Fixture and fallback data are labelled `source: "live"`, which risks the rubric cap (`scenario.py:86`, crowd, weather, bus).
- [ ] Reroute is saved permanently and never reverted (`status.py:55`). A failed re-plan gives a 500 on `/status`, and `/offline` serves steps through a blocked door (`status.py:48`).
- [ ] Per-trip all-or-nothing marking gives duplicate pushes, 404/410 subscriptions are never pruned, and there is no real retry (`jobs.py:46`).
- [ ] Delay figure taken from another line's advisory (`disruption.py:73`). `score_rules` message #6 locks the bug in.
- [ ] `step_free: "yes"` claimed for exits of unknown accessibility (`planner.py:104`).
- [ ] Empty or invalid upstream 200s overwrite committed fixtures, and fixtures are rewritten into the repo at runtime (`base.py:97`).
- [ ] `verify_stepfree.py` can pass vacuously (`verify_stepfree.py:51`).

### Docs vs code (not inline; the lines are mostly unchanged context)
**P1**
- [ ] **Stage 3/4 numbers mix two configurations.** The planner and `verify_stepfree.py` default to `prefer_sheltered=False`, but `POST /api/trips` defaults it to `True`.
  - With `False`: 696 m, **38%** sheltered, reroute +142 m / 4 min earlier.
  - With `True` (what the API serves): **707 m**, 60%, reroute **+171 m / 5 min** (09:19 → 09:14).
  - So "696 m, 60% sheltered" (§9 stage 3) and "+143 m, 4 min" (stage 4) each mix the two runs, and stage 4 contradicts I16. Pick one default and re-measure `PS2_BACKEND_PLAN.md` §9, I12, I17 and the `config.py:41` comment.
- [ ] `backend/README.md:96`: "Step-free route costs 13 m over the unrestricted one" isn't computed by `verify_stepfree.py`. It was measured from the old Blk 123 home (I11).
- [ ] **The privacy statement is wrong about OneMap.** I9 says OneMap sees trip endpoints "only in the offline verification script", but `alternatives.py:60` sends her home coordinate to OneMap on every `/alternatives` call. Fix I9 and decision record §8.
- [ ] Privacy §8 lists only coordinates, stations, exits and lifts. The server also stores the address label, preferences and full walking geometry from home, and `push_subs` rows are never swept. Update §8 or reduce what's stored.

**P2**
- [ ] **Contract drift not recorded in §10.**
  - `TripPlan.observed_at` is never emitted.
  - `access.lift_id` is absent, and `status` is always `unknown`.
  - `/alternatives` returns bus and taxi options with no disruption.
  - `delta_min` is null for taxi, and for bus unless OneMap timed it.
  - `leave_later` never actually changes the leave time.
  - Undocumented fields and parameters:
    - options: `leave_by`, `leave_by_label`, `timing_basis`
    - push: `trip_id` on `/push/test`, `sent_at` and `digest` in the payload, `?endpoint=` on `DELETE /push/subscribe`
    - trips: `preferences.buffer_min`
  - `weather.areas[]`, not `area`.
  - `/openapi.json` has no response models, and the 422 is documented as FastAPI's `{detail}` shape.
- [ ] Contract §8 shows a nested `{"scenarios":{…}}` POST body. That body returns 200 and changes nothing; the README's flat body is the one that works. Also, `{"enabled": false}` can't switch the demo off while any sub-scenario is true (`scenario.py:74`).
- [ ] The D7 hand-checked lift↔exit table for EW5/EW16 (plan §4:303) doesn't exist. `data/handchecked/` holds only parser examples, and 6 of the 10 `LiftDesc` rows are hand-written although the file says "Every row is real".
- [ ] `PS2_INDEX.md`:
  - L8 still says "No implementation started".
  - L10 commits `/home/zachary/...`.
  - S13 says "eight issues (I1–I8)", but there are 17.
  - S14 says "before the backend exists".
- [ ] Contract §3 example: the origin was updated, but the summary still shows 09:24, 46 min, 41–51, 78% and "0–5 min". §5 still shows only `leave_later`.

**P3**
- [ ] Plan §4 module layout:
  - lists `api/scenario.py`, but the routes live in `status.py`
  - omits `api/offline.py`, `services/{walking,notify,alternatives}.py`, `sources/base.py`, `data.py`, `score_rules.py` and `gen_vapid.py`
  - §5 says 613 exits; the real count is 603.
- [ ] README:
  - "paste your two keys", but `.env.example` has five, and without the VAPID keys `/push/key` returns 503
  - `PS2_DB` is undocumented
  - "four real lift outages stay live" only holds for the 17 Sep capture

### Minor / hygiene (P3)
- `leave_by` is derived from the unrounded slow end and truncated, so 10:30 − 15 − 55 shows 09:19, not 09:20, and the window ends on odd seconds (`timing.py:85`). Either derive from `range_min[1]` as the contract says, or update the contract.
- The snap distance (up to 100 m) isn't added to walk distance or time (`walking.py:88`). Entrance choice uses raw distance even when `prefer_sheltered` is on (`walking.py:111`).
- **Scheduler and digest:**
  - Every uvicorn worker starts its own scheduler, and `was_sent` → send → `mark_sent` isn't atomic, so `--workers 2` gives duplicate pushes.
  - The digest covers only title and body, so a second on-route outage produces no new push.
- `datamall.py:55-58`: `_fetch_crowd` is dead and broken. Delete it.
- **Reproducibility and repo hygiene:**
  - `requirements.txt` has only `>=` bounds. Pin versions or add a lock file.
  - `built_at=now()` changes the 4.9 MB `stepfree_graph.json` on every rebuild.
  - `.gitignore` misses `*.sqlite3-journal`/`-wal` and `.DS_Store`.
  - `PS2_USE_FIXTURES=1` still falls through to the network when a fixture is missing, and OneMap ignores the flag.

### Test gaps
`test_push_delivery.py` stubs `was_sent`, `mark_sent` and `send_push` in every test. Nothing exercises:
- real SQLite dedupe, or partial-failure duplicates
- 404/410 cleanup
- `trip_ids` overwrite on re-subscribe, or `sweep()`
- multi-exit or unmatched lifts against the route
- direction or bundled-line disruption parsing
- the fixture-vs-live `source` label

`score_rules.py` never runs `assess()`, `affects_route` or `blocked_exits`, so the dangerous paths above pass 16/16. Please add held cases with expected *route outcomes*, not just parser outputs.
"""

review = {"commit_id": "6405e329d12fc6468fca609560642f9da05e9ef6", "event": "COMMENT", "body": body, "comments": C}
json.dump(review, open("/private/tmp/claude-501/-Users-rayden-Desktop-projects-ltaxnebula-nebulax-lta/0c669e66-ef51-4cd3-b7af-0894f8a4d718/scratchpad/verify/review.json", "w"))
print(len(C), "inline comments")
