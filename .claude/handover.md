# Handover — PS2 frontend takeover: five fixes and a UI skill (2026-09-19)

> Supersedes the 2026-09-18 handover, which covered the PR #1 backend review. That work is
> done: PRs #1, #2 and #3 are merged. Its still-live gotchas are carried forward below.

## Goal

Take over the frontend a teammate (Jettan17) built on `codex/frontend`, now merged to
`main`, and get it to a state that survives judging: close the five open defects, then do
the visual pass, then encode the direction as a skill so future contributors stay aligned.

Context: NebulaX 2026 hackathon, Problem Statement 2 — Smart Commuter Companion. Persona
is **Mdm Lim**: Bedok → Singapore General Hospital, fortnightly appointment, step-free,
large text, lift-outage warning the evening before. Judged on a real phone browser.

## Status

- `origin/main` is at `ebd1ab2` and **pushed**. Working tree clean except `.DS_Store`.
- The frontend is merged and **runs against live LTA/OneMap data**, not fixtures.
- Docs are reconciled — `PS2_INDEX.md` §0 ranks every document's authority, §11 records
  every conflict and its resolution. **Read §0 before trusting any PS2 doc.**
- Nothing in the five work items below has been started. No code has been changed this
  session; all commits so far are documentation.

History shape on `main` — two deliberate merges, authorship kept separate:

```
ebd1ab2 docs(ps2): trace the map downscope to its origin in the frontend plan
b88bcb3 Merge docs/reconcile-ps2: the frontend document reconciliation
4afd7d2 Merge codex/frontend: the mobile journey companion   (13 commits, Jettan17)
```

## Next steps

Ordered. 1 is the cheapest real win; 4 must precede the UI pass or you redo the work.

1. **Register the service worker.** `PS2/frontend/src/main.tsx` is bare — nothing imports
   `virtual:pwa-register` or calls `navigator.serviceWorker.register`. So `src/sw.ts` and
   the PWA manifest are dead code. Consequence: `navigator.serviceWorker.ready` at
   `src/features/push/ReminderControls.tsx:29` never resolves, so "Enable reminders" hangs
   forever for every user, and a cold load while offline fails with no cached shell.
   `vite.config.ts` already configures `VitePWA` with `strategies: 'injectManifest'` and
   `registerType: 'prompt'`, which *requires* an explicit `registerSW()` call. One call in
   `main.tsx` unblocks both push and offline launch. Highest leverage in the codebase.

2. **Build the route map.** Decision is settled — see "Key decisions". Use **MapLibre GL JS
   with free-tier vector tiles** (needs one provider signup for an API key; Protomaps or
   MapTiler). No backend work required: `POST /api/trips` already returns
   `map.bbox` and `map.geometry`, a GeoJSON `FeatureCollection` with one **mode-tagged**
   `LineString` per leg (`{leg_id, mode}`). That `leg_id` tagging is exactly what the
   brief's "affected portion distinguished from the unaffected portion" needs.
   Known limit: the rail leg carries only 2 points, so it renders as a straight
   Bedok→Outram line, not the true track alignment. Acceptable; note it, don't fake it.

3. **Add automatic refresh.** There is no `setInterval`, visibility or reconnect refresh
   anywhere. `src/features/journey/journeyCoordinator.ts` fetches status once on mount and
   then only on a manual tap, while `statusFreshness` keeps reporting `'current'`
   indefinitely. For a "leave by" tool that is a correctness bug, and it undercuts
   *proactive*, one of the four scored words in the brief.

4. **Turn on `strict`.** No `strict` key exists in `tsconfig.json`, `tsconfig.app.json` or
   `tsconfig.node.json`, so TypeScript defaults to `strict: false` and `strictNullChecks`
   is off app-wide. Do this **before** the UI pass — it touches every file. Expect a pile
   of errors on first enable. Compounding factor: every backend response schema uses
   Pydantic `extra="allow"`, so `openapi-typescript` emits `& { [key: string]: unknown }`
   on all 54 response types — meaning `tsc` will **not** catch a typo'd or renamed field on
   any API response. Already exercised at `journeyCoordinator.ts:117-124`.

5. **Fix the flaky test.** Observed once: `1 failed | 31 passed`. Did not reproduce in 13
   subsequent runs, so the specific failing test was never captured. Mechanism not proven —
   do not claim a root cause without reproducing it. Two candidates:
   `src/features/planning/AppointmentForm.tsx:13` computes its default from the **real
   clock** (`Date.now() + 24h`) and `AppointmentForm.test.tsx` installs **no fake timers**
   (only `AsyncFeedback.test.tsx:10` and `api/client.test.ts:43` do); and
   `src/components/AsyncFeedback.tsx:12` has a 5-second slow-request timer that the third
   AppointmentForm test races against a never-resolving fetch.

Then, after the UI pass — **not before it**:

6. **Write the mobile UI skill** at `.claude/skills/ps2-mobile-ui/SKILL.md` (Claude Code
   auto-loads `SKILL.md` from that layout; a loose `skills.md` is not picked up). It must
   encode *decisions*, not generic mobile advice. The tokens already exist in
   `PS2_DESIGN_REFINEMENT_PLAN.md` — inlined under "Key decisions" below so you do not have
   to go find them. Write it *from* the UI pass so it describes what was actually built.

## Key decisions & constraints

- **The route map is mandatory and in scope. Do not relitigate this.**
  `PS2_DECISION_RECORD.md` §7.5 **D14 is titled "Never cut"** and its first item is
  "Door-to-door route (step-free walks, EWL leg) on an OSM map with attribution"; its
  fourth is "Visuals: affected route section shown by pattern and label". The brief,
  `PS2_README.md` §3.2.3, requires "The route itself on a map, with the affected portion
  clearly distinguished from the unaffected portion", and §3.2.4 caps a submission missing
  any of 3.2.1–3.2.3 at **level 3** on the part of the score it covers.
  Four documents had narrowed it away in four locally-reasonable steps (traced in
  `PS2_INDEX.md` §11.2). Those are now annotated as withdrawn.
- **Offline *tile caching* stays parked** — that is a genuine licensing constraint
  (`PS2/backend/app/api/offline.py:81`) and the brief's quiet-feed allowance covers
  shipping written steps offline. A parked tile pack is defensible to a judge; a missing
  map is a scoring cap. Do not conflate the two again — that conflation is what caused this.
- **OSM attribution is a licence breach if dropped, not a style point** — it caps the score.
  The backend serves the strings; `src/features/journey/JourneyPage.tsx:37` renders them
  today. Do not lose that in a UI rewrite.
- **Basemap: MapLibre GL JS + free-tier vector tiles.** Chosen over Leaflet+raster (the
  brief warns public tile servers "must not be hammered") and over a blank-canvas GeoJSON
  render (arguably fails "on a map" and would not lift the cap).
- **Visual direction of record** is `PS2_DESIGN_REFINEMENT_PLAN.md`. Its tokens, verbatim:
  - Canvas `#F4F5F0`; ink `#12271F`; secondary `#536259`; forest `#0D6048`; warm accent
    `#D8A35F`. Colour always accompanies text/icons; amber/red reserved for real warnings.
  - Spacing scale 4/8/12/16/24/32/48px. Mobile gutter 16px at 320px, 20px from 390px.
    Max reading width ~42rem; secondary column only from 960px.
  - Body 18px/1.5, supporting text ≥16px, departure 56–72px tabular, headings 24–32px,
    rem-based so text enlargement works. Manrope for headings, system sans for body.
  - Radius 16px controls / 24px primary surface, one shadow tier, 48px touch targets.
  - Motion: press 100ms, exit 140ms, enter 240ms, route reveal 420ms; entrance easing
    `cubic-bezier(.22, 1, .36, 1)`, exit `cubic-bezier(.4, 0, 1, 1)`. Respect
    `prefers-reduced-motion` (already honoured in all three stylesheets).
- **`AGENTS.md` rule:** atomic Conventional Commits, one theme per commit, no scope mixing.
- Commit attribution in use: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- The app is **single-corridor by construction** — `destination_id: 'SGH'` is hardcoded at
  `AppointmentForm.tsx:38` and enforced backend-side. That is intentional per the persona
  decision, not a bug. General routing is Tasks 6–10 of `PS2_CONSOLIDATED_ROADMAP.md` and
  is explicitly a separate programme.

## Gotchas / learnings

- **The teammate's own review already listed the worst bugs and nobody read it.**
  `PS2_FRONTEND_REVIEW.md` (27 lines, written at 00:56 on the first frontend commit) has
  the service-worker hang as finding 5 and the missing auto-refresh as finding 4. They were
  known within an hour of starting and never closed. Check that file before re-deriving.
- **"Completed" in `PS2_UX_POLISH_RESULTS.md` is not evidence.** The doc written 38 minutes
  later says so explicitly. The branch head is a *specification*, not a shipped increment —
  its required completion artefact `PS2_DESIGN_REFINEMENT_RESULTS.md` does not exist.
- **`PS2/references/` was found moved into `PS2/frontend/references/`** mid-session by
  something outside this session; restored. If it happens again: the six organiser files
  (problem statement, DataMall guides, weather specs) belong at `PS2/references/`, and
  `PS2_INDEX.md` §1 (sources S1–S9) and `PS2_README.md` both cite that path.
- **Check which branch you are on before editing.** The checkout was switched to
  `codex/frontend` mid-session by something outside this session, which is why
  `PS2/frontend/` existed to run. It is all merged to `main` now, but verify.
- **Playwright needs a browser binary**: `npx playwright install chromium --with-deps`
  before `npm run test:e2e`. Not in the frontend README's verification section.
- **`jsx-a11y` and `axe-core` are installed but never run.** The linter is `oxlint` and
  `.oxlintrc.json` enables only `react`/`typescript`/`oxc`; the single Playwright spec
  (`e2e/home.spec.ts`) does not import `AxeBuilder`. So none of the genuinely good a11y
  work in this codebase is automatically verified.
- **No error boundary exists anywhere** — any render throw white-screens the whole app.
- **`api:generate` needs a live backend**: it runs `openapi-typescript` against
  `http://127.0.0.1:8000/openapi.json`. Nothing checks `generated.d.ts` for staleness, so
  a backend schema change desyncs silently. It is current as of `ebd1ab2`.
- **OneMap token is a 3-day JWT.** The one in `PS2/.env` expires **2026-09-22 10:53 SGT**
  and will need re-minting. The LTA key was pasted into a chat transcript — worth rotating
  after the event.
- Carried forward from the backend session, still true:
  - Fixtures are **rewritten at runtime** (`app/sources/base.py:_record`), which dirties the
    git tree during tests. Monkeypatch `Source._record` or point `app.config.FIXTURES` at
    a temp dir.
  - `PS2_USE_FIXTURES=1` is **not** a hard offline switch — a missing fixture still hits the
    network, and `app/sources/onemap.py` ignores the flag entirely.
  - `data/derived/stepfree_graph.json` is 4.9 MB and its `built_at` changes on every
    rebuild; avoid re-running `scripts/build_data.py` without reason.
  - `gh` CLI is authenticated for this repo.

## Important files

- `PS2/PS2_INDEX.md` — **start here.** §0 is the document authority ranking, §11 is the
  full reconciliation (§11.2 = the map, §11.4 = open defects, §11.5 = live validation).
- `PS2/PS2_FRONTEND_REVIEW.md` — 7 open functional findings from the teammate. The work list.
- `PS2/PS2_DESIGN_REFINEMENT_PLAN.md` — visual direction of record; tokens, composition,
  motion. Its map-exclusion line is annotated as withdrawn.
- `PS2/PS2_DECISION_RECORD.md` — D1–D14, persona rationale, privacy draft. **Binding.**
- `PS2/PS2_README.md` — the organisers' brief and rubric. **Outranks everything in repo.**
- `PS2/frontend/src/features/journey/journeyCoordinator.ts` — 206 lines, the core state
  machine. Hand-rolled observable with a `generation` counter that correctly discards stale
  async responses. Good code; build on it, don't replace it.
- `PS2/frontend/src/main.tsx` — where the missing `registerSW()` goes (step 1).
- `PS2/frontend/vite.config.ts` — PWA config and the `/api` → `:8000` dev proxy.
- `.claude/pr1-review-findings.md` — 34 indexed backend findings from PR #1 (now merged).
- `.claude/repro/` — 47 scripts reproducing those findings, with a README mapping them.

## Verification

Environment is already provisioned — venv (Python 3.14.5) and 390 npm packages are
installed, `PS2/.env` exists with live LTA + OneMap keys and VAPID pair, and is gitignored.

Start both services (two terminals, from repo root):

```bash
cd PS2/backend && ../backend/.venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd PS2/frontend && npm run dev          # :5173, proxies /api to :8000
```

Confirm the stack is live, not fixtures:

```bash
curl -s localhost:8000/api/health
# expect: {"ok":true,"stations":186,"credentials":{...:true,...:true},"fixtures_only":false}

curl -s -X POST localhost:8000/api/trips -H 'content-type: application/json' \
  -d '{"appointment_at":"2026-09-20T10:30:00+08:00"}'
# expect: 3 legs Bedok→SGH, step-free lift instruction on leg 3, map.geometry populated
```

Frontend gates, from `PS2/frontend` — all four passed at `ebd1ab2`:

```bash
npm run typecheck     # exit 0
npm run lint          # oxlint, silent on success
npm run test:run      # 15 files, 32 tests  (see flake note, step 5)
npm run build         # ~296 kB / 92 kB gzip; PWA precache 6 entries
npm run test:e2e      # needs: npx playwright install chromium --with-deps
```

Per-step checks:

- **Step 1 done** when `navigator.serviceWorker.ready` resolves in a production build
  (`npm run build && npm run preview`), "Enable reminders" completes instead of hanging,
  and a reload with DevTools offline still serves the shell. Dev mode is not sufficient
  evidence — `injectManifest` behaves differently there.
- **Step 2 done** when the route renders on tiles with the affected leg visually distinct
  from unaffected ones, OSM attribution visible, and it reflows at 320px with no horizontal
  scroll. Drive it with the `/demo` scenario switches (`VITE_ENABLE_DEMO=true`) to force a
  disruption and confirm the affected leg actually changes appearance.
- **Step 4 done** when `npm run typecheck` exits 0 *with* `"strict": true` in
  `tsconfig.app.json`.
- **Step 5 done** when you have *reproduced* the failure, not merely seen green. Loop it:
  `for i in $(seq 1 30); do npx vitest run --reporter=basic || break; done`.

Do not claim any of these passed without pasting the actual command output.
