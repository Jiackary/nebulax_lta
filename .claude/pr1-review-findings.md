# PR #1 review findings — full text (fetched from GitHub after the correction pass)

Review: https://github.com/Jiackary/nebulax_lta/pull/1#pullrequestreview-5239015959

## Index

| ID | Sev | Location | Finding |
|---|---|---|---|
| F01 | P0 | `app/api/status.py:127` | "Your route does not use it." is shown for alerts where we can't know that. |
| F02 | P0 | `app/services/lifts.py:75` | A lift that serves more than one exit only blocks the first exit it names. |
| F03 | P1 | `app/api/push.py:52` | SSRF: the subscription `endpoint` is never validated, and the upstream response is shown to the caller. |
| F04 | P1 | `app/api/push.py:60` | `DELETE /api/push/subscribe` with no `endpoint` deletes every subscription and all their linked trips. |
| F05 | P1 | `app/api/push.py:72` | `/api/push/test` with no `trip_id` acts on someone else's trip. |
| F06 | P1 | `app/api/status.py:48` | If re-planning fails, `/status` returns 500 and `/offline` hides the outage. |
| F07 | P1 | `app/api/status.py:55` | A reroute is saved permanently and never undone. |
| F08 | P1 | `app/data.py:130` | Outram "entrances" include other stations' exits, and exits with the same ref overwrite each other. |
| F09 | P1 | `app/scenario.py:18` | The scenario flag is global, and it leaks into real scheduled pushes with no simulated label. |
| F10 | P1 | `app/services/disruption.py:73` | The delay figure can come from a different line's advisory (trap T6). |
| F11 | P1 | `app/services/planner.py:104` | `step_free: "yes"` is claimed for exits whose accessibility is unknown. |
| F12 | P1 | `app/sources/base.py:97` | Every 200 is recorded to the fixture, even if empty or invalid, and a write failure throws away a good fetch. |
| F13 | P1 | `scripts/verify_stepfree.py:51` | `verify_stepfree.py` can PASS without checking anything. Its output is a claim going into WRITEUP.md. |
| F14 | P2 | `app/api/push.py:32` | A push send blocks the event loop, and there is no timeout. |
| F15 | P2 | `app/api/trips.py:26` | Request validation gaps. |
| F16 | P2 | `app/api/trips.py:102` | Address search returns 500 on network errors, and ignores fixtures mode. |
| F17 | P2 | `app/data.py:125` | Snapping uses the main component of the graph *with* stairs, not of the step-free graph (I11 is half done). |
| F18 | P2 | `app/jobs.py:46` | Marking a trip sent is all-or-nothing, so one bad subscription causes duplicate pushes. There is also no real retry. |
| F19 | P2 | `app/jobs.py:53` | The check windows don't match D3's wording, and the actual evening-before push can be skipped. |
| F20 | P2 | `app/jobs.py:70` | Retention can run to about 48 h, not the 24 h promised in §8 commitment 1. |
| F21 | P2 | `app/main.py:41` | The error shape isn't always top-level, as the contract promises. |
| F22 | P2 | `app/scenario.py:86` | Recorded fixtures are labelled `source: "live"`. |
| F23 | P2 | `app/services/alternatives.py:127` | The bus option always says `step_free: "yes"`, and its live data describes now, not her departure. |
| F24 | P2 | `app/services/alternatives.py:202` | Leave-earlier has no slack and can suggest a time that has already passed. |
| F25 | P2 | `app/services/alternatives.py:245` | The taxi stand is always the one at Outram Park. |
| F26 | P2 | `app/services/disruption.py:66` | Direction is ignored, and an all-test-broadcast state is still reported as a disruption. |
| F27 | P2 | `app/services/timing.py:52` | Headway is looked up at the appointment hour, not the boarding hour. The nearest-hour fallback also invents service when no trains run. |
| F28 | P2 | `app/services/weather_policy.py:25` | Rain never changes the route. The label is only true because of the default preference. |
| F29 | P2 | `app/sources/base.py:88` | During an outage, callers queue behind the lock and every request re-hits upstream. |
| F30 | P2 | `app/store.py:60` | Trip IDs are 4 characters and act as the only access control. |
| F31 | P2 | `app/store.py:113` | Turning notifications off can leave trips on the server (privacy commitment 1). |
| F32 | P2 | `scripts/build_data.py:100` | A failed download puts the presigned S3 URL, with its token, in the error message. |
| F33 | P3 | `app/services/planner.py:123` | The last walk leg's geometry runs backwards. |
| F34 | P3 | `scripts/build_data.py:151` | One failed BusStops fetch breaks every later build. |

---

## Full comment text

### F01 — `PS2/backend/app/api/status.py:127` (P0)

**[P0] "Your route does not use it." is shown for alerts where we can't know that.**

Every on-route alert that didn't trigger a re-plan gets this sentence, including:
- `unmatched` rows ("we could not tell which exit")
- `station_only` rows. A concourse↔platform lift at her station may well be on her step-free path, and we can't tell. (Outram Park is a three-line interchange: NE3 and TE17 rows also resolve to EW16, so it could be an NEL- or TEL-side lift.)

Reproduced: `LiftDesc: "Exit6 Street level - Concourse"` at EW16 → *"An internal lift at Outram Park is under maintenance. Your route does not use it."* The plan still uses Exit 6.

The sentence is also wrong on the second `/status` call after a reroute. `refresh_plan` returns False because the stored plan already avoids the exit, so the reply pairs "does not use it" with a "See the new route" action.

**Fix:** only say "does not use it" for a `matched_exit` the plan provably avoids. For `unmatched` and `station_only` at EW5/EW16, say it *may* affect her route and raise a check-before-you-go warning.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542794)

---

### F02 — `PS2/backend/app/services/lifts.py:75` (P0)

**[P0] A lift that serves more than one exit only blocks the first exit it names.** This is a false negative, the dangerous direction for this persona.

`match_row` keeps only `next(e for e in exits if e in known)`, and `blocked_exits` (L143) blocks only that one exit.

Reproduced with `LiftDesc: "Exits 5/6 Street level - Concourse"` at EW16, while the default plan alights at Exit 6:
- `parsed_exits=['5','6']`, `exit_code='Exit 5'`
- `/status` → *"Exit 5's lift is under maintenance. Your route does not use it."*, `rerouted: false`
- The plan still sends her to Exit 6.

The regex on L32 also misses `Exits 6 & 7`, `6, 7`, `Exit6` (no space → `station_only`) and `EXIT NO. 6` (→ `['NO']`).

Caveat: all four live rows captured so far name a single exit. The only `Exits A/B` example (#7 in `lift_desc_examples.json`) is hand-written, so this format hasn't been seen live yet. `score_rules.py` checks `parsed_exits` and `resolution` but never `exit_code`, which is why #7 passes despite the bug.

**Fix:** keep every parsed exit the station knows and block all of them. Widen the regex, and add these variants to `data/handchecked/lift_desc_examples.json`.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542784)

---

### F03 — `PS2/backend/app/api/push.py:52` (P1)

**[P1] SSRF: the subscription `endpoint` is never validated, and the upstream response is shown to the caller.**

`send_push` POSTs to whatever URL was subscribed, and `str(exc)` goes back in `results[].error` (L94). pywebpush's exception text includes the upstream response body.

Reproduced against a local server: `"WebPushException: Push failed: 404 Not Found\nResponse body:INTERNAL-ADMIN-PAGE-CONTENT, Response INTERNAL-ADMIN-PAGE-CONTENT"`.

- The body is echoed when the target returns a status above 202. For connection errors, the `requests` error text still reveals whether a host or port is open.
- A VAPID JWT is sent too, but its `aud` is the target's own origin, so it can't be replayed against real push services.
- Preconditions: `VAPID_PRIVATE_KEY` is set, and the attacker supplies well-formed `p256dh`/`auth` keys (easy to generate).

**Fix:** accept only `https` endpoints on known push-service hosts (`fcm.googleapis.com`, `*.push.apple.com`, `*.notify.windows.com`, `updates.push.services.mozilla.com`). Return a generic error code.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542822)

---

### F04 — `PS2/backend/app/api/push.py:60` (P1)

**[P1] `DELETE /api/push/subscribe` with no `endpoint` deletes every subscription and all their linked trips.** It has no auth.

Reproduced: one bare `DELETE` → `subscriptions_removed: 1, trips_removed: 1`, and the other user's trip then returns 404. Any HTTP client can do this.

The `endpoint` query parameter is also missing from `PS2_API_CONTRACT.md`.

**Fix:** require `endpoint`, remove the delete-all branch (`store.py:133-135`), and document the parameter.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542809)

---

### F05 — `PS2/backend/app/api/push.py:72` (P1)

**[P1] `/api/push/test` with no `trip_id` acts on someone else's trip.**

It takes `all_trips()[0]`, whoever planned it, pushes to that trip's subscribers, and returns `payload.trip_id`.
- With that ID, `GET /api/trips/{id}` returns `legs[0].from`, which is her home label and coordinates. `DELETE` also works.
- Repeated calls spam her phone; there is no rate limit.

**Fix:** require `trip_id` (or a per-device secret issued at subscribe time), and rate-limit or gate this endpoint to demo mode. See also the trip-ID length in `store.py:60`.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542815)

---

### F06 — `PS2/backend/app/api/status.py:48` (P1)

**[P1] If re-planning fails, `/status` returns 500 and `/offline` hides the outage.**

`planner.plan_trip` raises `RuntimeError("no step-free walking route…")` and nothing here catches it.

Reproduced with Bedok exits A, B and C all out:
- `/status` → 500.
- `/offline` catches it and returns 200 with `status_snapshot: null`. `steps_plain[0]` is still "Walk … to Bedok MRT Exit B", a door whose lift is out, with no warning.

**Fix:** catch the error, keep the alerts, and set a critical "no step-free entrance available" overall. `/offline` should never serve steps with neither a snapshot nor a warning.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542860)

---

### F07 — `PS2/backend/app/api/status.py:55` (P1)

**[P1] A reroute is saved permanently and never undone.**

`refresh_plan` overwrites the stored plan with `rerouted: True`. Nothing ever re-plans back.

Reproduced: arm the Outram lift scenario, call `/status`, then turn the scenario off.
- `/status` says "Your usual route is clear".
- The stored and offline plan still use Exit 7, leave-by stays 5 min earlier, and `rerouted` stays `true`.

**Fix:** keep the original plan (or its inputs) and derive the effective plan from current alerts on each call. Base "moved you" on the diff from the original, not on whether *this* call re-planned.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542854)

---

### F08 — `PS2/backend/app/data.py:130` (P1)

**[P1] Outram "entrances" include other stations' exits, and exits with the same ref overwrite each other.**

`entrances_for("outram")` returns every entrance in the Outram bbox, keyed by the bare `ref`, so the last one wins. Measured against the committed graph:
- Outram Park **Exit 2** (16 m from the station, `wheelchair=yes`) is replaced by **Cantonment (CCL) Exit 2**, 888 m away, untagged.
- Outram Park **Exit 3** (107 m) is replaced by an unnamed Exit 3 at 462 m.
- `A`, `C`, `D`, `E`, `G` are **Chinatown's** exits.

Consequences:
- The real, tagged-accessible Exit 2 can never be chosen. (On its own this costs little: Outram Park Exit 1, also `wheelchair=yes`, survives and is equally far on foot from SGH.)
- When a reroute runs out of Outram exits, the plan says "Outram Park, Exit C", which is a Chinatown door about 560 m away (with `prefer_sheltered=True`, the API default; with it off, Exit A).
- An LTA outage can't block those refs, because they come out `unmatched` against LTA's 1–8.

Related (see `planner.py:104`): with only Exit 6 out, entrance choice picks the untagged Exit 7 (555 m) over the tagged Exit 1 (635 m).

**Fix:** tag each entrance with its station at build time by `name`. Use nearest station only for unnamed entrances, and not with a fixed radius: a 250 m cut-off would drop Outram Exit 6 (276 m), the default exit. Filter on that, and key by `(station, ref)`.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542801)

---

### F09 — `PS2/backend/app/scenario.py:18` (P1)

**[P1] The scenario flag is global, and it leaks into real scheduled pushes with no simulated label.**

`POST /api/scenario` needs no auth and flips a process-wide `_state`. `jobs.run_check → notify.check_trip` reads the same flag, and the push payload (`notify.py:48-57`) has no `source` or `simulated_note`.

Reproduced with `ewl_disruption` on, `check_trip` returns:
```
{'title': 'East-West Line delays towards Tuas Link', 'body': 'About 20 more minutes on your way to the hospital. …', 'severity': 'critical', …}
```
If the demo is left armed at 20:00, every subscriber whose trip falls in the check window gets that as a genuine alert. Nothing follows when the scenario is switched off, because there is no all-clear path. This is exactly the "mocked data presented as live" cap.

**Fix:** have the scheduled jobs ignore the scenario, or scope it to a demo trip or session. Carry `source` and `simulated_note` into the push payload whenever it is used.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542837)

---

### F10 — `PS2/backend/app/services/disruption.py:73` (P1)

**[P1] The delay figure can come from a different line's advisory (trap T6).**

The loop takes the first `additional travelling time of N min` found in any non-test message, whichever line it is about.

Reproduced:
- Content `"NSL - … 30 minutes … EWL - … 10 minutes"` → `delay_min=30` for her EWL trip.
- A newer separate NSL message also wins.

That wrong figure drives the push body and leave-earlier.

`score_rules.py` only tests `parse_delay()`, so it can't catch this. Example #6's note documents the first-figure behaviour, and its EWL clause is towards Pasir Ris, so for her westbound trip the right figure there is arguably none (see the direction comment on L66).

**Fix:** split `Content` on `<LINE> -` prefixes and only parse EWL clauses that match her direction.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542900)

---

### F11 — `PS2/backend/app/services/planner.py:104` (P1)

**[P1] `step_free: "yes"` is claimed for exits whose accessibility is unknown.**

- The rail leg is hardcoded `"yes"`.
- The walk legs and the summary (L144) check only `steps_used == 0`.
- `access` is always `status: "unknown"`.

Reproduced: with only Outram Exit 6 blocked she is sent to Exit 7 (`wheelchair=None`, 555 m) rather than the tagged Exit 1 (`wheelchair=yes`, 635 m). The summary still says step-free `"yes"` and "take the lift to street level". Plan §9 stage 4 records this reroute as verified.

The contract enum has `unknown` for exactly this (§6 limitation 5, D11).

**Fix:** return `"unknown"` (and soften the lift sentence) unless the chosen entrance is `wheelchair=yes`, and prefer tagged entrances over untagged ones when choosing.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542913)

---

### F12 — `PS2/backend/app/sources/base.py:97` (P1)

**[P1] Every 200 is recorded to the fixture, even if empty or invalid, and a write failure throws away a good fetch.**

- **Empty replies overwrite fixtures:** one live run after midnight turns `bus_84009.json` (10 services) into `[]`, because BusArrival returns nothing outside hours (T17). The offline demo then says "Not running now" forever. A 200 with an error body such as `{"code":24,"data":null}` caches and records `None` the same way (mechanism reproduced; not confirmed that data.gov.sg sends exactly this). Both reproduced with `httpx.MockTransport`.
- **Write failures discard good data:** `_record` is inside the `try`, so a `PermissionError` (read-only or container filesystem) turns a good 200 into `origin: "stale"`.
- **Runtime writes into the repo:** lift and alert fixtures are rewritten up to every 60 s while `/status` is polled, and bus fixtures on `/alternatives` calls after the 20 s TTL. This dirties the git tree during the demo.
- **Not atomic:** `write_text` is not atomic, and `_from_fixture` (L74) doesn't guard `json.loads`, so a truncated file turns the fallback into a 500.

**Fix:** record fixtures only behind an explicit flag or script, and only when the payload passes a per-source check. Write to a temp file then `os.replace`, and keep recording out of the `try`.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542967)

---

### F13 — `PS2/backend/scripts/verify_stepfree.py:51` (P1)

**[P1] `verify_stepfree.py` can PASS without checking anything. Its output is a claim going into WRITEUP.md.**

- **L50-51:** coordinate pairs that don't match a graph node are skipped with `continue`. A real staircase edge FAILs with exact coordinates, but PASSes when nudged by 1 cm.
- **L72-73:** legs without `station_code` / `exit_code` are skipped. With them stripped, the result is `('PASS', [])`.
- **L80:** `ok = tag == "yes" or not lift_out` passes any entrance with no matched outage: untagged, or even tagged `wheelchair=no` (the planner excludes those, so only a hand-built plan hits this). `station_only` / `unmatched` outages are ignored (L65).
- The steps check reads the same OSM edges the step-free router was built from, so it mostly checks itself.

Today's run does resolve 17/17 and 27/27 edges, so the current PASS is real, but nothing guards it.

**Fix:** FAIL on any unresolved pair or when zero entrances are checked, and print the checked counts. Require `wheelchair=yes` or (a lift near the exit and no matched or station-level outage).

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039543004)

---

### F14 — `PS2/backend/app/api/push.py:32` (P2)

**[P2] A push send blocks the event loop, and there is no timeout.**

`webpush()` is synchronous (it uses requests, and pywebpush passes `timeout=None`). It is called directly from `async def push_test` and `async def run_check`.

Reproduced: `/api/health` took 5.5 s while `/push/test` waited on a slow endpoint. An endpoint that never answers hangs the whole server, and with the SSRF above, an attacker chooses that endpoint.

**Fix:** `await asyncio.to_thread(webpush, ..., timeout=10)`.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542828)

---

### F15 — `PS2/backend/app/api/trips.py:26` (P2)

**[P2] Request validation gaps.**

All reproduced:
- `coord: []`, `[103.93]` or `[x, y, z]` → TypeError → plain-text 500.
- `buffer_min: -120` → leave 11:34 for a 10:30 appointment (200). `buffer_min: 1e12` → OverflowError 500.
- Appointments in 2001 or 9999 are accepted and stored. A date-only `"2026-09-21"` silently means midnight.
- `walking_pace: "sprint"` is accepted and stored in `preferences` (not echoed back), and silently planned as slow.

**Fix:** `conlist(float, min_length=2, max_length=2)` (NaN already gets a clean 400), `buffer_min: int = Field(15, ge=0, le=120)`, `walking_pace: Literal[...]`, and reject past or far-future appointments.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542943)

---

### F16 — `PS2/backend/app/api/trips.py:102` (P2)

**[P2] Address search returns 500 on network errors, and ignores fixtures mode.**

Only `OneMapAuthError` is caught. A connection error, timeout or 5xx from `raise_for_status` gives a 500 rather than `UPSTREAM_UNAVAILABLE`. With a token set, it also calls OneMap even when `PS2_USE_FIXTURES=1`. `onemap.pt_route` in alternatives ignores the flag too, but it's wrapped in `except Exception`, so there it costs a network call rather than a 500.

**Fix:** also catch `httpx.HTTPError` (and `ValueError` for a non-JSON body), and short-circuit OneMap in fixtures mode.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542949)

---

### F17 — `PS2/backend/app/data.py:125` (P2)

**[P2] Snapping uses the main component of the graph *with* stairs, not of the step-free graph (I11 is half done).**

`self.component` / `main_by_area` were built on the stairs-included graph. With stairs removed, Bedok's main component splits into 105 separate pieces (largest 12,077 nodes; the next 235, 77, …).

On a 25×25 grid over the Bedok bbox, 611 origins snap within 100 m, and 29 of those land on a small piece and get 400 "no step-free walking route". Example: `[103.937, 1.3197]` snaps 34 m to a small piece while sitting 42 m from the main step-free network.

**Fix:** compute components on `step_free` for `step_free=True`, or try the k nearest candidates until one routes.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542961)

---

### F18 — `PS2/backend/app/jobs.py:46` (P2)

**[P2] Marking a trip sent is all-or-nothing, so one bad subscription causes duplicate pushes. There is also no real retry.**

- **Duplicates:** if one of her subscriptions fails (an old browser, or a 404/410 expired endpoint), the digest is never marked. A later run with the same label that still covers the trip re-sends to the subscriptions that *did* succeed. Reproduced with 3 manual runs (3 identical pushes). On the real schedule a trip usually falls in only one 20:00 and one 07:00 window, so in practice this is about one extra duplicate.
- **Expired endpoints:** 404/410 subscriptions are never removed (`WebPushException.response.status_code` is never checked). They keep this failing forever and stay stored past trip deletion.
- **No targeted retry:** a failed 20:00 send is only retried by a later 20:00 run that still covers the trip, which usually doesn't exist. The 07:00 check (a separate label) does send on the day, so she isn't left without a warning, but "failures remain retryable" from the fix comment overstates it.
- **One error stops the run:** there is no try/except around `check_trip`. Low impact today: its only failure point is the shared lifts/alerts fetch, which already falls back to fixtures and would fail for every trip alike.

**Fix:** record sent state per `(trip, label, endpoint)`, delete subscriptions on 404/410, and wrap each trip's check. Add a short retry (for example a one-off job +10 min) if retry matters. Also claim the send atomically (`INSERT … ON CONFLICT DO NOTHING`) so two workers don't both send.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542865)

---

### F19 — `PS2/backend/app/jobs.py:53` (P2)

**[P2] The check windows don't match D3's wording, and the actual evening-before push can be skipped.**

- The "07:00 today" run uses `now+24h`, so it includes tomorrow's 06:30 appointment.
- The "20:00 evening before" run uses 36 h, so it reaches 08:00 two days ahead: a 07:30 appointment gets a push two evenings before.

Worse: `sent` is keyed on `(trip_id, "20:00")` with no date. For a Wed 07:30 appointment, Monday's 20:00 run sends the warning, then Tuesday's 20:00 run finds the same digest and skips it. The real evening-before push never fires.

The 36 h window is what plan §8 specifies, so the mismatch is with D3 and the "20:00 the evening before" label.

**Fix:** include the check date in the `sent` key, and compute calendar windows in SGT (07:00 → today until midnight; 20:00 → tomorrow).

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542871)

---

### F20 — `PS2/backend/app/jobs.py:70` (P2)

**[P2] Retention can run to about 48 h, not the 24 h promised in §8 commitment 1.**

- The sweep runs only at 03:00 (not on startup) and removes trips more than 24 h past the appointment. A 03:30 appointment survives the next day's sweep at 23.5 h and is removed at 47.5 h (reproduced with `sweep(now=…)`).
- `push_subs` rows are never swept, and keep dangling `trip_ids`.

**Fix:** sweep hourly and on startup, and drop subscriptions whose trips are all gone. Or reword the privacy statement.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542877)

---

### F21 — `PS2/backend/app/main.py:41` (P2)

**[P2] The error shape isn't always top-level, as the contract promises.**

This handler is registered for FastAPI's `HTTPException`, but routing raises Starlette's. Reproduced:
- Unknown routes return `{"detail":"Not Found"}`.
- A wrong method returns `{"detail":"Method Not Allowed"}`.
- Uncaught exceptions (see trips/status) return a text/plain 500.

**Fix:** register for `starlette.exceptions.HTTPException`, and add a catch-all `Exception` handler returning `{"error": {..., "retryable": true}}`.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542953)

---

### F22 — `PS2/backend/app/scenario.py:86` (P2)

**[P2] Recorded fixtures are labelled `source: "live"`.**

`_source: "live"` is stamped regardless of `fetched.origin`. With `PS2_USE_FIXTURES=1`, or on the automatic fallback when upstream fails, every lift row shows `source: "live"`. Each block carries `observed_at`, but there is no per-block `stale`; only the top-level flag says the data isn't current. Verified in fixture mode: sources `{'live'}` with `stale: true`.

The same applies to:
- `crowd.py:31` and `weather_policy.py:38`, which hardcode `"live"`.
- `alternatives.py:91`: the bus block has no `stale` or `observed_at`. With OneMap configured and service 2 timed, a day-old `bus_84039` fixture gives `eta_min: 0` and "The next bus has a wheelchair ramp". Without OneMap it gives "Not running now" instead. Either way, old data reads as current.

P2 rather than P1: fixtures are recorded real responses, not mock data, but they still shouldn't read as current.

**Fix:** keep `source` as `live`/`simulated` (contract §1 limits it to those). Add a per-block `stale` flag (contract rule 4) driven by `fetched.stale`/`fetched.origin`, add `observed_at` to the bus block, and don't compute a bus ETA from a fixture.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542848)

---

### F23 — `PS2/backend/app/services/alternatives.py:127` (P2)

**[P2] The bus option always says `step_free: "yes"`, and its live data describes now, not her departure.**

- `step_free` is `"yes"` even when `wheelchair_accessible` is `False` or `None`.
- `not_running` and `eta_min` come from the current `BusArrival` and ignore departure time. Reproduced: opening alternatives at 01:03 for a 15:00 trip says "Not running now; first bus 0530". Opened the evening before, the ETA is for a bus tonight.

**Fix:** derive `step_free` from `wheelchair_accessible` (`unknown` when `None`). Suppress live ETA and not-running when departure is more than about 30 min away.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542977)

---

### F24 — `PS2/backend/app/services/alternatives.py:202` (P2)

**[P2] Leave-earlier has no slack and can suggest a time that has already passed.**

- **No slack:** `arrival_at = arrive_late + (delay − shortfall)`, i.e. `arrive_late + buffer_min`, which lands within a minute of the appointment (the gap is only leave-by rounding). Reproduced: arrival 14:59:48 for a 15:00 appointment, while the text says "still in time".
- **Can be in the past:** `earlier` is never compared with now. With the 20-min replay, an 08:30 departure becomes "Leave at 08:25". A 35-min delay advised at 08:12 would say "Leave at 08:10 instead", which has already passed.

**Fix:** keep the buffer (shift by the full delay), and drop or reword the option when `earlier < now`.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542994)

---

### F25 — `PS2/backend/app/services/alternatives.py:245` (P2)

**[P2] The taxi stand is always the one at Outram Park.**

`_taxi_option(DEST_STATION)` is hardcoded. For a trip she hasn't started (she's still in Bedok, which is the main case for a pre-departure disruption), she is offered "Outram Rd outside Outram Park MRT Station, 32 m away". Reproduced.

This contradicts I7's own rule, "the station the current leg is heading to": before departure that is EW5 (Bedok), even though I7's worked example names EW16.

**Fix:** anchor on the origin station before departure.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542986)

---

### F26 — `PS2/backend/app/services/disruption.py:66` (P2)

**[P2] Direction is ignored, and an all-test-broadcast state is still reported as a disruption.**

- A segment with `Direction: "Pasir Ris"` (eastbound; she rides towards Tuas Link) is treated as hers: "… delays towards Pasir Ris", plus leave-earlier advice.
- When every message is a `Test :` broadcast but the segment is populated, a critical disruption is still returned.

Both reproduced.

**Fix:** only keep segments whose direction is `Tuas Link` or `Both`. When every message is a `Test :` broadcast but a segment is populated, don't drop it (T3 says to trust the segments). Downgrade to `warn` and don't show a delay figure.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542908)

---

### F27 — `PS2/backend/app/services/timing.py:52` (P2)

**[P2] Headway is looked up at the appointment hour, not the boarding hour. The nearest-hour fallback also invents service when no trains run.**

The lookup is here; the caller passing `appointment_at` is `planner.py:65`.

- **Wrong hour:** a Monday 08:40 appointment uses the 08h headway (2.5 min), but she boards around 07:39, when it is 5.0. The slow end is under-estimated by 2.5 min, which breaks "plan against the slow end".
- **No trains running:** the EW5 westbound tables only have hours 5–23. A 01:30 appointment returns "leave 00:20" using the nearest hour (5). A 05:30 appointment matches hour 5 exactly but plans "leave 04:20", boarding in hour 4 when no trains run.
- **Holidays:** public holidays use the weekday table.

**Fix:** estimate the boarding time, then look up that hour and day type (one iteration is enough). Reject or warn when that hour has no service, and add a PH list mapped to `sunday_ph`.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542936)

---

### F28 — `PS2/backend/app/services/weather_policy.py:25` (P2)

**[P2] Rain never changes the route. The label is only true because of the default preference.**

The planner never reads the weather; shelter comes only from `preferences.prefer_sheltered`, which the API defaults to `True` (`trips.py:20`). With default preferences the walk is already shelter-weighted, so "We have kept your walk covered" holds by accident. It is false for `prefer_sheltered: false`.

The real gap: D9, contract §3 and plan §1 capability 5 describe rain → sheltered route, and a judge can't observe that. Contract §3's "`sheltered_pct` shown only when rain is forecast" isn't wired in either.

**Fix:** make `rain_expected` force `prefer_sheltered` when planning or re-planning, or change the claim and this sentence.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542998)

---

### F29 — `PS2/backend/app/sources/base.py:88` (P2)

**[P2] During an outage, callers queue behind the lock and every request re-hits upstream.**

- The lock is held for the whole upstream call (20 s timeout).
- A failure doesn't update `_entry.at`, so the next request retries immediately.

Reproduced: with a 1 s hang, 5 concurrent callers returned at 1, 2, 3, 4 and 5 s. `/status` makes 4 source calls in a row, so a real outage can take a single request past 80 s. That's the opposite of "serve stale".

Minor: the lock is created per source at import (L58). Under one uvicorn loop that's fine, but once contended in one loop it raises `RuntimeError` if contended in another (e.g. tests or scripts that call `asyncio.run` repeatedly).

**Fix:** on failure, back off before the next retry. Serve the stale value to waiters instead of queuing, and shorten the timeout to about 5 s.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542972)

---

### F30 — `PS2/backend/app/store.py:60` (P2)

**[P2] Trip IDs are 4 characters and act as the only access control.**

`token_urlsafe(4)` with `-` and `_` stripped, cut to 4 characters: about 14.8M values, and about 0.03% come out as 3 characters.
- GET, DELETE, status and offline need nothing but the ID. GET and offline return her home coordinate.
- A collision raises `IntegrityError` → 500 (unlikely at this scale).

**Fix:** use `secrets.token_urlsafe(16)` and retry on collision.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542884)

---

### F31 — `PS2/backend/app/store.py:113` (P2)

**[P2] Turning notifications off can leave trips on the server (privacy commitment 1).**

`INSERT OR REPLACE` overwrites `trip_ids`, and the default is `[]`. If she subscribes for trip A and later re-subscribes with trip B:
- A is unlinked and gets no warnings.
- `DELETE /push/subscribe` leaves A in place.

Reproduced. A is still swept 24 h after its appointment, but not "immediately" as promised.

**Fix:** merge `trip_ids` on upsert, or link trips to the subscription or device when they are created.

<sub>Edited after independent re-verification: corrected details above.</sub>

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542892)

---

### F32 — `PS2/backend/scripts/build_data.py:100` (P2)

**[P2] A failed download puts the presigned S3 URL, with its token, in the error message.**

`raise_for_status()` includes the full URL, `X-Amz-Security-Token=…`, which contradicts the comment on L99. Reproduced with a 403: *"Client error '403 Forbidden' for url 'https://…X-Amz-Security-Token=…'"*. Tracebacks get pasted into chat and CI logs.

**Fix:** check `blob.status_code` and `sys.exit(f"{endpoint}: download failed ({blob.status_code})")`.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039543011)

---

### F33 — `PS2/backend/app/services/planner.py:123` (P3)

**[P3] The last walk leg's geometry runs backwards.**

`walk_out` is routed SGH → exit (L53), but the leg says `from` exit, `to` SGH. A frontend animating or snapping progress along the line will run backwards.

**Fix:** reverse `walk_out.coords`.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039542925)

---

### F34 — `PS2/backend/scripts/build_data.py:151` (P3)

**[P3] One failed BusStops fetch breaks every later build.**

`bus_routes.json` is written before BusStops is fetched, and the skip check only looks at `bus_routes.json`. If BusStops fails once, every later `--all` run skips the fetch and `build_bus_options` crashes with `FileNotFoundError`. Reproduced.

**Fix:** check both files, and write both only after both fetches succeed. The Overpass and GTFS cache writes have the same non-atomic pattern.

[comment link](https://github.com/Jiackary/nebulax_lta/pull/1#discussion_r4039543022)

---

## Review summary body (as posted)

## Review of `6405e32`: correctness, security and docs

<sub>Edited after independent re-verification of every claim: corrected numbers and wording, fixed two suggested fixes, and re-graded three severities (two P1 → P2, one P3 → P2).</sub>

I split this review across five parallel passes: push/scheduler, planner/timing, lifts/disruption/alternatives, sources/pipeline, and docs vs code. The headline findings were re-run against the PR head in fixture mode with a scratch DB. Inline comments carry the file:line detail and repro notes. **No code changes were made.**

### Were the previous four findings fixed?
| Prior finding | Status |
|---|---|
| Push sent to every subscription | ✅ Fixed. `jobs.py:37` and `push.py:89` filter by `trip_ids`. |
| Digest marked before delivery | ⚠️ Fixed narrowly. Nothing is marked on failure, but a partial failure can re-send to working subscriptions, and there is no targeted retry (the 07:00 check still sends on the day). Inline on `jobs.py:46`. |
| Naive timestamps depend on the server TZ | ✅ Fixed. Naive → SGT, and aware → converted. |
| Origin silently snapped to Bedok | ✅ Fixed (bbox + 100 m haversine). Remaining gaps: snapping uses the stairs-included component, and coords aren't validated (inline). |

Tests pass (9), `score_rules.py` gives 16/16, `verify_stepfree.py` gives PASS. **No secrets are committed** (searched the diff, history and fixtures).

### Must fix before merge
**P0: route safety** (false "all clear" for a step-free persona)
- [ ] A lift serving two exits (`Exits 5/6`) only blocks the first exit. Her Exit 6 stays in the plan (`lifts.py:75`). This format hasn't been seen in live rows yet.
- [ ] "Your route does not use it" is shown for `unmatched` and `station_only` outages at her own station (`status.py:127`).

**P1**
- [ ] Outram entrances mix in Chinatown and Cantonment exits. The real accessible Exit 2 is overwritten by Cantonment's (`data.py:130`).
- [ ] `DELETE /api/push/subscribe` with no endpoint wipes every subscription and trip (`push.py:60`).
- [ ] `/push/test` with no `trip_id` acts on another user's trip and leaks its ID, and through it her home coordinate (`push.py:72`).
- [ ] SSRF via the subscription endpoint, with the upstream response returned to the caller (`push.py:52`).
- [ ] Scenario flag is global. An armed demo sends unlabelled simulated disruptions to real subscribers at 20:00 (`scenario.py:18`).
- [ ] Reroute is saved permanently and never reverted (`status.py:55`). A failed re-plan gives a 500 on `/status`, and `/offline` serves steps through a blocked door (`status.py:48`).
- [ ] Delay figure taken from another line's advisory (`disruption.py:73`).
- [ ] `step_free: "yes"` claimed for exits of unknown accessibility (`planner.py:104`).
- [ ] Empty or invalid upstream 200s overwrite committed fixtures, and fixtures are rewritten into the repo at runtime (`base.py:97`).
- [ ] `verify_stepfree.py` can pass vacuously (`verify_stepfree.py:51`).

**P2, worth fixing alongside**
- [ ] Recorded fixture and fallback data carry `source: "live"` with no per-block `stale` (`scenario.py:86`, crowd, weather, bus).
- [ ] Per-trip all-or-nothing marking can duplicate pushes, 404/410 subscriptions are never pruned, and there is no targeted retry (`jobs.py:46`).
- [ ] The 20:00 dedupe key has no date, so the actual evening-before push can be skipped (`jobs.py:53`).

### Docs vs code (not inline; the lines are mostly unchanged context)
**P1**
- [ ] **Stage 3/4 numbers mix two configurations.** The planner and `verify_stepfree.py` default to `prefer_sheltered=False`, but `POST /api/trips` defaults it to `True`.
  - With `False`: 696 m, **38%** sheltered, reroute +142 m / 4 min earlier.
  - With `True` (what the API serves): **707 m**, 60%, reroute **+171 m / 5 min** (09:19 → 09:14).
  - So "696 m, 60% sheltered" (§9 stage 3) and "+143 m, 4 min" (stage 4) each mix the two runs, and stage 4 contradicts I16. Pick one default and re-measure `PS2_BACKEND_PLAN.md` §9, I12, I17 and the `config.py:41` comment.
- [ ] `backend/README.md:96`: "Step-free route costs 13 m over the unrestricted one" isn't computed by `verify_stepfree.py`. It was measured from the old Blk 123 home (I11).
- [ ] **The privacy statement is wrong about OneMap.** I9 says OneMap sees trip endpoints "only in the offline verification script", but when `ONEMAP_TOKEN` is set, `alternatives.py:60` sends her home coordinate to OneMap on every `/alternatives` call. README:16's "address search only" is wrong too. Fix I9, the README and decision record §8.
- [ ] Privacy §8 lists start and end coordinates, appointment date and time, and the stations, exits and lifts. The server also stores the address label, preferences and full walking geometry from home, and `push_subs` rows are never swept. Update §8 or reduce what's stored.

**P2**
- [ ] **Contract drift not recorded in §10.**
  - `TripPlan.observed_at` is never emitted.
  - `access.lift_id` is absent, and `status` is always `unknown`.
  - `/alternatives` returns bus and taxi options with no disruption.
  - `delta_min` is null for taxi (unrecorded), and for bus unless OneMap timed it (implied by I15's null `duration_min`).
  - `leave_later` never actually changes the leave time.
  - Undocumented fields and parameters:
    - options: `leave_by`, `leave_by_label`, `timing_basis`
    - push: `trip_id` on `/push/test`, `sent_at` and `digest` in the payload, `?endpoint=` on `DELETE /push/subscribe`
    - trips: `preferences.buffer_min`
  - `weather.area` is no longer emitted (§10 records the added `areas[]`, not the removal).
  - `/openapi.json` has no response models, and the 422 is documented as FastAPI's `{detail}` shape.
- [ ] Contract §8 shows one GET/POST response shape (nested `scenarios`) and never documents the POST body. Posting that nested shape returns 200 and changes nothing; only the README's flat body works. Also, `{"enabled": false}` can't switch the demo off while any sub-scenario is true (`scenario.py:74`).
- [ ] The D7 hand-checked lift↔exit table for EW5/EW16 (plan §4:303) doesn't exist. `data/handchecked/` holds only parser examples, and 6 of the 10 `LiftDesc` rows are hand-written although the file says "Every row is real".
- [ ] `PS2_INDEX.md`:
  - L8 still says "No implementation started".
  - L10 commits `/home/zachary/...`.
  - S13 says "eight issues (I1–I8)", but there are 17.
  - S14 says "before the backend exists".
- [ ] Contract §3 example: the origin was updated, but the summary still shows 09:24, 46 min, 41–51 and 78% (measured: 09:19, 45–56, 60%). The "0–5 min" basis is superseded in §10, but the example wasn't refreshed.

**P3**
- [ ] Plan §4 module layout:
  - lists `api/scenario.py`, but the routes live in `status.py`
  - omits `api/offline.py`, `services/{walking,notify,alternatives}.py`, `sources/base.py`, `data.py`, `score_rules.py` and `gen_vapid.py`
  - §5 says 613 exits; the real count is 603.
- [ ] README:
  - "paste your two keys", but `.env.example` has five, and without the VAPID keys `/push/key` returns 503
  - `PS2_DB` is undocumented
  - "four real lift outages stay live" only holds for the committed fixture (recorded 18 Sep 00:09 SGT)

### Minor / hygiene (P3)
- `leave_by` is derived from the unrounded slow end and truncated, so with `prefer_sheltered=True` (the API default) a 10:30 appointment with `range_min` [45, 55] shows 09:19, not 09:20, and the window ends on odd seconds (`timing.py:85`). Either derive from `range_min[1]` as the contract says, or update the contract.
- The snap distance (up to 100 m) isn't added to walk distance or time (`walking.py:88`). Entrance choice uses raw distance even when `prefer_sheltered` is on (`walking.py:111`). The 100 m snap cap only applies on the origin side (`planner.py:60`); the destination snap is uncapped.
- **Scheduler and digest:**
  - Every uvicorn worker starts its own scheduler, and `was_sent` → send → `mark_sent` isn't atomic, so `--workers 2` gives duplicate pushes.
  - The digest covers only title and body, so a second on-route outage produces no new push while the first stays listed first, and lift changes are ignored entirely during a disruption.
- `datamall.py:55-58`: `_fetch_crowd` is dead and broken. Delete it.
- **Reproducibility and repo hygiene:**
  - `requirements.txt` has only `>=` bounds. Pin versions or add a lock file.
  - `built_at=now()` changes the 4.9 MB `stepfree_graph.json` on every rebuild.
  - `.gitignore` misses `*.sqlite3-journal` and `.DS_Store`.
  - `PS2_USE_FIXTURES=1` still falls through to the network when a fixture is missing, and OneMap ignores the flag.

### Test gaps
Every push test in `test_push_delivery.py` stubs `send_push`, and the scheduled-check tests also stub `was_sent`/`mark_sent`. Nothing exercises:
- real SQLite dedupe, or partial-failure duplicates
- 404/410 cleanup
- `trip_ids` overwrite on re-subscribe, or `sweep()`
- multi-exit or unmatched lifts against the route
- direction or bundled-line disruption parsing
- the fixture-vs-live `source` label

`score_rules.py` never runs `assess()`, `affects_route` or `blocked_exits`, so the dangerous paths above pass 16/16. Please add held cases with expected *route outcomes*, not just parser outputs.

