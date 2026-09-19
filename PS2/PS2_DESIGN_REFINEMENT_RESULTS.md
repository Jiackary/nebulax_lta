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
| 2 | Establish the visual system | Done — `27f7db9` |
| 3 | Rebuild the journey composition | Done — `27f7db9` |
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

## Batches 2 and 3 — the visual system and the journey composition (`27f7db9`)

Run as one commit rather than two. The batches were designed to be separable, but the
composition work in batch 3 is what the stylesheet restructure in batch 2 exists to carry, and
splitting them would have produced one commit whose screenshots showed a half-restyled page.
The user asked for the two to run back to back with a single report; this is that report.

Read against a stated priority of **mobile**. Everything below was judged at 320 and 390 CSS
pixels first; the desktop layout is checked but is not what the decisions optimise for.

### Gates

All five run at the committed tree. Output, not assertion:

```
npm run typecheck   exit 0, silent (tsc -b --pretty false, strict, covers e2e/)
npm run lint        exit 0, silent (oxlint)
npm run test:run    Test Files 20 passed (20) · Tests 55 passed (55)
npm run build       precache 7 entries (347.41 KiB)
npm run test:e2e    228 passed (1.1m)
npm run test:screens 39 passed — 13 states x 320/390/1280
```

The precache went from 6 entries to 7 and from 318.60 KiB to 347.41 KiB: the added entry is
the 24,576-byte Manrope woff2, and `injectManifest.globPatterns` was widened to include
`woff2` so that the saved journey opens offline with the font it was laid out in.

### Stylesheet restructure

`global.css`, `native.css` and `feedback.css` are deleted. `src/styles/index.css` is the only
stylesheet `App.tsx` imports, and it `@import`s four files in a fixed order:

| File | Owns |
|---|---|
| `tokens.css` | every colour, space, radius, shadow, type size and duration, defined once |
| `base.css` | the `@font-face`, reset, document, element type scale, focus, reduced motion |
| `layout.css` | app shell, header, page column, the journey's named regions, reflow guards |
| `components.css` | one block per component |

`native.css` had stacked three passes that each overrode the one before, and tokens were
redefined in three files. No component now has more than one owner.

### Rem-based sizing, and the four reflow faults it exposed

Sizes were almost entirely `px` before, which is why the existing 200%-text tests passed:
`px` does not respond to root font size, so the tests were not measuring anything. Converting
to `rem` made them measure, and they failed. Each failure was real. Measured with
`e2e/fixtures/overflow.ts`, which reports the offending element, its box, its computed width
and its layout ancestor:

**1. Nested `auto` grid tracks, plan form at 320px / 32px root font — 64px over.**

```
plan form @ 320 with 32px root font: scrollWidth 384 vs clientWidth 320 (over by 64px)
  form.appointment-form box 32→384.42 (352.42px wide), computed width 352.422px,
    min-width auto, inside section.content-panel [display: grid]
  div.form-field box 32→384.42 (352.42px wide), computed width 352.422px,
    min-width auto, inside form.appointment-form [display: grid]
  input#appointment-at box 65→351.42 (286.42px wide), computed width 286.422px,
    min-width 0px, inside div.form-field [display: grid]
```

A grid container with no explicit template gets an implicit `auto` track whose automatic
minimum is the min-content size of its widest child. The native `datetime-local` control has
an intrinsic minimum of about 286px at 32px text, and that floor propagated up through four
nested `auto` tracks to the shell. Fixed by giving every grid container in the app an explicit
`minmax(0, 1fr)`, not only the ones that had overflowed so far.

**2. The fieldset's UA minimum — 13px over.**

```
plan form @ 320 with 32px root font: scrollWidth 333 vs clientWidth 320 (over by 13px)
  fieldset.form-field box 34→332.7 (298.7px wide), computed width 298.703px,
    min-width min-content, inside form.appointment-form [display: grid]
```

`min-width: min-content` is a UA style on `fieldset` that the `minmax(0, 1fr)` track does not
release; only `min-inline-size: 0` on the element itself does.

**3. An unwrappable step-head row, journey at 390px / 32px root font — 42px over.**

```
journey ready, status current @ 390 with 32px root font: scrollWidth 432 vs clientWidth 390
  span.journey-duration box 328.08→431.92 (103.84px wide), computed width 103.844px,
    min-width auto, inside div.journey-step-head [display: flex] — "10 min"
```

`.journey-step-head` holds the step title and its duration. The duration is `white-space:
nowrap` by design — "10 min" must not break — and the row had no `flex-wrap`, so the title's
min-content plus 103.84px of unbreakable chip could not fit. Fixed by wrapping the row and
keeping the chip at its intrinsic width, which is the same resolution batch 1 recorded for
`.time-delta`: a nowrap chip needs `flex: none` and a wrapping parent, never `min-inline-size:
0`.

**4. The departure clock, journey at 320px / 32px root font — 104px over.**

```
journey ready, status current @ 320 with 32px root font: scrollWidth 424 vs clientWidth 320
  h1#journey-heading.departure-time box 80→372.55 (292.55px wide),
    computed width 292.547px, min-width auto, inside section.departure-card [display: grid]
```

`clamp(3.5rem, 15vw, 4.5rem)` resolves its lower bound against the root font, so at 200% text
the clock was 112px and "09:22" was 290px of glyphs inside a 208px column. Changed to
`min(4.5rem, 20vw)`.

**This is a recorded trade-off, not a clean fix.** The departure clock no longer grows under
text-only enlargement. It is bounded by the viewport instead: 64px at 320px, 72px from 360px.
Everything else on the page — including every other heading, all body copy and all supporting
text — still scales normally, and the page reflows without horizontal scrolling at 200%. The
clock is already about four times body size. A reader who needs it larger still gets a larger
number from browser page zoom, which scales `vw` units; they do not get one from text-only
zoom. If that is judged unacceptable the alternative is a smaller base clock, not a rem-based
one, because a rem-based clock at 200% cannot fit a 320px screen at any legible size.

### Composition

- **Departure.** One dominant dark surface carrying `Leave by`, the clock, the arrival window
  and the two metrics. The clock is formatted from `summary.leave_by` by a new
  `formatSingaporeClock`. `JourneyPage.tsx` previously did
  `plan.summary.leave_by_label.replace(/^Leave at\s*/i, '')` — a time parser built out of
  English copy. The full backend label is still in the DOM and is what assistive technology
  announces from the `h1`.
- **Route trace.** `RouteOverview.tsx` is rebuilt as an SVG trace: one `<line>` per leg inside
  a viewBox stretched to the container, dotted for walking and solid for rail, with HTML
  labels in a grid whose columns line up with the node positions by construction. Stroke width
  is held constant with `vector-effect="non-scaling-stroke"` and the dash pattern is expressed
  against `pathLength`, so the walking dots stay evenly spaced at any width instead of
  becoming one long dash. It needs no map tiles and handles zero, one or many legs.
- **The trace distinguishes the affected section.** It reads the same `legImpact.ts` the map
  reads, so the two pictures of one journey cannot disagree, and the schematic still shows the
  disruption when the map cannot draw — offline, or when tiles fail. Affected legs are dashed
  in the map's own warning colours (`#b26a00`, `#b3261e`, now tokens). Colour is never the
  only carrier: the reasons are written once under the trace, deduplicated, because one lift
  outage touches both legs that meet at the station.
- **Step titles** come from `mode`, `to` and `line`. `JourneyTimeline.tsx:17` previously put
  the whole instruction paragraph in an `<h3>`. The instruction is kept verbatim as body text
  and is never parsed for facts. `placeName.ts` shortens long postal names for display only.
- **`timing_basis` is restored** in a `<details>` disclosure, together with the planned arrival
  range and buffer. Uncertainty and safety warnings stay outside it.
- **Repeated metadata reduced honestly.** "Step-free access checked" appeared on every step.
  It is now stated once when every leg is confirmed, and the moment any leg differs every step
  carries its own label again, so the exception cannot hide.
- **Refresh** is a labelled control in the status region beside the checked time, replacing the
  `↻` orb in the hero. Its icon turns only while a request is actually pending.
- **Home** no longer says "Your saved journey is ready" from an id alone; it says "You have a
  saved journey" and the action is "Open saved journey".
- **The appointment form** starts empty and requires an explicitly chosen time. Field errors
  and request errors are separate pieces of state, so a failed network call can no longer mark
  a valid date invalid.

### Defects found by inspecting the screenshots, and fixed

None of these were in the plan; all three were visible only once the images were looked at.

- The `<legend>` straddled its card border and spilled past the rounded corner. HTML picks the
  *rendered legend* — the one in the notch — as the first `legend` child whose float is `none`;
  giving it a float disqualifies it, and the float itself is then ignored because a child of a
  grid container is never floated.
- At 320px the Options header ran the back label into the screen title with no gap:
  "JourneyOther ways to travel". The title is now "Options" and both header labels hold one
  line and lose their tail rather than growing into each other.
- `OptionCard.tsx` rendered **"About undefined minutes"** for the taxi option.
  `option.duration_min` is *absent*, not `null`, when the backend cannot time an option, and
  the code compared against `null` alone.

Also changed on inspection: the offline copy's accompanying message was painted in the
critical red reserved for something being wrong with the journey. Reading the saved copy with
no network is the case the feature exists for, and the notice above it already says so, so it
is now a caution.

### Live verification

The screenshot harness aborts OneMap tile requests, so it cannot prove the map renders. Driven
separately against the live backend on `:8000` through a dev server on `:5199`, Pixel 5
viewport, SwiftShader:

```
trip t_hMf_30u4prHb4K5Fo8EHPA (created live, not a fixture)
onemap tile requests: 4   (12/3229/2033, 12/3230/2033, 12/3229/2032, 12/3230/2032)
container 351x288 · canvas 351x288
page errors: none
```

The OneMap Grey basemap draws, the route is overlaid in forest green with the destination
marker, and the "OneMap © contributors | Singapore Land Authority" attribution is present, as
is the backend's OpenStreetMap / LTA DataMall / data.gov.sg attribution in
`.journey-actions`. Screenshot at `/tmp/live-journey.png` (not committed).

The rail leg draws as a straight line between its endpoints because the backend sends two
coordinates for it. That is the data, not the renderer.

### Not done

- **`e2e/a11y.spec.ts` was not written.** `@axe-core/playwright` and `axe-core` are installed
  and have still never been run. The 48px touch targets are set from a `--target` token and
  are visible in the screenshots, but they are **not** machine-verified, and no automated
  contrast or landmark check has been run against any state. This is the largest gap in this
  batch and it is a deliberate one, taken under submission time pressure.
- Batches 4, 5 and 6 remain deferred.
- WebKit remains unverified. Everything above is Chromium.
- `PS2_FRONTEND_REVIEW.md` findings #1, #3 and #6 are still open; they were not regressed but
  they were not addressed.
