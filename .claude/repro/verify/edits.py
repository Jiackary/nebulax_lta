import json
SP="/private/tmp/claude-501/-Users-rayden-Desktop-projects-ltaxnebula-nebulax-lta/0c669e66-ef51-4cd3-b7af-0894f8a4d718/scratchpad/verify/"
local=json.load(open(SP+"review.json"))
bodies={f'{c["path"].replace("PS2/backend/","")}:{c["line"]}':c["body"] for c in local["comments"]}
orig=dict(bodies)
NOTE="\n\n<sub>Edited after independent re-verification: corrected details above.</sub>"

def rep(key, old, new):
    b=bodies[key]; n=b.count(old)
    assert n==1, (key, n, old[:60])
    bodies[key]=b.replace(old,new)

# lifts.py:75
rep("app/services/lifts.py:75", "**Fix:** keep every parsed exit",
 "Caveat: all four live rows captured so far name a single exit. The only `Exits A/B` example (#7 in `lift_desc_examples.json`) is hand-written, so this format hasn't been seen live yet. `score_rules.py` checks `parsed_exits` and `resolution` but never `exit_code`, which is why #7 passes despite the bug.\n\n**Fix:** keep every parsed exit")

# status.py:127
rep("app/api/status.py:127", "- `station_only` rows. A concourse↔platform lift at her station is on *every* step-free path.",
 "- `station_only` rows. A concourse↔platform lift at her station may well be on her step-free path, and we can't tell. (Outram Park is a three-line interchange: NE3 and TE17 rows also resolve to EW16, so it could be an NEL- or TEL-side lift.)")
rep("app/api/status.py:127", "For `unmatched` and `station_only` at EW5/EW16, raise a check-before-you-go warning.",
 "For `unmatched` and `station_only` at EW5/EW16, say it *may* affect her route and raise a check-before-you-go warning.")

# data.py:130
rep("app/data.py:130", "884 m away, untagged.", "888 m away, untagged.")
rep("app/data.py:130", "- The real, tagged-accessible Exit 2 can never be chosen.",
 "- The real, tagged-accessible Exit 2 can never be chosen. (On its own this costs little: Outram Park Exit 1, also `wheelchair=yes`, survives and is equally far on foot from SGH.)")
rep("app/data.py:130", "the plan says \"Outram Park, Exit C\", which is a Chinatown door about 560 m away.",
 "the plan says \"Outram Park, Exit C\", which is a Chinatown door about 560 m away (with `prefer_sheltered=True`, the API default; with it off, Exit A).")
rep("app/data.py:130", "**Fix:** tag each entrance with its station at build time (by `name`, or nearest station within about 250 m). Filter on that, and key by `(station, ref)`.",
 "Related (see `planner.py:104`): with only Exit 6 out, entrance choice picks the untagged Exit 7 (555 m) over the tagged Exit 1 (635 m).\n\n**Fix:** tag each entrance with its station at build time by `name`. Use nearest station only for unnamed entrances, and not with a fixed radius: a 250 m cut-off would drop Outram Exit 6 (276 m), the default exit. Filter on that, and key by `(station, ref)`.")

# push.py:60
rep("app/api/push.py:60", "It has no auth, and CORS is `*`.", "It has no auth.")
rep("app/api/push.py:60", "Any web page she visits could do this.", "Any HTTP client can do this.")

# push.py:52
rep("app/api/push.py:52", 'Reproduced against a local server: `"Push failed: 404 Not Found\\nResponse body:INTERNAL-ADMIN-PAGE-CONTENT"`. The server\'s VAPID-signed JWT also goes to that host.',
 'Reproduced against a local server: `"WebPushException: Push failed: 404 Not Found\\nResponse body:INTERNAL-ADMIN-PAGE-CONTENT, Response INTERNAL-ADMIN-PAGE-CONTENT"`.\n\n- The body is echoed when the target returns a status above 202. For connection errors, the `requests` error text still reveals whether a host or port is open.\n- A VAPID JWT is sent too, but its `aud` is the target\'s own origin, so it can\'t be replayed against real push services.\n- Preconditions: `VAPID_PRIVATE_KEY` is set, and the attacker supplies well-formed `p256dh`/`auth` keys (easy to generate).')

# scenario.py:18
rep("app/scenario.py:18", "If the demo is left armed at 20:00, every real subscriber gets that as a genuine alert. `mark_sent` then stops any correction being sent.",
 "If the demo is left armed at 20:00, every subscriber whose trip falls in the check window gets that as a genuine alert. Nothing follows when the scenario is switched off, because there is no all-clear path.")

# scenario.py:86
k="app/scenario.py:86"
rep(k, "**[P1] Recorded fixtures are labelled `source: \"live\"`.**", "**[P2] Recorded fixtures are labelled `source: \"live\"`.**")
rep(k, "Only the top-level `stale` flag says otherwise. Verified in fixture mode: sources `{'live'}` with `stale: true`.",
 "Each block carries `observed_at`, but there is no per-block `stale`; only the top-level flag says the data isn't current. Verified in fixture mode: sources `{'live'}` with `stale: true`.")
rep(k, "- `alternatives.py:91`: a day-old `bus_*` fixture gives `eta_min: 0` and \"The next bus has a wheelchair ramp\", with no `stale` or `observed_at`.",
 "- `alternatives.py:91`: the bus block has no `stale` or `observed_at`. With OneMap configured and service 2 timed, a day-old `bus_84039` fixture gives `eta_min: 0` and \"The next bus has a wheelchair ramp\". Without OneMap it gives \"Not running now\" instead. Either way, old data reads as current.")
rep(k, "**Fix:** set `source` from `fetched.origin` (`live` / `stale` / `fixture`), add `stale` and `observed_at` to each block (contract rule 4), and don't compute a bus ETA from a fixture.",
 "P2 rather than P1: fixtures are recorded real responses, not mock data, but they still shouldn't read as current.\n\n**Fix:** keep `source` as `live`/`simulated` (contract §1 limits it to those). Add a per-block `stale` flag (contract rule 4) driven by `fetched.stale`/`fetched.origin`, add `observed_at` to the bus block, and don't compute a bus ETA from a fixture.")

# jobs.py:46
k="app/jobs.py:46"
rep(k, "**[P1] Marking a trip sent", "**[P2] Marking a trip sent")
rep(k, "Every later run with the same label re-sends to the subscriptions that *did* succeed. Reproduced: 3 runs gave 3 identical pushes to the working endpoint.",
 "A later run with the same label that still covers the trip re-sends to the subscriptions that *did* succeed. Reproduced with 3 manual runs (3 identical pushes). On the real schedule a trip usually falls in only one 20:00 and one 07:00 window, so in practice this is about one extra duplicate.")
rep(k, "- **No real retry:** the only retry is the next run with the same label, 24 h later, which for a 10:30 appointment is after the appointment. So \"failures remain retryable\" from the fix comment doesn't hold in practice.",
 "- **No targeted retry:** a failed 20:00 send is only retried by a later 20:00 run that still covers the trip, which usually doesn't exist. The 07:00 check (a separate label) does send on the day, so she isn't left without a warning, but \"failures remain retryable\" from the fix comment overstates it.")
rep(k, "- **One error stops the run:** there is no try/except around `check_trip`.",
 "- **One error stops the run:** there is no try/except around `check_trip`. Low impact today: its only failure point is the shared lifts/alerts fetch, which already falls back to fixtures and would fail for every trip alike.")

# jobs.py:53
k="app/jobs.py:53"
rep(k, "**[P3] The check windows don't match D3's wording.**", "**[P2] The check windows don't match D3's wording, and the actual evening-before push can be skipped.**")
rep(k, "**Fix:** compute calendar windows",
 "Worse: `sent` is keyed on `(trip_id, \"20:00\")` with no date. For a Wed 07:30 appointment, Monday's 20:00 run sends the warning, then Tuesday's 20:00 run finds the same digest and skips it. The real evening-before push never fires.\n\nThe 36 h window is what plan §8 specifies, so the mismatch is with D3 and the \"20:00 the evening before\" label.\n\n**Fix:** include the check date in the `sent` key, and compute calendar windows")

# store.py:60
rep("app/store.py:60", "- GET, DELETE, status and offline need nothing but the ID, and they return her home coordinate.\n- A collision raises `IntegrityError` → 500.",
 "- GET, DELETE, status and offline need nothing but the ID. GET and offline return her home coordinate.\n- A collision raises `IntegrityError` → 500 (unlikely at this scale).")

# store.py:113
rep("app/store.py:113", "Reproduced.", "Reproduced. A is still swept 24 h after its appointment, but not \"immediately\" as promised.")

# disruption.py:73
rep("app/services/disruption.py:73", "`score_rules.py` message example #6 expects 30 for the bundled NSL/EWL content, so the check locks this bug in.",
 "`score_rules.py` only tests `parse_delay()`, so it can't catch this. Example #6's note documents the first-figure behaviour, and its EWL clause is towards Pasir Ris, so for her westbound trip the right figure there is arguably none (see the direction comment on L66).")
rep("app/services/disruption.py:73", "and only parse EWL clauses.", "and only parse EWL clauses that match her direction.")

# disruption.py:66
rep("app/services/disruption.py:66", "Also, when `_messages()` is empty but raw messages exist and every one is a test, return None.",
 "When every message is a `Test :` broadcast but a segment is populated, don't drop it (T3 says to trust the segments). Downgrade to `warn` and don't show a delay figure.")

# planner.py:104
rep("app/services/planner.py:104", "Reproduced: with Outram exits 4 and 6 blocked she is sent to Exit 7 (`wheelchair=None`). The summary still says step-free `\"yes\"` and \"take the lift to street level\".",
 "Reproduced: with only Outram Exit 6 blocked she is sent to Exit 7 (`wheelchair=None`, 555 m) rather than the tagged Exit 1 (`wheelchair=yes`, 635 m). The summary still says step-free `\"yes\"` and \"take the lift to street level\". Plan §9 stage 4 records this reroute as verified.")
rep("app/services/planner.py:104", "unless the chosen entrance is `wheelchair=yes`.",
 "unless the chosen entrance is `wheelchair=yes`, and prefer tagged entrances over untagged ones when choosing.")

# timing.py:52
k="app/services/timing.py:52"
rep(k, "- **Wrong hour:** a Monday", "The lookup is here; the caller passing `appointment_at` is `planner.py:65`.\n\n- **Wrong hour:** a Monday")
rep(k, "The slow end is under-estimated by about 3 min,", "The slow end is under-estimated by 2.5 min,")
rep(k, "- **No trains running:** a 01:30 or 05:30 appointment returns a normal plan (\"leave 00:20\" / \"04:20\") using the nearest hour's headway.",
 "- **No trains running:** the EW5 westbound tables only have hours 5–23. A 01:30 appointment returns \"leave 00:20\" using the nearest hour (5). A 05:30 appointment matches hour 5 exactly but plans \"leave 04:20\", boarding in hour 4 when no trains run.")

# trips.py:26
k="app/api/trips.py:26"
rep(k, "- `walking_pace: \"sprint\"` is accepted, stored and echoed back, but planned as slow.",
 "- `walking_pace: \"sprint\"` is accepted and stored in `preferences` (not echoed back), and silently planned as slow.")
rep(k, "`conlist(float, min_length=2, max_length=2)` with finite values,", "`conlist(float, min_length=2, max_length=2)` (NaN already gets a clean 400),")

# trips.py:102
k="app/api/trips.py:102"
rep(k, "it also calls OneMap even when `PS2_USE_FIXTURES=1`, and so does `onemap.pt_route` in alternatives.",
 "it also calls OneMap even when `PS2_USE_FIXTURES=1`. `onemap.pt_route` in alternatives ignores the flag too, but it's wrapped in `except Exception`, so there it costs a network call rather than a 500.")
rep(k, "**Fix:** also catch `httpx.HTTPError`,", "**Fix:** also catch `httpx.HTTPError` (and `ValueError` for a non-JSON body),")

# data.py:125
k="app/data.py:125"
rep(k, "29 of 625 grid origins with a snap under 100 m land on a small piece and get 400 \"no step-free walking route\". Example: `[103.937, 1.3197]`, 42 m from the main step-free network.",
 "On a 25×25 grid over the Bedok bbox, 611 origins snap within 100 m, and 29 of those land on a small piece and get 400 \"no step-free walking route\". Example: `[103.937, 1.3197]` snaps 34 m to a small piece while sitting 42 m from the main step-free network.")

# base.py:97
k="app/sources/base.py:97"
rep(k, "data.gov.sg `{\"code\":24,\"data\":null}` caches and records `None` the same way.",
 "A 200 with an error body such as `{\"code\":24,\"data\":null}` caches and records `None` the same way (mechanism reproduced; not confirmed that data.gov.sg sends exactly this).")
rep(k, "- **Runtime writes into the repo:** the bus fixture is rewritten every 20 s, which dirties the git tree during the demo.",
 "- **Runtime writes into the repo:** lift and alert fixtures are rewritten up to every 60 s while `/status` is polled, and bus fixtures on `/alternatives` calls after the 20 s TTL. This dirties the git tree during the demo.")

# base.py:88
rep("app/sources/base.py:88", "Also, `asyncio.Lock()` is created at import (L58) and shared across event loops.",
 "Minor: the lock is created per source at import (L58). Under one uvicorn loop that's fine, but once contended in one loop it raises `RuntimeError` if contended in another (e.g. tests or scripts that call `asyncio.run` repeatedly).")

# alternatives.py:127
k="app/services/alternatives.py:127"
rep(k, "**[P2] The bus option always says `step_free: \"yes\"`, and its live data is measured against now, not her departure.**",
 "**[P2] The bus option always says `step_free: \"yes\"`, and its live data describes now, not her departure.**")
rep(k, "- At the 20:00 or 01:00 check, \"Not running now; first bus 0530\" and `eta_min` describe *now*, not tomorrow's departure. Reproduced for a 15:00 trip checked at 01:03.",
 "- `not_running` and `eta_min` come from the current `BusArrival` and ignore departure time. Reproduced: opening alternatives at 01:03 for a 15:00 trip says \"Not running now; first bus 0530\". Opened the evening before, the ETA is for a bus tonight.")

# alternatives.py:245
rep("app/services/alternatives.py:245", "I7's \"the station the current leg is heading to\" doesn't fit here.",
 "This contradicts I7's own rule, \"the station the current leg is heading to\": before departure that is EW5 (Bedok), even though I7's worked example names EW16.")

# alternatives.py:202
k="app/services/alternatives.py:202"
rep(k, "- **No slack:** `arrival_at = arrive_late + shortfall`, which is exactly the appointment time. Reproduced: arrival 14:59:03 for a 15:00 appointment, while the text says \"still in time\".",
 "- **No slack:** `arrival_at = arrive_late + (delay − shortfall)`, i.e. `arrive_late + buffer_min`, which lands within a minute of the appointment (the gap is only leave-by rounding). Reproduced: arrival 14:59:48 for a 15:00 appointment, while the text says \"still in time\".")
rep(k, "- **Already past:** `earlier` is never compared with now. An 08:12 advisory for an 08:30 departure gives \"Leave at 08:10 instead\".",
 "- **Can be in the past:** `earlier` is never compared with now. With the 20-min replay, an 08:30 departure becomes \"Leave at 08:25\". A 35-min delay advised at 08:12 would say \"Leave at 08:10 instead\", which has already passed.")

# weather_policy.py:25 (full rewrite)
bodies["app/services/weather_policy.py:25"] = """**[P2] Rain never changes the route. The label is only true because of the default preference.**

The planner never reads the weather; shelter comes only from `preferences.prefer_sheltered`, which the API defaults to `True` (`trips.py:20`). With default preferences the walk is already shelter-weighted, so "We have kept your walk covered" holds by accident. It is false for `prefer_sheltered: false`.

The real gap: D9, contract §3 and plan §1 capability 5 describe rain → sheltered route, and a judge can't observe that. Contract §3's "`sheltered_pct` shown only when rain is forecast" isn't wired in either.

**Fix:** make `rain_expected` force `prefer_sheltered` when planning or re-planning, or change the claim and this sentence."""

# verify_stepfree.py:51
rep("scripts/verify_stepfree.py:51", "passes any untagged entrance, including one with no lift at all.",
 "passes any entrance with no matched outage: untagged, or even tagged `wheelchair=no` (the planner excludes those, so only a hand-built plan hits this).")

for k in bodies:
    if bodies[k]!=orig[k]:
        bodies[k]+=NOTE

# ---- review body ----
body=local["body"]
def rb(old,new):
    global body
    n=body.count(old); assert n==1,(n,old[:70]); body=body.replace(old,new)

rb("## Review of `6405e32`: correctness, security and docs\n",
   "## Review of `6405e32`: correctness, security and docs\n\n<sub>Edited after independent re-verification of every claim: corrected numbers and wording, fixed two suggested fixes, and re-graded three severities (two P1 → P2, one P3 → P2).</sub>\n")
rb("| ⚠️ Fixed narrowly. Nothing is marked on failure, but one bad subscription now causes **duplicate** pushes, and there is no retry before the appointment (inline on `jobs.py:46`). |",
   "| ⚠️ Fixed narrowly. Nothing is marked on failure, but a partial failure can re-send to working subscriptions, and there is no targeted retry (the 07:00 check still sends on the day). Inline on `jobs.py:46`. |")
rb("- [ ] A lift serving two exits (`Exits 5/6`) only blocks the first exit. Her Exit 6 stays in the plan (`lifts.py:75`).",
   "- [ ] A lift serving two exits (`Exits 5/6`) only blocks the first exit. Her Exit 6 stays in the plan (`lifts.py:75`). This format hasn't been seen in live rows yet.")
rb("- [ ] Fixture and fallback data are labelled `source: \"live\"`, which risks the rubric cap (`scenario.py:86`, crowd, weather, bus).\n", "")
rb("- [ ] Per-trip all-or-nothing marking gives duplicate pushes, 404/410 subscriptions are never pruned, and there is no real retry (`jobs.py:46`).\n", "")
rb("- [ ] Delay figure taken from another line's advisory (`disruption.py:73`). `score_rules` message #6 locks the bug in.",
   "- [ ] Delay figure taken from another line's advisory (`disruption.py:73`).")
rb("- [ ] `verify_stepfree.py` can pass vacuously (`verify_stepfree.py:51`).\n",
   "- [ ] `verify_stepfree.py` can pass vacuously (`verify_stepfree.py:51`).\n\n**P2, worth fixing alongside**\n- [ ] Recorded fixture and fallback data carry `source: \"live\"` with no per-block `stale` (`scenario.py:86`, crowd, weather, bus).\n- [ ] Per-trip all-or-nothing marking can duplicate pushes, 404/410 subscriptions are never pruned, and there is no targeted retry (`jobs.py:46`).\n- [ ] The 20:00 dedupe key has no date, so the actual evening-before push can be skipped (`jobs.py:53`).\n")
rb("but `alternatives.py:60` sends her home coordinate to OneMap on every `/alternatives` call. Fix I9 and decision record §8.",
   "but when `ONEMAP_TOKEN` is set, `alternatives.py:60` sends her home coordinate to OneMap on every `/alternatives` call. README:16's \"address search only\" is wrong too. Fix I9, the README and decision record §8.")
rb("- [ ] Privacy §8 lists only coordinates, stations, exits and lifts.",
   "- [ ] Privacy §8 lists start and end coordinates, appointment date and time, and the stations, exits and lifts.")
rb("  - `delta_min` is null for taxi, and for bus unless OneMap timed it.",
   "  - `delta_min` is null for taxi (unrecorded), and for bus unless OneMap timed it (implied by I15's null `duration_min`).")
rb("  - `weather.areas[]`, not `area`.\n", "  - `weather.area` is no longer emitted (§10 records the added `areas[]`, not the removal).\n")
rb("- [ ] Contract §8 shows a nested `{\"scenarios\":{…}}` POST body. That body returns 200 and changes nothing; the README's flat body is the one that works.",
   "- [ ] Contract §8 shows one GET/POST response shape (nested `scenarios`) and never documents the POST body. Posting that nested shape returns 200 and changes nothing; only the README's flat body works.")
rb("- [ ] Contract §3 example: the origin was updated, but the summary still shows 09:24, 46 min, 41–51, 78% and \"0–5 min\". §5 still shows only `leave_later`.",
   "- [ ] Contract §3 example: the origin was updated, but the summary still shows 09:24, 46 min, 41–51 and 78% (measured: 09:19, 45–56, 60%). The \"0–5 min\" basis is superseded in §10, but the example wasn't refreshed.")
rb("\"four real lift outages stay live\" only holds for the 17 Sep capture",
   "\"four real lift outages stay live\" only holds for the committed fixture (recorded 18 Sep 00:09 SGT)")
rb("- `leave_by` is derived from the unrounded slow end and truncated, so 10:30 − 15 − 55 shows 09:19, not 09:20,",
   "- `leave_by` is derived from the unrounded slow end and truncated, so with `prefer_sheltered=True` (the API default) a 10:30 appointment with `range_min` [45, 55] shows 09:19, not 09:20,")
rb("Entrance choice uses raw distance even when `prefer_sheltered` is on (`walking.py:111`).",
   "Entrance choice uses raw distance even when `prefer_sheltered` is on (`walking.py:111`). The 100 m snap cap only applies on the origin side (`planner.py:60`); the destination snap is uncapped.")
rb("  - The digest covers only title and body, so a second on-route outage produces no new push.",
   "  - The digest covers only title and body, so a second on-route outage produces no new push while the first stays listed first, and lift changes are ignored entirely during a disruption.")
rb("  - `.gitignore` misses `*.sqlite3-journal`/`-wal` and `.DS_Store`.",
   "  - `.gitignore` misses `*.sqlite3-journal` and `.DS_Store`.")
rb("`test_push_delivery.py` stubs `was_sent`, `mark_sent` and `send_push` in every test. Nothing exercises:",
   "Every push test in `test_push_delivery.py` stubs `send_push`, and the scheduled-check tests also stub `was_sent`/`mark_sent`. Nothing exercises:")

ids=json.load(open(SP+"ids.json"))
changed={("PS2/backend/"+k):bodies[k] for k in bodies if bodies[k]!=orig[k]}
json.dump({"comments":{str(ids[k]):v for k,v in changed.items()},"review_body":body}, open(SP+"edits.json","w"))
print("changed comments:",len(changed)); print("\n".join(sorted(changed)))
