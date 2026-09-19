# Handover — PS2 frontend UI pass, batch 2 of 3 (2026-09-19)

> Supersedes the earlier 2026-09-19 handover ("batches 1–3"). **Batch 1 is done and committed.**
> That handover's corrections and gotchas sections are still accurate and are carried forward
> below; its "Next steps" for batch 1 are complete.

## Goal

Execute **batches 2 and 3** of `PS2/PS2_DESIGN_REFINEMENT_PLAN.md` on `feat/ps2-frontend-fixes`.
Batch 1 is finished. Batches 4–6 are deferred by the user. Keep writing
`PS2/PS2_DESIGN_REFINEMENT_RESULTS.md` **as you go** — batch 1's section is already written; add
batch 2's and 3's in the same shape.

Context: NebulaX 2026 hackathon, Problem Statement 2 — Smart Commuter Companion. Persona is
**Mdm Lim**: Bedok → Singapore General Hospital, fortnightly appointment, step-free, large text,
lift-outage warning the evening before. Judged on a real phone browser.

## Status

- Branch `feat/ps2-frontend-fixes`, **9 commits, 3 of them unpushed**, tracking
  `origin/feat/ps2-frontend-fixes`. Clean tree except the pre-existing untracked `.DS_Store`.
- All five gates pass at `3981667`: `typecheck` (strict, now also covers `e2e/`), `lint`,
  `test:run` (20 files / 52 tests), `build`, `test:e2e` (228 tests).

```
3981667 docs(ps2): record the batch 1 reflow evidence          ← this session
4c00747 refactor(ps2-frontend): give each journey region its own grid area  ← this session
c9b9e52 fix(ps2-frontend): stop a saved journey scrolling sideways          ← this session
2ea24e8 docs(hoto): hand over the UI pass to a fresh session
ce72edd fix(ps2-frontend): let a saved journey open offline
```

**Batch 2 was designed and the design was presented, but never approved — the user asked for a
handover instead of answering.** Re-present it (it is reproduced in full below) or just proceed;
the three decisions it depended on were already answered and are binding (see Key decisions).

## Next steps

One coherent Conventional Commit per batch or smaller fix. Attribution line:
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. All paths under `PS2/frontend`.

### Batch 2 — establish the visual system (the approved design, verbatim)

**Stylesheet structure.** Delete `global.css` and `native.css`; fold `feedback.css` in. Replace
with one entry that makes cascade order explicit and gives every component exactly one owner:

```
src/styles/index.css       @import the four, in order  ← App.tsx imports only this
  tokens.css               every token, defined once
  base.css                 reset, document, type scale, links, focus, reduced motion
  layout.css               app shell, header, journey regions, reflow guards
  components.css           one block per component
```

**Tokens**, verbatim from the plan: canvas `#F4F5F0`, ink `#12271F`, secondary `#536259`, forest
`#0D6048`, warm accent `#D8A35F`. Spacing 4/8/12/16/24/32/48. Gutter 16px at 320, 20px from 390.
Max reading width ~42rem; secondary column only from 960px. Radius 16px controls / 24px primary
surface. One shadow tier. 48px touch targets.

**Everything becomes rem-based.** It is almost entirely `px` today — that is the single change
that makes text enlargement work, and it will make the existing 200%-text tests *stricter*
rather than looser. Expect the responsive suite to surface new failures here; that is the suite
doing its job, not a regression.

**Type.** Manrope self-hosted (latin variable subset, 24 KiB woff2, weights 400–800,
`font-display: swap`, tabular numerals) for the departure time and headings; system sans for body
at 18px/1.5; supporting text ≥16px. Commit the OFL licence beside it.
- CSS: `https://fonts.googleapis.com/css2?family=Manrope:wght@400..800&display=swap` (send a
  browser User-Agent or you get the legacy TTF sheet)
- latin woff2: `https://fonts.gstatic.com/s/manrope/v20/xn7gYHE41ni1AdIRggexSvfedN4.woff2`
  — **24,576 bytes, already verified**
- licence: `https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt` (the
  `sharanda/manrope` repo paths 404)

**Surfaces.** One dominant dark departure surface, one lightly bordered status region, route
diagram on the canvas, mostly borderless timeline. **Not every block a card.** Delete the
decoration that competes with it: `.button-primary::after` sheen, `body::before` grid,
`.journey-hero::before` circle and `::after` grid, `.status-panel::after` circle,
`.hero-panel::before` bar, `.route-ticket::before` tab.

**Behaviour changes the plan puts in batch 2, not just paint:**
- Replace the `↻` glyph with a **labelled "Refresh" control**, moved into the status region
  beside the checked-time. It currently lives in the hero as `.refresh-orb`.
- Home must stop claiming readiness from an ID alone → neutral **"Open saved journey"**
  (`App.tsx`, the `.appointment-preview` heading and the `.home-action` link).
- Extract **`src/components/PageShell.tsx`** from `App.tsx`, with a contextual header naming each
  screen and its back destination.
- `AppointmentForm.tsx` must **require an explicitly chosen time** instead of defaulting to
  tomorrow-at-this-minute (`futureSingaporeDateTime()`), keep errors tied to the right field, and
  stop letting a network failure mark a valid date invalid.

**Testing.** Add `e2e/a11y.spec.ts` — `@axe-core/playwright` and `axe-core` are **installed but
have never been run**, so none of the a11y work here is verified by anything. Cover ready,
pending, error and dialog states, plus explicit 48px touch-target measurement. Screenshots at
320/390/1280 for all six screens via `npm run test:screens`, then **inspect them**.

**Two things to flag rather than silently decide:** the warm accent `#D8A35F` is about 2.1:1 on
the light canvas, so it fails WCAG AA as text — use it for non-text emphasis only and record
that. And moving Refresh out of the hero changes that surface's composition, which batch 3
rebuilds anyway.

Gate: screenshots at 320 / 390 / desktop; verify 48px targets, contrast, large text, wrapping,
one obvious primary action.

### Batch 3 — rebuild the journey composition

Files: `JourneyPage.tsx`, `RouteOverview.tsx`, `JourneyTimeline.tsx`, `JourneySkeleton.tsx`,
`StatusPanel.tsx`.

- **`RouteOverview.tsx` still needs the SVG rebuild.** Replace the uniform dots + joined
  stop-name paragraph with a **responsive SVG route trace** with adjacent HTML labels tied to
  nodes. Walking dotted, rail solid. Must handle zero/one/many legs, long names and missing
  geometry, and **never require real map tiles**. Separate from the MapLibre map added in
  `e395d94` — both are meant to exist; the map is the brief's §3.2.3 requirement, the SVG trace
  is the always-works schematic. Reuse `legImpact.ts` so the diagram and the map agree on which
  leg is affected.
- Derive **short step titles** from structured `mode`/`from`/`to`/`line` fields. Do **not** parse
  prose. Keep the original `instruction` as readable body text; exit, lift and safety details
  stay exposed. Today `JourneyTimeline.tsx:17` puts the whole instruction paragraph in an `<h3>`.
- **Restore `plan.summary.timing_basis`** in a labelled disclosure — the hero dropped it for
  metrics. Uncertainty and safety warnings stay *outside* the disclosure.
- `JourneyPage.tsx` still does `plan.summary.leave_by_label.replace(/^Leave at\s*/i, '')` —
  a regex stripping English copy as a time parser. Keep the full backend label accessible and
  stop relying on this.
- Gate: ready / stale / warning / no-overview / failed-replan screenshots; no information lost;
  no retained plan falsely presented as confirmed.

## Key decisions & constraints — do not relitigate

**Decided this session by the user (2026-09-19):**
- **Full stylesheet restructure**, not a minimal token-only diff. Because `native.css` stacks
  three passes that each override the one before, and batch 3 builds directly on it.
- **Self-host Manrope.** It came in at 24 KiB against the plan's 60 KiB budget, which was the
  plan's own condition for using it rather than falling back to system fonts.
- **No checkpoint between batches 2 and 3.** Run them back to back, commit separately, report
  once at the end.

**Carried forward, still binding:**
- **The route map is mandatory and in scope.** `PS2_DECISION_RECORD.md` §7.5 D14 is titled
  "Never cut"; `PS2_README.md` §3.2.3 requires the route on a map with the affected portion
  distinguished, and §3.2.4 caps a submission missing it at **level 3**. The map-exclusion line
  inside `PS2_DESIGN_REFINEMENT_PLAN.md` is annotated as **withdrawn**; the rest of that plan
  (tokens, spacing, typography, composition, motion) remains current.
- **Basemap is OneMap raster, not MapLibre vector tiles.** SLA serves it free for Singapore, no
  signup, no API key to mint before a demo, and the backend already talks to OneMap. Endpoint
  `https://www.onemap.gov.sg/maps/tiles/Grey/{z}/{x}/{y}.png`, no token. Grey over Default —
  Default fights the route overlay.
- **Offline *tile caching* stays parked** (licensing, `PS2/backend/app/api/offline.py:81`).
  A parked tile pack is defensible; a missing map is a scoring cap. Do not conflate them.
- **OSM attribution is a licence breach if dropped**, not a style point. `JourneyPage.tsx`
  renders the backend strings in `.journey-actions`; the map adds OneMap/SLA separately.
  **Do not lose either in a UI rewrite.**
- **Single-corridor by construction** — `destination_id: 'SGH'` hardcoded in
  `AppointmentForm.tsx` and enforced backend-side. Intentional, not a bug.
- **Backend is fine and out of scope.** Live LTA + OneMap data, PRs #1–#3 merged.
- Batch 6's **≤5 KiB added compressed JS** budget: MapLibre is 279 KiB gzip — justified by
  D14/§3.2.3, code-split and precache-excluded, but it **must be recorded** in
  `PS2_DESIGN_REFINEMENT_RESULTS.md`, not quietly ignored. Manrope's 24 KiB is a font, not JS,
  and has its own 60 KiB budget.

## Gotchas / learnings

### From this session

- **The e2e route glob `**/api/**` also matches the dev server's own `/src/api/*.ts` modules**
  and answers them with JSON, which silently breaks the page before React boots — 121 tests
  "failed" for this reason before I spotted it. `mockApi.ts` now matches on
  `url.pathname.startsWith('/api/')`. Do not go back to a glob.
- **Releasing a `white-space: nowrap` chip from its automatic minimum makes reflow worse.**
  `min-inline-size: 0` on `.time-delta` shrank it to 48px while its text stayed 109px, spilling
  across the page and regressing two previously-passing tests. Nowrap chips need
  `flex: none` and a wrapping parent instead. Same applies to `.journey-date`, `.route-chip` and
  the section-heading link.
- **`grid-area: <name>` with no matching `grid-template-areas` silently stacks every region on
  top of the others** — the browser creates implicit lines with that name. The mobile
  single-column area map in `global.css` is load-bearing, not decorative.
- **Typing the e2e fixtures immediately caught four fabricated payload shapes** (`Disruption`,
  `TripMap`, `NotOffered`). `e2e/` sat outside every tsconfig project until `tsconfig.e2e.json`
  was added. Keep it referenced from `tsconfig.json`.
- **Playwright runs the responsive suite on one worker** regardless of `--workers=N`, because
  `fullyParallel` is not set and the tests live in one file. 228 tests take ~65s. Do not assume
  a hung run.
- **The screenshot spec asserts nothing**, so it is its own Playwright project (`screens`) and is
  excluded from `npm run test:e2e`. Run it with `npm run test:screens`. Output goes to
  `PS2/evidence/screens/<width>/` and is **gitignored**, not committed.
- **In the screenshot harness the route map shows its loading fallback**, because `mockApi`
  aborts all OneMap tile requests so a slow tile server cannot be mistaken for a layout fault.
  That is the harness, not a bug — but it means screenshots cannot prove the map renders. Verify
  the map separately against the live backend.
- The warm accent `#D8A35F` is roughly **2.1:1 on the `#F4F5F0` canvas** — fails WCAG AA for
  text. Non-text emphasis only.

### Carried forward

- **There is still no error boundary anywhere except around the map.** This already caused one
  white screen: offline, the non-precached map chunk's dynamic import rejects and the throw
  blanked the whole page, wiping the written steps she saved for exactly that moment. Fixed in
  `ce72edd` with a boundary in `RouteMapPanel.tsx` and by skipping the map for
  `snapshot.source === 'saved'`. **Any new lazy import or render throw in batches 2–3 has the
  same failure mode.** Consider a top-level boundary. This is also why
  `formatSingaporeDateTime` now returns an unparseable value instead of letting `Intl` throw.
- **Assert durable outcomes, not transient ones, in tests.** A previous flake was an assertion on
  a loading skeleton that disappears when the mocked fetch settles. Batch 3 touches
  `JourneySkeleton.tsx`; this bites again there.
- `journeyCoordinator.ts` is good code — a hand-rolled observable with a `generation` counter
  that correctly discards stale async responses. **Build on it, do not replace it.** Batch 4
  warns: do not key/remount `JourneyProvider` for visual transitions or you cause duplicate
  network requests.
- **Three MapLibre failures that report no error at all**, all fixed in `e395d94`: MapLibre
  mutates the style object it is handed (build a fresh style per instance); its worker must be
  imported with **`?worker&url`**, not `?url`; and `vite preview` does not inherit `server.proxy`
  (`preview.proxy` now added). Symptom: `map.isStyleLoaded()` stays `false` while layers exist.
- **Backend response schemas use Pydantic `extra="allow"`**, so `openapi-typescript` emits an
  index signature on all 54 response types. `tsc` will **not** catch a typo'd or renamed field on
  any API response, even with strict on. `plan.replan_failed` is one such undeclared field.
- **OneMap token is a 3-day JWT — expires 2026-09-22 10:53 SGT** and will need re-minting. The
  LTA key was pasted into a chat transcript; worth rotating after the event.
- The Chrome extension (`mcp__claude-in-chrome__*`) is **not connected**. Use Playwright; it
  works well and gives reproducible evidence. Headless WebGL needs
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`.
- Node scripts run from `/tmp` cannot resolve `node_modules`; run throwaway Playwright scripts
  from inside `PS2/frontend` and delete them.
- Fixtures are **rewritten at runtime** (`app/sources/base.py:_record`), dirtying the git tree
  during backend tests. `PS2_USE_FIXTURES=1` is **not** a hard offline switch.
- `api:generate` needs a live backend on `:8000`; nothing checks `generated.d.ts` for staleness.

## Important files

**The spec and its authorities**
- `PS2/PS2_DESIGN_REFINEMENT_PLAN.md` — **the spec for this work.** 179 lines. Batches at
  §"Bounded implementation batches"; tokens at §"Design direction"; target wireframe at
  §"Target composition"; motion table (batch 4, deferred) at §"Motion specification".
- `PS2/PS2_INDEX.md` — §0 ranks every document's authority, §11 records every conflict and its
  resolution. **Read §0 before trusting any PS2 doc.**
- `PS2/PS2_README.md` — organisers' brief and rubric. **Outranks everything in repo.**
- `PS2/PS2_DECISION_RECORD.md` — D1–D14. **Binding.**
- `PS2/PS2_FRONTEND_REVIEW.md` — 7 findings. **#2 and #4 closed**; #5 and #7 partial;
  **#1, #3, #6 still open** (two are High). Not in scope for 2–3 but do not regress them.

**Written this session**
- `PS2/PS2_DESIGN_REFINEMENT_RESULTS.md` — batch 1 section complete: reproduction, measured root
  cause, the desktop re-placement numbers, gate output, honest limitations. **Append to this.**
- `PS2/frontend/e2e/fixtures/payloads.ts` — frozen API payloads captured from the live backend,
  959 lines. Trip id `t_fixture000000000000001`, observed-at stamps frozen to 09:05.
- `PS2/frontend/e2e/fixtures/states.ts` — the named states derived from those payloads
  (`statusStale`, `statusDisrupted`, `planLongNames`, `planNoOverview`, `savedBundle`, …).
- `PS2/frontend/e2e/fixtures/mockApi.ts` — route interception + IndexedDB seeding.
- `PS2/frontend/e2e/fixtures/overflow.ts` — reports the offending element, its box, its computed
  width and its layout ancestor. Reuse it rather than writing a new probe.
- `PS2/frontend/e2e/responsive.spec.ts` — 221 tests, 17 states × 10 widths + 200% text.
- `PS2/frontend/e2e/journey-layout.spec.ts` — region placement stability.
- `PS2/frontend/e2e/screenshots.spec.ts` — capture only, project `screens`.

**To be rewritten in batches 2–3**
- `PS2/frontend/src/App.tsx` — `PageShell` is defined inline here; batch 2 extracts it.
- `PS2/frontend/src/styles/` — `tokens.css` (18 lines), `global.css` (~100), `native.css` (~117),
  `feedback.css` (9). The override tangle batch 2 replaces.
- `PS2/frontend/src/features/journey/RouteOverview.tsx` — the schematic batch 3 replaces.
- `PS2/frontend/src/features/journey/legImpact.ts` — maps status onto legs. Reuse it for the SVG
  trace so the diagram and the map agree.
- `PS2/frontend/src/features/planning/AppointmentForm.tsx` — the default-time and error-binding
  changes batch 2 needs.

## Relevant memory (inlined — these do NOT auto-reload after /compact)

Memory was empty at the start of this session; two files were written. Verbatim:

> **`ps2-design-batch2-direction.md`** (type: project)
> On 2026-09-19 the user chose, for batch 2 of `PS2/PS2_DESIGN_REFINEMENT_PLAN.md`:
> 1. **Full stylesheet restructure**, not a minimal token-only diff. `global.css` and
>    `native.css` are to be replaced by `tokens.css` / `base.css` / `layout.css` /
>    `components.css` behind a single `index.css`, with exactly one owner per component.
> 2. **Self-host Manrope** — latin variable subset, 24 KiB woff2, OFL licence committed. Used for
>    the departure time and headings only; system sans for body.
> 3. **No checkpoint between batches 2 and 3** — run them back to back, commit separately,
>    report once at the end.
>
> **Why:** `native.css` stacks three passes that each override the one before, so any further
> decoration on top is unmaintainable, and batch 3 builds directly on it. The font came in well
> under the plan's 60 KiB budget, which was the plan's own condition for using it rather than
> falling back to system fonts.
>
> **How to apply:** treat these three as settled; do not re-ask. Batches 4–6 remain deferred.

> **`ps2-user-prefers-options-with-a-recommendation.md`** (type: feedback)
> The user opens sessions with instructions like "read handover and get to work!" and answers
> multi-part decision prompts in one pass without hesitation. When offered a checkpoint between
> two batches of work they declined it and said to carry straight on.
>
> **Why:** they are executing a plan they already wrote and reviewed; the decisions they want are
> the ones the plan genuinely leaves open (a budget, a risk appetite, a trade-off), not
> confirmation that the plan should be followed.
>
> **How to apply:** batch the genuinely-open decisions into one prompt, lead each option with a
> recommendation and the fact behind it, then execute without further check-ins. Do not ask
> "shall I proceed?" between steps.

## Verification

Environment is provisioned — venv (Python 3.14.5), npm packages installed, `PS2/.env` has live
LTA + OneMap keys and a VAPID pair, gitignored. Playwright's `chromium-1243` is already in
`~/Library/Caches/ms-playwright/`; no `npx playwright install` needed.

**The backend was running on :8000 during this session** and answered `/api/health` with
`fixtures_only: false` and both credentials `true`. A Playwright dev server may still be on
:5173. Start fresh ones on other ports rather than trusting these to be alive.

```bash
cd PS2/backend && ./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd PS2/frontend && npm run dev            # proxies /api to :8000
curl -s localhost:8000/api/health         # expect fixtures_only:false, both credentials true
```

Gates — all five passed at `3981667`, tree unchanged since:

```bash
cd PS2/frontend
npm run typecheck     # exit 0; strict; now covers e2e/ via tsconfig.e2e.json
npm run lint          # oxlint, silent on success
npm run test:run      # 20 files, 52 tests
npm run build         # precache 6 entries (318.60 KiB)
npm run test:e2e      # 228 tests, ~65s, single worker
npm run test:screens  # capture only → PS2/evidence/screens/<width>/, gitignored
```

The e2e suite is the regression net for batches 2 and 3. **Expect the 200%-text tests to fail
once type goes rem-based** — that is the suite getting stricter, and those failures are real
reflow to fix, not noise.

Additionally:

- **Do not claim a fix without the measurement.** `e2e/fixtures/overflow.ts` prints the offending
  element and its computed size; paste it.
- **Inspect screenshots, do not just generate them** — clipped controls, crowding, inconsistent
  alignment, unexplained empty space. Known and unfixed as of `3981667`: full instruction
  paragraphs used as bold headings, the joined stop-name paragraph, and empty space below the
  desktop second column. Batches 2–3 address all three.
- Verify the production build separately where the service worker is involved; dev-server checks
  do not establish production offline behaviour. Regression check for `ce72edd`: with the network
  disabled, a cold load of `/trip/:id` must return 200 and show the departure time, the
  offline-copy notice and the written steps, with **zero page errors**.
- Do not claim any of these passed without pasting the actual command output.
