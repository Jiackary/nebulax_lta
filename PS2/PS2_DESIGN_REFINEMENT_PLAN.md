# Nusa: independent design review and implementation handoff

Reviewed 19 September 2026 against `66f7197` on `codex/frontend`.
This is a planning deliverable; application code was not changed in this pass.

## Outcome and priority

The current interface is a styled prototype, not yet the polished mobile product requested. The next pass must deliver three things together: reliable reflow, visible continuity between screens and states, and a distinctive transit visual language. More rounded cards and shadows alone do not satisfy the brief.

This plan supersedes the visual and motion portions of `PS2_UX_POLISH_PLAN.md`. Preserve its state-coherence and truthful-feedback requirements. Audit the earlier checklist against code: the results document is not evidence that every earlier item was completed. TTS, general routing, live location and geographic maps remain outside this frontend pass.

## Independent findings

| Priority | Evidence | Required response |
|---|---|---|
| P1 | User reports horizontal scrolling. Existing `e2e/home.spec.ts` measures overflow only on Home before navigating to Plan. | Reproduce the offending route/state/browser; add page and element bounds checks across the actual app. Do not mark the issue resolved from the home test. |
| P1 | `App.tsx` mounts separate `PageShell` instances under individual routes. There is no route-transition implementation. `Dialog.tsx` immediately unmounts on close. | Add a persistent shell and explicit page, dialog and content-reveal motion with lifecycle rules below. |
| P1 | `JourneyPage.tsx` mixes optional notices, errors, feedback, status and warnings directly into the layout grid. Desktop CSS pins the overview to rows 1–2 while other children auto-place. | Group semantic regions so transient feedback cannot rearrange unrelated content. Test all conditional states at both sides of the breakpoint. |
| P2 | `native.css` repeatedly overrides `global.css` and itself; tokens are redefined in multiple files. | Consolidate touched styles into one owner per component and one token source before further decoration. |
| P2 | RouteOverview draws uniform dots then concatenates stop names into a paragraph; the previous desktop screenshot shows excess empty height caused by stretching. | Build a labelled, mode-aware route diagram; keep its height content-driven and its names tied to nodes. |
| P2 | Full instruction paragraphs are bold headings; status, overview and timeline all compete as similarly weighted cards. | Use a clear decision hierarchy, short structured step titles, and lighter supporting information. Preserve every instruction and warning. |
| P2 | The hero replaced `timing_basis` with journey metrics, removing the visible explanation of timing. | Restore timing assumptions in a labelled disclosure; leave uncertainty and safety warnings outside it. |
| P2 | Home says “Your saved journey is ready” based only on an active ID; the form defaults to tomorrow at the current minute. | Use neutral “Open saved journey” until data is verified; require an explicit appointment time. |

### What was and was not reproduced

Read-only browser measurements in Chrome returned viewport/scroll widths of 320/320 for the settled fixture journey and appointment form. At a 768px viewport the journey reported a 753px document scroll width (no overflow). This does **not** disprove the reported problem: error/pending/offline states, other widths, large text and Safari were not covered by these samples. Exact user-device reproduction remains pending. Record the offending element and computed size when found; do not claim an unverified root cause.

Likely inspection points, not proven causes: automatic grid minimums; fixed marker plus `1fr` timeline tracks; nowrap appointment/time badges; native date/time controls; long IDs/timestamps/messages; negative header margins; optional grid children; modal content. The existing `body { min-width: 320px }` also prevents reflow below that CSS width.

## Design direction: a calm transit companion

Retain Nusa's forest green identity. Make the signature element a crisp departure board connected to a purposeful route ribbon. The first glance answers: when should I leave, what is the current confidence, and where am I going? The next glance exposes the steps. Treat the requested Awwwards standard as a craft bar: deliberate composition, typography, transitions and complete edge states. An award itself is not a measurable acceptance criterion.

- Canvas: warm off-white `#F4F5F0`; ink `#12271F`; secondary text `#536259`; forest `#0D6048`; a restrained warm accent `#D8A35F`. Validate actual contrast on all backgrounds. Reserve amber/red for meaningful warnings; colour always accompanies text/icons.
- Typography: locally hosted, licensed Manrope variable for the departure and headings; system sans for body. Include the font licence and `font-display: swap`. One WOFF2 asset, target <=60 KiB compressed; use system fallback if the asset cannot meet the budget. Body 18px with 1.5 line height; supporting text >=16px except attribution. Departure 56–72px, tabular numerals; headings 24–32px. Use rem-based values so text enlargement works.
- Spacing: 4/8/12/16/24/32/48px scale. Mobile gutter 16px at 320px, 20px from 390px. Maximum reading width around 42rem; use a deliberate secondary column only when both columns fit, initially at 960px.
- Surfaces: one dominant dark departure surface, one lightly bordered status region, a route diagram on the canvas, and a mostly borderless timeline. Avoid making every block an elevated card. Radius 16px for controls, 24px for the primary surface. One subtle shadow tier.
- Controls: consistent inline SVG icons, 48px targets, visible focus, text labels for important actions. Replace the unicode refresh symbol with a labelled “Refresh” control in the status region. Hover treatment must not be the only feedback available on touch.
- Remove decorative button sheen and repeated background grids/circles if they compete with the diagram. No scroll hijacking, custom cursor, autoplay cinematic intro or animation that postpones access to directions.

## Target composition

```text
MOBILE / JOURNEY                 HOME / NO ACTIVE PLAN
‹ Home     Journey     Settings  Nusa                  Settings
                                Plan your next
Hospital visit · Mon 21 Sep      hospital visit
┌──────────────────────────┐    Your usual route
│ Leave by                 │    Bedok
│ 08:17                    │      · walk / East–West Line
│ Arrive 09:01–09:12        │    SGH · Block 3
│ 50 min · 707 m walking    │
└──────────────────────────┘    [ Plan journey             → ]
Status + checked time [Refresh]  Currently Bedok → SGH
Warning, when applicable

YOUR ROUTE
Home ··· Bedok ══ Outram ··· SGH
Labels wrap below their nodes
Schematic · not to scale

JOURNEY STEPS
1  Walk to Bedok MRT      7 min
   Exit B · 286 m
   Essential instruction
   More details ▾
2  East–West Line        31 min
   Towards Tuas Link · 11 stops
3  Walk to SGH           10 min
   Exit 6 · lift to street level

Timing assumptions ▾
[ Save written steps offline ]
```

On desktop align departure/status with the route overview; give the overview a readable composition rather than distributing four lines through a large empty card. Steps remain in a bounded reading column. Conditional warnings occupy a named full-width region ahead of directions. At narrow widths, the diagram may use a vertical orientation; it must never require horizontal scrolling. No fake geography or moving train position.

## Motion specification

Implement a small reusable motion layer using CSS and, when needed, the browser Web Animations API. No animation runtime dependency. Use tokens: press 100ms, exit 140ms, enter 240ms, route reveal 420ms; easing `cubic-bezier(.22, 1, .36, 1)` for entrance and `cubic-bezier(.4, 0, 1, 1)` for exit.

| Event | Visible choreography | Lifecycle / acceptance |
|---|---|---|
| Forward route navigation | New main content fades in and translates up 8px over 240ms; header stays still. | URL and focus update immediately. Animate the page wrapper only on location changes, never request-state changes. No blank frame. |
| Browser back | Prior content fades in, maximum 4px translation, 180ms. | Restore recorded scroll keyed by history entry where possible. Direct entry/forward navigation goes to top. No focus-induced jump. |
| First journey data available | Skeleton region swaps to ready content with a 180ms fade; departure is first, overview follows by at most 60ms. | Reserve approximate geometry; all information exists immediately. Do not replay on refresh or every provider render. |
| Route diagram | Connectors reveal once over 420ms using SVG stroke dash offset. Walking dotted, rail solid. | Only on first successful plan presentation or actual plan change. Explicitly schematic. Reduced motion renders the full line immediately. |
| Refresh | Button acknowledges press; icon rotates only while the real request is pending; thin indeterminate line sits inside status. | Preserve directions, focus and scroll. Stop motion on success/failure/unmount. Update status copy once per real phase. |
| Save offline | Stable-width button pending state, then check icon and persistent saved time. | Success only after storage succeeds. Failure stays adjacent to the action. |
| Modal/sheet | Backdrop fades 160ms; sheet rises 20px over 240ms; closes in 140ms. | Manage mounted/open/closing states. Background inert and scroll locked while mounted; restore focus once on completed close. Escape and rapid reopen cancel stale animations. |
| Press | Scale .985 over 100ms on enabled actions; optional subtle colour change. | No hover-only affordance; no transforms on disabled controls. |

Reduced motion: no translate, scale, line drawing, spinning or pulsing; immediate state change or <=80ms opacity only. No minimum request duration, invented percentage or fake loading stage. Animations must be interruptible and cleaned up. Avoid animating height, filter, blur and shadows per frame. Text must remain available if animation setup fails.

## Bounded implementation batches

Complete in order. One coherent Conventional Commit per batch or smaller fix. Preserve existing changes; do not push unrelated work. All paths below are under `PS2/frontend` unless stated otherwise.

### 1. Reproduce and fix reflow

Files: `src/styles/global.css`, `native.css`, affected components, `e2e/responsive.spec.ts`, typed fixtures in `e2e/fixtures/`.

- Establish deterministic fixtures for journey ready/loading/error/stale/failed-replan, alternatives and saved states. Capture the actual offending bounding box, CSS width and nearest layout ancestor before patching a reproduced issue.
- Test 320, 360, 375, 390, 430, 767, 768, 820, 960 and 1280 CSS-pixel widths. Test 200% text enlargement, long destination names and timestamps, and the native date/time control.
- Use explicit `minmax(0, 1fr)` tracks and `min-inline-size: 0` at shrinkable grid/flex boundaries. Allow semantic text wrapping and stack crowded header/footer rows. Limit `overflow-wrap: anywhere` to content that truly needs it.
- Refactor journey into summary/status, notices, overview, directions and actions regions. Explicit grid areas for desktop; no conditional child auto-placement dependency.
- Do not hide document overflow with `overflow-x: hidden/clip`. Clip only intentionally decorative child surfaces. No truncated essential instructions.
- Gate: document scroll width <= client width + 1px and all important controls within viewport bounds in every covered state. Record any Safari/device limitation honestly.

### 2. Establish the visual system

Files: `src/styles/tokens.css`, `global.css`, `native.css`, `src/App.tsx`; extract `src/components/PageShell.tsx`.

- Consolidate competing declarations into readable blocks; tokens belong in tokens.css. Retain functional state classes and reduced-motion rules.
- Implement palette, typography, spacing and surface rules above. Apply to Home, Plan, Journey, Options, Settings and dialogs, not only the journey hero.
- Contextual headers identify each screen and back destination. Home avoids readiness claims based solely on an ID. Plan requires an explicit chosen time and keeps errors tied to the appropriate field; network failures must not mark valid date input invalid.
- Gate: screenshot each page at 320 and 390px plus desktop; verify 48px targets, contrast, large text, wrapping and one obvious primary action.

### 3. Rebuild the journey composition

Files: `JourneyPage.tsx`, `RouteOverview.tsx`, `JourneyTimeline.tsx`, `JourneySkeleton.tsx`, `StatusPanel.tsx` in `src/features/journey/`.

- Implement the wireframe using actual plan fields. Keep full backend departure label accessible; do not rely on regex stripping English copy as a time parser. Restore timing methodology in a disclosure.
- Replace joined stop-name paragraph with a responsive SVG route trace and adjacent HTML labels. Support zero/one/many legs, long names and missing geometry. Never require real map tiles.
- Derive short step titles from structured mode/from/to/line data; retain original instructions as readable body text. Exit, lift and safety details remain exposed. Do not guess structured facts by parsing prose.
- Reduce repeated metadata; secondary details can be expanded with native disclosures. Current/fresh, retained/stale and unavailable states must remain visually distinct.
- Gate: ready, stale, warning, no-overview and failed-replan screenshots; verify no information is lost and no retained plan is falsely presented as confirmed.

### 4. Add actual transitions

Files: persistent shell/routing in `src/App.tsx`, new `src/styles/motion.css`, small `src/components/PageTransition.tsx` if useful, `Dialog.tsx`, journey and offline controls.

- Follow the motion table exactly. Keep `PageShell` mounted above changing route content. Do not key/remount `JourneyProvider` for visual transitions or cause duplicate network requests.
- Implement entrance motion as the baseline. Outgoing-page screenshots or a View Transition enhancement are optional only after baseline behaviour passes; do not retain two interactive pages or block navigation waiting for exit.
- Preserve route focus semantics and back scroll; background status updates never trigger page transitions. Scope animations to explicit route/snapshot identities.
- Implement dialog close lifecycle and background inertness carefully; test Escape, tab containment, return focus, rapid close/reopen and navigating away.
- Gate: short recordings of Home → Plan → Journey → Options → Back, refresh, offline save, dialog open/close and reduced motion. A static screenshot cannot prove this batch complete.

### 5. Finish loading and recovery

Files: `AsyncFeedback.tsx`, API-facing page components, skeletons, existing journey coordinator only where necessary.

- Preserve established coherent snapshot/generation guards. No broad rewrite of working backend/state infrastructure for appearance.
- Reserve loading regions, avoid fast-request flicker, show slow-request copy at five seconds, and clear pending feedback on every terminal outcome.
- Initial retryable failure offers Retry and Home; missing/expired journey offers Plan new journey. Recoverable failure preserves entered form data or qualified prior directions.
- Test 503, timeout, status failure, effective-plan failure, empty alternatives and local-storage failure using interception. Do not confuse a successful fixture API call with production integration verification.
- Gate: each asynchronous action has idle, pending, success and failure presentation; no impossible ready claims or permanent spinner.

### 6. Verification and handoff

- Run `npm run lint`, `npm run typecheck`, `npm run test:run`, `npm run build`, `npm run test:e2e`. Use installed Chrome via `PLAYWRIGHT_CHROME_EXECUTABLE` if bundled Chromium is absent.
- Add meaningful tests for reflow, interrupted animations/focus and request-state transitions; avoid tests that only assert class names. Existing home smoke coverage is insufficient.
- Run existing axe tooling on representative ready, pending, error and dialog states. Manually check keyboard, 200% text, reduced motion and touch-sized controls. Test WebKit if available; otherwise state it remains unverified.
- Capture mobile and desktop screenshots plus the motion recordings. Inspect them, don't just generate them. Check every screenshot for clipped controls, crowding, inconsistent alignment and unexplained empty space.
- Measure production preview performance under a documented mobile viewport/CPU setting: target CLS <=0.1 and no motion-related main-thread task >50ms. Record actual values and trace conditions. Do not infer performance from bundle size alone. No animation runtime; font budget above; keep added compressed JS <=5 KiB unless justified.
- Verify production service-worker/offline navigation separately if touched; dev-server checks do not establish offline production behaviour.
- Create `PS2/PS2_DESIGN_REFINEMENT_RESULTS.md`: commit IDs, command outcomes, reproduction/fix evidence, screenshot/recording paths, measured performance, unresolved defects and unavailable device checks. Never label untested rows passed.

## Smaller-model execution prompt

> Implement PS2/PS2_DESIGN_REFINEMENT_PLAN.md in its six ordered batches on the current frontend branch. Preserve existing work and the earlier journey state-coherence contracts. First reproduce and fix horizontal overflow across routes and transient states; do not conceal it with global overflow clipping. Then implement the specified visual system, labelled route diagram, persistent-shell page transitions, dialog lifecycle and real loading/recovery behaviour. Use the exact motion timings and reduced-motion fallback. Make frequent atomic Conventional Commits. Run the prescribed checks, inspect screenshots, record motion demonstrations and write PS2/PS2_DESIGN_REFINEMENT_RESULTS.md with honest evidence and remaining limitations. Complete the scoped frontend work; do not implement TTS, geographic maps or broader backend routing. Do not describe a static restyle as completed transitions.

The batches are suitable for a smaller coding model. Ordinary CSS and component choices are specified here. Escalate only a concrete state-contract conflict or repeatedly failing browser-specific issue, with reproduction evidence and attempted fixes.
