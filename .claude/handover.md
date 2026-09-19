# Handover — PS2 frontend UI pass, batches 1–3 (2026-09-19)

> Supersedes the earlier 2026-09-19 handover ("five fixes and a UI skill"). All five of its
> work items are **done and pushed**, plus a sixth fix it did not know about. Several of its
> claims were **wrong** and are corrected below — read "Corrections" before trusting it if
> you find a copy.

## Goal

Execute **batches 1, 2 and 3** of `PS2/PS2_DESIGN_REFINEMENT_PLAN.md` on
`feat/ps2-frontend-fixes`. Batches 4–6 are explicitly deferred; the user scoped to 1–3 and
will reassess. Write `PS2/PS2_DESIGN_REFINEMENT_RESULTS.md` **as you go**, not at the end.

Context: NebulaX 2026 hackathon, Problem Statement 2 — Smart Commuter Companion. Persona is
**Mdm Lim**: Bedok → Singapore General Hospital, fortnightly appointment, step-free, large
text, lift-outage warning the evening before. Judged on a real phone browser.

## Status

- Branch `feat/ps2-frontend-fixes`, **6 commits, pushed**, tracking `origin/`. Clean tree
  except a pre-existing untracked `.DS_Store`.
- All five gates pass: `typecheck` (strict on), `lint`, `test:run` (19 files / 49 tests),
  `build`, `test:e2e` (1 test).
- Not merged. `origin/main` is behind; local `main` has `51958ad` (old handover) unpushed,
  which rides along in this branch's history.

```
ce72edd fix(ps2-frontend): let a saved journey open offline
a1b517d test(ps2-frontend): stop the appointment form test racing its own fetch
3863693 build(ps2-frontend): turn on TypeScript strict mode
32d48e9 feat(ps2-frontend): keep the journey status current without a tap
e395d94 feat(ps2-frontend): draw the route on a map with the affected leg distinguished
73d08d6 fix(ps2-frontend): make enabling reminders fail instead of hanging
```

## Next steps

Batches are ordered and gated. **One coherent Conventional Commit per batch or smaller fix**
(`AGENTS.md`: atomic, one theme, no scope mixing). Attribution line:
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

### Batch 1 — Reproduce and fix reflow (the only P1 correctness item)

Files: `src/styles/global.css`, `native.css`, affected components, new
`e2e/responsive.spec.ts`, typed fixtures in `e2e/fixtures/`.

- A user reported horizontal scrolling that **was never reproduced**. The plan forbids
  claiming an unverified root cause — capture the offending bounding box, CSS width and
  nearest layout ancestor before patching.
- Widths to cover: **320, 360, 375, 390, 430, 767, 768, 820, 960, 1280**. Plus 200% text
  enlargement, long destination names/timestamps, and the native date/time control.
- States to cover: journey ready / loading / error / stale / failed-replan, alternatives,
  saved-offline.
- Use `minmax(0, 1fr)` and `min-inline-size: 0` at shrinkable grid/flex boundaries.
  **Do not** use `overflow-x: hidden/clip` on the document to hide it.
- Gate: document scroll width <= client width + 1px, all important controls within viewport,
  in every covered state.

Known suspects, unproven: `global.css:6` has `body { min-width: 320px }` which itself
prevents reflow below 320 CSS px. `native.css:93` `.button-primary::after` is a decorative
sheen at `width:42%; height:330%; transform: rotate(25deg)` inside `overflow:hidden` —
batch 2 says to remove that sheen anyway. Negative header margins at `native.css:76` and
`global.css:79`. Long ISO timestamps (see below) are a live overflow candidate.

### Batch 2 — Establish the visual system

Files: `src/styles/tokens.css`, `global.css`, `native.css`, `src/App.tsx`; **extract
`src/components/PageShell.tsx`** (currently defined inline inside `App.tsx`).

- Tokens belong in `tokens.css` only. Today `native.css` repeatedly overrides `global.css`
  **and itself**, and tokens are redefined across files. Consolidate to one owner per
  component before decorating further.
- Apply to **all six screens** — Home, Plan, Journey, Options, Settings, dialogs — not just
  the journey hero.
- Replace the unicode `↻` refresh glyph with a **labelled "Refresh" control** in the status
  region (`JourneyPage.tsx`, the `.refresh-orb` button).
- Remove the decorative button sheen and repeated background grids/circles.
- Home must not claim readiness from an ID alone — use neutral "Open saved journey".
- Gate: screenshots at 320 / 390 / desktop; verify 48px targets, contrast, large text,
  wrapping, one obvious primary action.

Tokens, verbatim from the plan (these are the direction of record):
- Canvas `#F4F5F0`; ink `#12271F`; secondary `#536259`; forest `#0D6048`; warm accent
  `#D8A35F`. Colour always accompanies text/icons; amber/red reserved for real warnings.
- Spacing 4/8/12/16/24/32/48. Gutter 16px at 320, 20px from 390. Max reading width ~42rem;
  secondary column only from 960px.
- Body 18px/1.5, supporting text >=16px, departure 56–72px tabular, headings 24–32px,
  rem-based. Manrope variable (locally hosted, WOFF2, <=60 KiB compressed, `font-display:
  swap`, include licence) for departure/headings; system sans for body. **Fall back to
  system if the font cannot meet the budget.**
- Radius 16px controls / 24px primary surface, one shadow tier, 48px touch targets.
- Surfaces: one dominant dark departure surface, one lightly bordered status region, route
  diagram on the canvas, mostly borderless timeline. **Not every block a card.**

### Batch 3 — Rebuild the journey composition

Files: `JourneyPage.tsx`, `RouteOverview.tsx`, `JourneyTimeline.tsx`, `JourneySkeleton.tsx`,
`StatusPanel.tsx`.

- **`RouteOverview.tsx` still needs the SVG rebuild.** Replace the uniform dots + joined
  stop-name paragraph with a **responsive SVG route trace** with adjacent HTML labels tied to
  nodes. Walking dotted, rail solid. Must handle zero/one/many legs, long names and missing
  geometry, and **never require real map tiles**. This is *separate from* the MapLibre map
  added in `e395d94` — both are meant to exist; the map is the brief's §3.2.3 requirement,
  the SVG trace is the always-works schematic.
- Derive **short step titles** from structured `mode`/`from`/`to`/`line` fields. Do **not**
  parse prose. Keep the original `instruction` as readable body text; exit, lift and safety
  details stay exposed.
- **Restore `plan.summary.timing_basis`** in a labelled disclosure — the hero currently drops
  it in favour of metrics. Uncertainty and safety warnings stay *outside* the disclosure.
- `JourneyPage.tsx:23` does `plan.summary.leave_by_label.replace(/^Leave at\s*/i, '')` —
  a regex stripping English copy as a time parser. Plan says keep the full backend label
  accessible and stop relying on this.
- Gate: ready / stale / warning / no-overview / failed-replan screenshots; no information
  lost; no retained plan falsely presented as confirmed.

**First concrete item, already found:** `JourneyPage.tsx:26` renders raw ISO strings —
`Offline copy · saved 2026-09-19T05:16:14.011Z · plan generated 2026-09-19T13:16:13+08:00`.
There is already a `formatSingaporeDateTime` helper in `src/lib/singaporeTime.ts` used
elsewhere. Raw ISO is both a plain-language failure for this persona and a long-string
overflow candidate for batch 1.

## Key decisions & constraints — do not relitigate

- **The route map is mandatory and in scope.** `PS2_DECISION_RECORD.md` §7.5 D14 is titled
  "Never cut"; `PS2_README.md` §3.2.3 requires the route on a map with the affected portion
  distinguished, and §3.2.4 caps a submission missing it at **level 3**. The map-exclusion
  line inside `PS2_DESIGN_REFINEMENT_PLAN.md` is annotated as **withdrawn** — the rest of
  that plan (tokens, spacing, typography, composition, motion) remains current.
- **Basemap is OneMap raster, not MapLibre vector tiles.** User chose this over
  MapTiler/Protomaps: SLA serves it free for Singapore, no signup, no API key to mint before
  a demo, and the backend already talks to OneMap. This supersedes the old handover's
  "free-tier vector tiles" line. Endpoint:
  `https://www.onemap.gov.sg/maps/tiles/Grey/{z}/{x}/{y}.png` (no token needed).
  Grey chosen over Default — Default is far busier and fights the route overlay.
- **Offline *tile caching* stays parked** (licensing, `PS2/backend/app/api/offline.py:81`).
  A parked tile pack is defensible; a missing map is a scoring cap. Do not conflate them.
- **OSM attribution is a licence breach if dropped**, not a style point.
  `JourneyPage.tsx` footer renders the backend strings; the map adds OneMap/SLA separately.
  **Do not lose either in a UI rewrite.**
- **Single-corridor by construction** — `destination_id: 'SGH'` hardcoded at
  `AppointmentForm.tsx` and enforced backend-side. Intentional, not a bug.
- **Backend is fine and out of scope.** Live LTA + OneMap data, PRs #1–#3 merged.
- Batch 6 sets a **<=5 KiB added compressed JS** budget. MapLibre is 279 KiB gzip — justified
  by D14/§3.2.3, code-split and precache-excluded, but it **must be recorded** in
  `PS2_DESIGN_REFINEMENT_RESULTS.md`, not quietly ignored.

## Corrections to the previous handover (it was wrong; do not redo this work)

1. **"Service worker is never registered / reminders hang for every user" — false.**
   `vite-plugin-pwa` defaults to `injectRegister: 'auto'` and had always injected
   `/registerSW.js` into production builds. Proven by stashing, rebuilding and probing the
   pre-fix build: SW registered, `ready` resolved, offline cold load served the shell.
   `sw.ts` was never dead code. Adding `registerSW()` in `main.tsx` is actively *worse* — the
   plugin stops injecting when it sees the import, trading a 130-byte inline script for
   5.65 kB of `workbox-window`. The real bugs, both now fixed in `73d08d6`: dev-mode had no
   worker at all (`devOptions` unset), and `navigator.serviceWorker.ready` **never rejects**,
   so any browser with SW blocked span forever.
2. **"Expect a pile of errors on first enable" (strict) — false.** Exactly **one** error.
   `Boolean(status)` does not narrow in TS; a direct null check does.
3. **The flaky test's two suggested causes were both wrong**, and the real one is now proven.
   It was *not* the real clock (validation accepts every value that default can take —
   checked across 75,292 timestamps spanning a year) and *not* the AsyncFeedback 5s timer
   (it only appends a sibling `<p>`). The test asserted a **transient loading skeleton**
   that disappears when the mocked fetch settles. Inserting one macrotask tick into the
   untouched original reproduces `1 failed | 31 passed` exactly. Fixed in `a1b517d`.
4. **"Playwright needs `npx playwright install chromium`" — stale.** `chromium-1243` is
   already in `~/Library/Caches/ms-playwright/`. `npm run test:e2e` runs as-is.

## Gotchas / learnings

- **Three MapLibre failures that report no error at all.** All fixed in `e395d94`, but the
  *pattern* matters: the basemap still tiles and the markers still mount, so a completely
  broken map looks like a working one. Symptom to watch for: `map.isStyleLoaded()` stays
  `false` and `queryRenderedFeatures` returns 0 while layers exist.
  - MapLibre **mutates the style object it is handed**. A module-level shared style left
    StrictMode's second map permanently unloaded. Build a fresh style per instance.
  - MapLibre resolves its worker via `new URL('./maplibre-gl-worker.mjs', import.meta.url)`,
    which no bundler can follow. **`?worker&url`** emits it with the `maplibre-gl-shared`
    chunk it imports; plain `?url` emits the worker alone and its sibling import falls
    through to the SPA handler, which answers a script request with `index.html`. Every
    GeoJSON source is parsed in that worker.
  - `vite preview` does **not** inherit `server.proxy`. A production build served locally
    could not reach the API at all — which also means the old handover's own "verify with
    `npm run preview`" instruction could not have worked. `preview.proxy` now added.
- **There is still no error boundary anywhere except around the map.** This already caused
  one white screen: offline, the non-precached map chunk's dynamic import rejects, and the
  throw blanked the whole page — `root innerHTML length -> 0`, wiping the written steps she
  saved for exactly that moment. Fixed in `ce72edd` with a boundary in `RouteMapPanel.tsx`
  and by skipping the map entirely for `snapshot.source === 'saved'`. **Any new lazy import
  or render throw in batches 1–3 has the same failure mode.** Consider a top-level boundary.
- **Assert durable outcomes, not transient ones, in tests.** That was the flake. If you add
  tests around loading/skeleton states in batch 3, this bites again.
- `journeyCoordinator.ts` is good code — a hand-rolled observable with a `generation`
  counter that correctly discards stale async responses. **Build on it, do not replace it.**
  Batch 5 says the same. Batch 4 warns: do not key/remount `JourneyProvider` for visual
  transitions or you will cause duplicate network requests.
- **`jsx-a11y` and `axe-core` are installed but never run.** Linter is `oxlint` and
  `.oxlintrc.json` enables only `react`/`typescript`/`oxc`; `e2e/home.spec.ts` does not
  import `AxeBuilder`. None of the genuinely good a11y work here is automatically verified.
- `api:generate` needs a live backend on `:8000`; nothing checks `generated.d.ts` for
  staleness. Current as of `ce72edd`.
- **Backend response schemas use Pydantic `extra="allow"`**, so `openapi-typescript` emits an
  index signature on all 54 response types. `tsc` will **not** catch a typo'd or renamed
  field on any API response, even with strict on.
- **OneMap token is a 3-day JWT — expires 2026-09-22 10:53 SGT** and will need re-minting.
  The LTA key was pasted into a chat transcript; worth rotating after the event.
- The Chrome extension (`mcp__claude-in-chrome__*`) is **not connected** — `tabs_context_mcp`
  returns "Browser extension is not connected". Use Playwright directly; it works well and
  gives reproducible evidence. Headless WebGL needs
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`.
- Node scripts run from `/tmp` cannot resolve `node_modules`; run throwaway Playwright
  scripts from inside `PS2/frontend` and delete them after.
- Fixtures are **rewritten at runtime** (`app/sources/base.py:_record`), dirtying the git
  tree during backend tests. `PS2_USE_FIXTURES=1` is **not** a hard offline switch.
- `PS2/references/` was once moved into `PS2/frontend/references/` by something outside the
  session. The six organiser files belong at `PS2/references/`.

## Important files

- `PS2/PS2_DESIGN_REFINEMENT_PLAN.md` — **the spec for this work.** 179 lines. Batches at
  §"Bounded implementation batches"; tokens at §"Design direction"; target wireframe at
  §"Target composition"; motion table (batch 4, deferred) at §"Motion specification".
- `PS2/PS2_INDEX.md` — §0 ranks every document's authority, §11 records every conflict and
  its resolution. **Read §0 before trusting any PS2 doc.**
- `PS2/PS2_README.md` — organisers' brief and rubric. **Outranks everything in repo.**
- `PS2/PS2_DECISION_RECORD.md` — D1–D14. **Binding.**
- `PS2/PS2_FRONTEND_REVIEW.md` — 7 findings. **#2 and #4 now closed**; #5 and #7 partial;
  **#1, #3, #6 still open** (two are High). Not in scope for batches 1–3 but do not
  regress them.
- `PS2/frontend/src/App.tsx` — `PageShell` is defined inline here; batch 2 extracts it.
- `PS2/frontend/src/features/journey/RouteOverview.tsx` — the schematic batch 3 replaces.
- `PS2/frontend/src/features/journey/legImpact.ts` — maps status onto legs (affected-leg
  logic the rubric scores). Reuse it for the SVG trace so diagram and map agree.
- `PS2/frontend/src/styles/` — `tokens.css` (18 lines), `global.css` (80), `native.css`
  (now ~118), `feedback.css` (9). The override tangle batch 2 untangles.
- `.claude/pr1-review-findings.md` + `.claude/repro/` — 34 backend findings and 47 repro
  scripts from PR #1 (merged). Historical.

## Relevant memory (inlined — these do NOT auto-reload after /compact)

**There is no project memory.** `~/.claude/projects/-Users-rayden-Desktop-projects-ltaxnebula-nebulax-lta/memory/`
exists but is **empty** — no `MEMORY.md`, no memory files. Nothing to carry over, and nothing
was silently relied upon. If you learn something durable this session, write it there.

## Verification

Environment is provisioned — venv (Python 3.14.5), npm packages installed, `PS2/.env` has
live LTA + OneMap keys and a VAPID pair, gitignored.

**The backend was already running on :8000 from a previous session** (`curl localhost:8000/`
returns 404, which is normal — check `/api/health`). Dev servers were left on :5190 and
:5173; preview on :4180 and :4173. Start fresh ones on other ports rather than trusting
these to still be alive.

```bash
cd PS2/backend && ./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd PS2/frontend && npm run dev            # proxies /api to :8000
curl -s localhost:8000/api/health         # expect fixtures_only:false, both credentials true
```

Gates — all five passed at `ce72edd`:

```bash
cd PS2/frontend
npm run typecheck     # exit 0, strict mode on
npm run lint          # oxlint, silent on success
npm run test:run      # 19 files, 49 tests
npm run build         # ~300 kB main / 93 kB gzip; precache 6 entries (317 KiB)
npm run test:e2e      # chromium already installed
```

Batch-specific gates are quoted under each batch above. Additionally:

- **Do not claim a reflow fix without the measurement.** Record the offending element and its
  computed size. The plan explicitly forbids an unverified root cause.
- **Inspect screenshots, do not just generate them** — check for clipped controls, crowding,
  inconsistent alignment and unexplained empty space.
- Verify the production build separately where the service worker is involved; dev-server
  checks do not establish production offline behaviour. Regression check for `ce72edd`:
  with the network disabled, a cold load of `/trip/:id` must return 200 and show the
  departure time, the offline-copy notice and the written steps, with **zero page errors**.
- Do not claim any of these passed without pasting the actual command output.
