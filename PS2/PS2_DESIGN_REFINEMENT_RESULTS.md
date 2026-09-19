# Design refinement: results

Evidence for `PS2/PS2_DESIGN_REFINEMENT_PLAN.md`, written as each batch lands. Branch
`feat/ps2-frontend-fixes`. Batches 1–3 are in scope; 4–6 are deferred by the user and are
**not** claimed here.

Nothing below is marked passed unless the command was run and its output read. Rows for work
that was not done say so.

## Batch status

| Batch | Scope | State |
|---|---|---|
| 1 | Reproduce and fix reflow | Done — `c9b9e52`, `4c00747` |
| 2 | Establish the visual system | Not started |
| 3 | Rebuild the journey composition | Not started |
| 4 | Add actual transitions | Deferred by the user |
| 5 | Finish loading and recovery | Deferred by the user |
| 6 | Verification and handoff | Deferred by the user; this document is started early |

## Batch 1 — reproduce and fix reflow

### What was reproduced

The plan records that earlier passes never reproduced the reported horizontal scrolling,
and forbids claiming an unverified cause. A sweep of **221 combinations** — 17 screen states
across 10 widths (320, 360, 375, 390, 430, 767, 768, 820, 960, 1280), plus 17 states at 320,
390 and 768 with a 32px root font — produced exactly **one** failure:

```
journey read from the offline copy @ 320 with 32px root font:
  scrollWidth 338 vs clientWidth 320 (over by 18px)
  section.journey-hero            box 20→338.45 (318.45px wide), computed width 318.453px, min-width auto, inside div.journey-layout [display: grid]
  p.offline-notice                box 20→338.45 (318.45px wide), computed width 318.453px, min-width auto, inside div.journey-layout [display: grid]
  p.form-error                    box 20→338.45 (318.45px wide), …
  section.status-panel.status-ok  box 20→338.45 (318.45px wide), …
  section.route-overview          box 20→338.45 (318.45px wide), …
  section.route-map               box 20→338.45 (318.45px wide), …
  section.timeline-panel          box 20→338.45 (318.45px wide), …
  div.offline-save                box 20→338.45 (318.45px wide), …
  a.text-button                   box 20→338.45 (318.45px wide), …
  footer.attribution              box 20→338.45 (318.45px wide), …
  control out of view: button.button.button-secondary "Save written steps offline" at 20→338.45
  control out of view: a.text-button "Journey settings" at 20→338.45
```

Every one of the eleven grid children is exactly 318.45px wide in a 280px content box, which
points at the track rather than at any single child.

### Measured root cause

Direct measurement in the failing state, not inference:

```
layout offsetWidth=280  clientWidth=320
min-content 318.45 :: p.offline-notice   :: "Offline copy · saved 2026-09-19T09:06:00+08:00 · plan generated 2026-0…"
min-content 311.81 :: section.journey-hero
scrollWidth before=338, after grid-template-columns:minmax(0,1fr) =326
```

`JourneyPage.tsx` printed `snapshot.receivedAt` and `snapshot.generatedAt` as raw ISO-8601.
`2026-09-19T09:06:00+08:00` is a single token with no soft-wrap opportunity, so
`p.offline-notice` has a min-content width of 318.45px. `.journey-layout` is a single-column
grid whose implicit track is `auto`; a grid item's automatic minimum size is its min-content
size, so the track grew to 318.45px and every sibling inherited it.

Capping the track alone left 326px, because the notice's own text still overflowed its box by
26px, of which 6px escaped the shell's 20px padding. Both the content and the mechanism needed
fixing.

### What changed

- `JourneyPage.tsx` formats both stamps with the existing `formatSingaporeDateTime`. The
  notice now reads `saved 19 September 2026 at 09:06`, which wraps and which this persona can
  read.
- `formatSingaporeDateTime` returns an unparseable value unchanged instead of letting `Intl`
  throw. The one screen that depends on it is the offline copy, and there is still no
  top-level error boundary, so a throw there blanks the written steps.
- `minmax(0, 1fr)` on the page-level grids and on the fixed-plus-flexible pairs
  (`.journey-leg`, `.endpoint`, `.how-it-helps li`); `min-inline-size: 0` on crowded flex rows.
- Nowrap chips (`.journey-date`, `.route-chip`, `.time-delta`, the section-heading link) hold
  their intrinsic width and their rows wrap under them. **This was found the hard way:**
  releasing `.time-delta` from its automatic minimum shrank it to 48px while its nowrap text
  stayed 109px, spilling across the page and regressing `alternatives @ 320` and `@ 390`.
- No `overflow-x: hidden` or `clip` on the document. The only clipping surfaces are
  `.journey-hero` and `.status-panel`, which clip absolutely-positioned decoration; measurement
  confirmed no text is clipped by either.

### The second P1: transient feedback rearranged unrelated content

Measured at 960px, `.journey-layout` children, before the fix:

| State | `.route-map` y | `.timeline-panel` y |
|---|---|---|
| ready | 581 | 1020 |
| status check failed | 462 | 901 |
| disrupted | 605 | 1044 |
| saved offline | 572 | 850 |

A failed status check inserts one `p.form-error` in the **first** column and moves the route
map, in the **second** column, by 119px. Only `.route-overview` was pinned
(`grid-row: 1 / span 2`); everything after it auto-placed, so any optional child renumbered the
rest.

Fixed by grouping the page into the five regions the plan names — summary (hero, notices,
status, warnings), overview, directions, actions — each holding a named `grid-template-areas`
slot, at mobile and desktop. An empty notices region collapses in place.

### Gate

Plan gate: *document scroll width ≤ client width + 1px and all important controls within
viewport bounds in every covered state.*

```
$ npm run test:e2e
  228 passed (1.1m)
```

227 of those are the reflow and region suites; 1 is the pre-existing home smoke test.

```
$ npm run typecheck      # tsc -b --pretty false — exit 0, strict on, now covers e2e/ too
$ npm run lint           # oxlint — silent on success
$ npm run test:run       # Test Files 20 passed (20) · Tests 52 passed (52)
$ npm run build          # built in 189ms · precache 6 entries (318.60 KiB)
```

### Honest limitations

- **Chromium only.** WebKit and Safari are not installed here, so the plan's "record any
  Safari/device limitation honestly" applies: **Safari remains unverified.**
- **200% text is emulated**, not set through browser chrome. The suite injects
  `html { font-size: 32px }`, which is what Chrome's "Very large" font setting does to the
  default. Values fixed in `px` — and most of this stylesheet is still in `px` — do not follow
  it, so this under-tests enlargement rather than over-tests it. Batch 2 moves type to `rem`,
  which will make the same suite stricter.
- **The native date/time control** is covered only as it renders in Chromium's mobile
  emulation. A real iOS wheel picker is not exercised.
- `body { min-width: 320px }` still prevents reflow below 320 CSS px. It was left alone; the
  plan lists 320 as the narrowest target.
- `.journey-layout`'s desktop second column keeps a `minmax(290px, .88fr)` floor. It passes at
  every tested width but it is a hard minimum, so it is recorded here rather than assumed safe.

### Files

New: `e2e/fixtures/payloads.ts` (frozen API payloads captured from the live backend on
2026-09-19), `e2e/fixtures/states.ts`, `e2e/fixtures/mockApi.ts`, `e2e/fixtures/overflow.ts`,
`e2e/responsive.spec.ts`, `e2e/journey-layout.spec.ts`, `e2e/screenshots.spec.ts`,
`tsconfig.e2e.json`, `src/features/journey/JourneyPage.test.tsx`.

Changed: `src/features/journey/JourneyPage.tsx`, `src/lib/singaporeTime.ts`,
`src/styles/global.css`, `src/styles/native.css`, `playwright.config.ts`, `package.json`,
`tsconfig.json`.

The e2e fixtures are now type-checked. They were not before — `e2e/` sat outside every
tsconfig project — and typing them immediately caught four fabricated payload shapes
(`Disruption`, `TripMap`, `NotOffered`).

### Screenshots

Regenerate with `npm run test:screens`; they are written to `PS2/evidence/screens/<width>/`
and gitignored rather than committed. 13 states at 320, 390 and 1280.

Inspected after the region refactor: mobile reading order and desktop two-column alignment are
correct, timestamps read in plain Singapore time, and no control is clipped. Three things the
plan already assigns to later batches are visible and **not** fixed here — full instruction
paragraphs used as bold headings, the joined stop-name paragraph in the route overview, and
unexplained empty space below the second column on desktop.

In the screenshot harness the route map shows its loading fallback, because the harness aborts
all OneMap tile requests so a slow tile server cannot be mistaken for a layout fault. That is a
property of the harness, not of the app.
