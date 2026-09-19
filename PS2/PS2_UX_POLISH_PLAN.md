# Nusa UI/UX polish — independent review and implementation handoff

> **Superseded in part — reconciled 19 Sep 2026; see `PS2_INDEX.md` §11.**
> `PS2_DESIGN_REFINEMENT_PLAN.md` supersedes the **visual and motion** portions of this
> document. Its state-coherence and truthful-feedback requirements still stand.
>
> One instruction below is withdrawn: "Do not... select a map-tile provider as part of UI
> polish. Those programmes remain in `PS2_CONSOLIDATED_ROADMAP.md`." That roadmap's ten
> tasks contain no map task, so the map fell through the gap between the two documents.
> The route map is in scope per `PS2_DECISION_RECORD.md` D14 — see `PS2_INDEX.md` §11.2.

**Goal:** Make the mobile journey companion feel composed, responsive and dependable through clear hierarchy, stable layouts, useful route context and complete loading/recovery feedback.

**Review basis:** `codex/frontend`, frontend commit `535bdab`, plus the working-tree documentation. Browser inspection covered home, appointment form, failed planning and empty settings. Source inspection covered journey, coordinator, alternatives, offline save, API timeout and design styles. Planning in the running preview returned “The service is temporarily unavailable”; the successful journey and alternatives observations below are source-based, not claims of live browser verification. No real-device, screen-reader or performance benchmark was performed in this review.

**Execution:** Read this file and `PS2_FRONTEND_REVIEW.md` first. Implement the batches in order, using executing-plans, one coherent commit per batch. The decisions below are settled for this pass. Do not expand routing, implement speech, or select a map-tile provider as part of UI polish. Those programmes remain in `PS2_CONSOLIDATED_ROADMAP.md`.

## 1. Independent assessment

The calm green palette, readable system type, grouped route ticket and large primary button are worth preserving. The interface now resembles a mobile utility. It still feels like a collection of rendered pages because its state changes have little spatial continuity or explanation.

| Priority | Finding and evidence | Required outcome |
|---|---|---|
| P1 | `JourneyPage.tsx` replaces the initial layout with a heading and paragraph. `AlternativesPage.tsx` shows only a heading while loading. | Content-shaped skeletons preserve structure and explain what is being requested. |
| P1 | `AppointmentForm.tsx` only changes its button label during submission; failure produces generic text. Live preview reproduced the failure. | Immediate acknowledgement, visible ongoing activity, slow-request guidance, and retry with entered values intact. |
| P1 | Coordinator can preserve an old all-clear after refresh failure; missing status says “Checking” even when no request is running. | Explicit request state and freshness; old data must be visibly qualified. This precedes decorative polish. |
| P1 | No route overview is rendered; the journey is a long textual stack. | Lightweight diagram for walk → train → walk plus leg details. No implied live location. |
| P2 | Home uses only the active trip ID to say “Your saved journey is ready.” It cannot establish appointment time, expiry or route validity. | Show actual appointment/departure facts when available; otherwise say “Open saved journey.” |
| P2 | Header retains the brand and settings link on all pages, including settings. Back links have generic names. No explicit route focus/scroll management exists in `App.tsx`. | Contextual page titles, labelled back destinations, keyboard focus management and intentional scroll restoration. |
| P2 | The appointment form defaults to tomorrow at the current minute; “Arrival buffer” is technical and shelter copy is long. | Clear appointment choice, human summary of the chosen date/time, and “Arrive early by” wording. |
| P2 | Refresh, save, retry and missing-trip flows use different message patterns. Successful offline save is not restored as persistent saved state. | Shared asynchronous action patterns with operation-specific success and recovery. |
| P2 | Every journey leg displays a similar density of instruction, timing and accessibility copy. | Scannable mode/endpoint heading, essential exit instruction, secondary detail disclosure; warnings always exposed. |
| P2 | `native.css` overrides `global.css`, including tokens and typography. | Consolidated tokens and component ownership, preserving existing appearance before introducing refinements. |

Do not treat these priorities as findings of data loss or measured accessibility failure. The existing offline and push correctness findings remain in the separate review and must be addressed where they overlap this plan.

## 2. Design direction and constraints

Design for Mdm Lim using one hand, occasionally in glare or with a weak connection. The screen should answer: **When do I leave? Can I use this route? What should I do next?**

- Keep the existing deep green accent, warm pale background, white grouped surfaces and system font. Avoid a new brand, glass layers, external fonts or a new animation framework.
- Use one primary action per screen. Do not add a bottom tab bar to a product with only one active journey.
- Set body/instruction text to 17–18px with 1.45–1.55 line height; secondary content at least 15px. Use 14px only for nonessential metadata.
- Use a 4px spacing base: 8 within related content, 16 within groups, 24 between groups, 32 between major sections. Horizontal gutters: 16px at 320px, 20px from 375px; maximum reading width 640px.
- Use 16px control radius, 20px section radius and 24px summary radius. Borders define surfaces; shadows are reserved for a floating action dock or dialog.
- Touch targets are at least 48×48px; primary actions at least 56px high. No information may require hover or gesture discovery.
- Fix and measure normal-text contrast at 4.5:1, large text and meaningful UI graphics at 3:1. Do not assume muted green already passes every background.
- Add `scroll-padding-top` and focus offset for sticky chrome. A sticky action area must not cover content, validation, the keyboard, or the last focused control.

## 3. Screen wireframes

Wireframes show hierarchy, not exact colours. Use flexible content heights; the dimensions below apply only to the route illustration and loading reserves.

### Home — active appointment

```text
┌──────────────────────────────────┐
│ Nusa                  [Settings] │
│ Your next appointment            │
│ Sun, 20 Sep · 10:30 am            │
│ Singapore General Hospital       │
│ Block 3                          │
│                                  │
│ Leave by                         │
│ 9:19 am                          │
│ Planned arrival 10:03–10:14 am    │
│ Last checked 8:42 am · [Refresh]  │
│                                  │
│ Home ○·· EW5 ═════ EW16 ··▣ SGH  │
│ Walk      East–West Line   Walk  │
│                                  │
│ [       Open journey        →  ] │
│             New appointment      │
└──────────────────────────────────┘
```

Only display leave/arrival times from a matching saved or network plan. Tag locally restored information “Saved plan”; this is not a fresh status check. Without an active trip retain the existing route ticket, replace promotional copy with “Plan your next hospital visit,” and show one Plan journey action. Empty settings should show useful app information and a plan action, without a settings button linking to the same page.

### Planning — pending state within the same screen

```text
┌──────────────────────────────────┐
│ ‹ Home       New appointment     │
│ Bedok → SGH, Block 3             │
│ [ Appointment date          ]    │
│ [ Appointment time          ]    │
│ Sunday, 20 September · 10:30 am   │
│ Singapore time                   │
│ [✓] Prefer sheltered walking     │
│ Arrive early by [15 minutes ▾]   │
│                                  │
│ ━━━━━━━━ moving activity ──────  │
│ Preparing your journey…          │
│ Finding a route and leave time.  │
│ [       Planning…           ◌  ] │
└──────────────────────────────────┘
```

Use native date/time controls with explicit labels and a readable confirmation sentence. Do not claim “Checking lifts” or “Finding exits” as completed substeps during the single POST request: the API does not stream those events. Disable edits only while the submitted request is active, prevent duplicate submit, preserve all values on failure. Default date can remain tomorrow; require explicit time entry rather than silently accepting the current minute as the appointment.

### Journey — initial skeleton then settled view

```text
LOADING                           READY
‹ Home       Journey              ‹ Home       Journey
┌──────────────────────┐          ┌──────────────────────┐
│ Leave by             │          │ Leave by             │
│ ███████████          │          │ 9:19 am              │
│ █████████████████    │          │ Arrive 10:03–10:14   │
└──────────────────────┘          └──────────────────────┘
◌ Loading your saved route…       ✓ No reported disruption
┌──────────────────────┐          Checked 8:42 am [Refresh]
│ ○····○════○····▣     │          ┌──────────────────────┐
│ Route overview       │          │ Home··EW5══EW16··SGH │
│ ██████████████       │          │ Schematic · not to   │
└──────────────────────┘          │ scale                │
1  █████████████████              └──────────────────────┘
   ██████████                     1 Walk to Bedok MRT
2  █████████████████                Exit B · 7 min
   ██████████                     2 Train to Outram Park
                                  …
                                  [Save for offline use]
```

The skeleton contains no fabricated exits, timings, status badges or geographic streets. Its overview occupies the same 180–220px region as the final schematic. A route warning goes above the illustration and steps. A background refresh keeps the existing layout and scroll position; use a slim activity line inside the status section rather than returning to the initial skeleton.

### Failure and recovery

```text
! We couldn't update your journey
  Showing the plan saved at 8:42 am.
  Current conditions are unavailable.
  [Try again]       [Use saved steps]
```

Only offer saved steps when a matching bundle exists. On first-load failure without a plan, render a compact explanatory panel in the reserved content region with Retry and Back to home. On a confirmed missing/expired trip, show Plan new journey; repeating the same missing-trip fetch is not a useful primary action. A failed create request says “We couldn't prepare your journey. Your appointment details are still here.” Do not imply a server-side trip was definitely not created after a network timeout.

## 4. Loading and feedback contract

| Operation | Immediate feedback | Pending copy | Success | Failure/recovery |
|---|---|---|---|---|
| Create trip | Button disabled on first click; stable width and spinner | “Preparing your journey…” | Navigate with returned plan as initial data; then check status | Preserve form; Try again, no automatic POST retry |
| Initial plan fetch | Render journey skeleton | “Loading your saved route…” | Reveal available plan, explicitly unconfirmed until status finishes | Retry or matching saved bundle |
| Status request | Retain plan, activity strip in status area | “Checking current conditions…” | Fetch effective plan before confirming directions | Qualify retained status with last known time |
| Effective plan fetch | Keep the activity strip | “Updating your directions…” | Commit plan/status together | Warn that directions aren't confirmed against the new check |
| Alternatives | Two neutral option-shaped skeletons, no invented choices | “Checking other ways to travel…” | Render actual options or explicit empty result | Retry options, retain route link |
| Offline save | Disable only save action | “Preparing offline steps…” then “Saving on this device…” at the actual storage step | Check icon, “Saved at 8:42 am”; persistent state | Distinguish network preparation from local-storage failure |
| Route schematic | Reserve container, draw from plan when available | “Loading route overview…” only while work is pending | Label “Schematic · not to scale” | “Route overview unavailable. Written steps are below.” |

Timing rules:

- Acknowledge user input immediately. Delay animated skeleton/shimmer appearance by about 150ms to avoid a flash on fast completion, but reserve layout immediately.
- Never add minimum wait time just to show an animation. Finish as soon as real work finishes.
- At 5 seconds, add “This is taking longer than usual. You can stay on this screen.” This describes elapsed time, not an invented network diagnosis.
- Keep the existing per-request 20-second timeout unless a measured operation requires a change. A multi-request refresh may take longer overall; test this explicitly rather than assuming the whole flow times out in 20 seconds.
- Use indeterminate progress bars for requests with unknown total work. Omit `aria-valuenow`; give the progress indicator an accessible label. No percentage or staged completion without measurable events.
- A single polite live region announces real phase transitions; do not announce every animation frame. Failures use one alert, avoiding simultaneous duplicate announcements.
- Every timer and late response is scoped to the request generation/trip; leaving the screen or changing trip prevents obsolete completion from updating UI.

## 5. Route illustration and future map loading

Implement a local SVG schematic first. It gives useful orientation with negligible bundle/network cost and works offline. Derive names, modes and ordering from `TripPlan.legs`, with walking dotted lines and rail solid lines plus text labels. Do not draw the rail leg as a geographically precise line: the current backend rail geometry is only endpoint coordinates. Wrap long names and preserve an accessible textual equivalent. No pulsing “you are here” dot, moving train, or travelled-leg completion; there is no progress tracking.

Offer “View journey steps” as an anchor to the textual timeline. If selecting a schematic leg is included, it only scrolls/focuses that leg; it must not imply starting live navigation. The schematic cannot certify accessibility; warnings and unknown access remain explicit in the steps.

A geographic map is a separate optional batch after a provider/licence decision. Its future container has independent `loading | ready | unavailable | offline` state. Reserve a neutral map-shaped grid labelled “Loading map”; render known route data separately only when accurate. Tile failure must not hide directions or restart the entire journey. No simulated cartography, fake tile network requests or offline tile caching without the provider decision.

## 6. Motion and tactile feedback

- Press feedback: 100–140ms, maximum scale reduction 0.985. Disabled controls do not animate as clickable.
- Section reveal: 160–200ms opacity transition, no large translation or staggered delay through the journey steps.
- Skeleton: one subtle opacity pulse in a shared CSS animation, approximately 1.6s. No rapid shimmer, per-row timers, animated blur or shadow.
- Initial loading and refresh use different visuals; never animate an entire settled page continuously.
- Respect `prefers-reduced-motion`: static skeletons and progress labels, no transforms or automatic smooth scrolling.
- Do not wrap the application in transition machinery that delays routing, focus, or screen-reader updates.

## 7. Implementation batches for a smaller model

Paths below are relative to `PS2/frontend`. Complete only one batch at a time, inspect its result, then commit. Use actual generated types for fixtures; no `as never`. Introduce no runtime dependency for skeletons, progress, icons or SVG rendering.

### Batch 1 — establish state truth before animation

Modify `src/features/journey/journeyCoordinator.ts`, `JourneyProvider.tsx`, `journeyContext.ts`, `StatusPanel.tsx` and associated tests.

- [ ] Extend state with a typed operation phase: `idle | loading-plan | checking-status | loading-effective-plan | preparing-offline | saving-offline`. Keep view availability separate from request activity.
- [ ] Track last successful snapshot time and last check outcome separately. A failed refresh cannot retain a current/all-clear visual treatment. An absent status with no request says “Current status unavailable,” not “Checking.”
- [ ] Keep plan/status coherent; serialize offline preparation with refresh through the same coordinator. Preserve generation guards, and test an older response arriving after a trip switch.
- [ ] Preserve bundle generated time, expiry and warnings on hydration. Do not replace saved time with hydration time. Treat network reachability separately from the bundle's freshness.
- [ ] Acceptance: deferred-promise tests prove initial, refreshing, failed-check, effective-plan failure, saved snapshot and stale-response behaviour. No UI percentages are introduced.

### Batch 2 — reusable feedback components

Create `src/components/AsyncFeedback.tsx`, `Skeleton.tsx`, `AsyncFeedback.test.tsx`; create `src/styles/feedback.css`; modify `src/styles/tokens.css`.

- [ ] `AsyncFeedback` takes actual operation, label, start time and optional retry handler. Render one labelled indeterminate indicator and slow-operation text after five seconds; reset on operation identity change.
- [ ] `Skeleton` is visual-only (`aria-hidden`) and uses named variants matching summary, overview and leg dimensions. The parent region owns `aria-busy` and accessible status text.
- [ ] Add tokens for spacing, radius, motion and status surfaces. Consolidate duplicate declarations only where touched; no unrelated full stylesheet rewrite.
- [ ] Acceptance: fake-clock tests cover delayed visual indicator, slow copy, cleanup and rapid completion. Reduced-motion CSS stops all nonessential animation.

### Batch 3 — planning and navigation

Modify `src/App.tsx`, `src/features/planning/AppointmentForm.tsx`, `src/lib/singaporeTime.ts` as needed and their tests; create `src/components/RouteFocus.tsx`.

- [ ] Use explicit date/time labels and readable SGT summary; keep the existing Singapore conversion functions. Require a chosen time, preserve fields on failure, mark invalid fields with `aria-invalid` and focus the first invalid field.
- [ ] Replace “Arrival buffer” with “Arrive early by”; concise helper: “Extra time before your appointment.”
- [ ] Connect the real create request to `AsyncFeedback`; maintain button dimensions and prevent duplicate submission. Successful creation seeds the matching trip plan to avoid a redundant blank GET screen. Do not mark its live status confirmed.
- [ ] Use contextual headers: Home brand; New appointment; Journey; Travel options; Settings. Back labels name the destination. Remove the settings self-link.
- [ ] On forward route navigation, reset scroll and focus the page heading without hiding it behind sticky chrome. On browser back, restore prior scroll where practical. Background refresh never resets either.
- [ ] Acceptance: double submit sends once, form errors retain values, forward navigation exposes the heading, keyboard focus is visible. Show success/failure feedback where the user's attention already is.

### Batch 4 — journey hierarchy, skeletons and schematic

Create `src/features/journey/JourneySkeleton.tsx`, `RouteOverview.tsx`, `RouteOverview.test.tsx`; modify `JourneyPage.tsx`, `JourneyTimeline.tsx`, `src/styles/native.css`.

- [ ] Build the loading/ready hierarchy in the wireframes. The leave-by heading leads, arrival range follows, then status, overview and steps. Move lengthy timing methodology into a labelled Details disclosure; uncertainty and warnings remain visible.
- [ ] Build the SVG schematic from actual legs and include accessible labels. Set a stable overview region; handle zero/one leg, long names, missing geometry and unknown accessibility without inventing content.
- [ ] Keep critical warnings above directions. A failed replan visibly labels retained steps “Previous plan — may not be usable”; never decorate them with a confirmed badge.
- [ ] Make steps scannable: mode, destination, duration and essential exit instruction first; expandable secondary details. No collapsing warnings.
- [ ] Acceptance: snapshots for initial load, good status, stale status, reroute, failed replan and no overview. Mobile layout at 320/390/430px and 200% text zoom remains readable without horizontal page scrolling.

### Batch 5 — home, alternatives, saved-state completion

Modify `HomePage` in `src/App.tsx`, `src/features/alternatives/AlternativesPage.tsx`, `OptionCard.tsx`, `src/features/offline/SaveOfflineButton.tsx`, `src/features/settings/SettingsPage.tsx`.

- [ ] Home reads a matching actual plan for appointment/departure facts. While unresolved show “Open saved journey,” never a blanket “ready.” If expired/missing, explain and offer a new appointment.
- [ ] Alternatives preserve page heading and render option skeletons. Add Retry for retryable failures, an explicit empty state, and “View details” wording; no “Choose” action implying the backend changes route.
- [ ] Offline action distinguishes fetching the bundle from writing storage and shows persistent saved time after reload. Its correctness depends on Batch 1; do not independently call the status-mutating endpoint.
- [ ] Empty settings remains compact and useful. Deletion errors identify partial completion rather than claiming complete removal; keep irreversible controls visually separated from normal preferences.
- [ ] Acceptance: every asynchronous action has idle, pending, success and failure states; the UI never leaves a permanent spinner after completion/failure.

### Batch 6 — verification and handoff

Create `e2e/ux-states.spec.ts`, `e2e/fixtures/journeys.ts`, and `PS2_UX_POLISH_RESULTS.md` in the parent `PS2` directory. Modify `playwright.config.ts` only as needed for a separate production-preview project.

- [ ] Use Playwright request interception in test code with typed, schema-valid fixtures. Hold/release responses for deterministic loading checks rather than arbitrary sleeps. Cover fast success, five-second pending, timeout, 503, missing trip, status failure, effective-plan failure and navigation during a request.
- [ ] Capture home empty/active, planning idle/loading/error, journey skeleton/ready/stale/failed-replan, alternatives loading/error/empty, saved-state success/failure and settings at mobile widths.
- [ ] Run `npm run lint`, `npm run typecheck`, `npm run test:run`, `npm run build`, `npm run test:e2e` from `PS2/frontend`. Record exact outcomes. A passing build alone is not a visual review.
- [ ] Test production preview for service-worker/offline behaviour; the current default E2E server uses Vite dev and cannot prove cold offline navigation.
- [ ] Run axe on representative states, then keyboard checks for form, details disclosures, dialogs and retry actions. Manually verify large text/reduced motion; record real-device checks as pending if unavailable.
- [ ] Performance targets: no new map/animation runtime library; no artificial request delay; no skeleton timers per row; no geometry computation per animation frame; target CLS ≤0.1 and no loading/reveal long task >50ms in the controlled mobile test. Record measurements, do not infer them from bundle size.
- [ ] Report screenshots, unresolved findings and exact commands in the results file. Stop after the scoped plan is complete; broader routing and speech stay separate.

## 8. Smaller-model execution prompt

> Read PS2/PS2_UX_POLISH_PLAN.md and PS2/PS2_FRONTEND_REVIEW.md. Implement the polish plan batch by batch on the current frontend branch, preserving existing changes. Keep the established green visual style, follow the wireframes and operation-state contracts, and derive progress only from actual requests. Use a local SVG route schematic, with no tile provider or live location. Finish correctness prerequisites before loading animations. Run the checks and produce PS2/PS2_UX_POLISH_RESULTS.md with screenshots and honest verification limits. Do not mark untested mobile/offline behaviour complete. Do not implement TTS or general station routing in this pass.

This task is suitable for a smaller coding model when executed in bounded batches. Escalate only if it finds a backend contract conflict or cannot maintain coherent plan/status state; ordinary styling and component decisions are specified here.
