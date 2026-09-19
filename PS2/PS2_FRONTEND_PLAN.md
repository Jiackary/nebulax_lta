# PS2 Frontend Implementation Plan

> **Historical — reconciled 19 Sep 2026; see `PS2_INDEX.md` §0 and §11.**
> Implementation *has* started: the frontend exists on `codex/frontend`. The line below
> saying otherwise predates it. For current direction use `PS2_DESIGN_REFINEMENT_PLAN.md`
> (visual) and `PS2_FRONTEND_REVIEW.md` (open functional findings). Note that the stack
> stated below specifies "TypeScript strict mode" and axe-core; neither is actually in
> effect in the built code — `strict` is absent from every `tsconfig` and axe is never
> run. See `PS2_INDEX.md` §11.4.
>
> **§1's "Map scope decision" is withdrawn.** It is the earliest of the four documents
> that narrowed the map, and the origin of the chain traced in `PS2_INDEX.md` §11.2:
> a tile-less "route sketch" here, then a deferred provider choice in
> `PS2_UX_POLISH_PLAN.md`, then no map task in `PS2_CONSOLIDATED_ROADMAP.md`, then
> "geographic maps remain outside this frontend pass" in
> `PS2_DESIGN_REFINEMENT_PLAN.md`. Each step was locally reasonable; together they
> dropped a mandatory capability. `PS2_README.md` §3.2.3 requires the route on a map
> with the affected portion distinguished, and `PS2_DECISION_RECORD.md` D14 lists it
> under "Never cut". Offline tiles stay parked; the online map is in scope.

> For agentic workers: use the executing-plans skill to implement one task at a time. Use the checkboxes to track progress. Do not implement this entire document in one turn. Implementation has not started.

**Goal:** Build a polished, accessible, mobile-first journey companion for Mdm Lim's Bedok → Singapore General Hospital appointment journey, using the existing backend without inventing capabilities.

**Architecture:** React/TypeScript Vite PWA under `PS2/frontend`, with typed API access, a serialized journey coordinator, and explicit offline snapshots. The backend owns routes, timings and disruption interpretation. The frontend owns presentation, browser interactions and local persistence.

**Tech stack:** React, TypeScript strict mode, Vite, React Router, CSS custom properties, native fetch, `idb`, Vitest/Testing Library, Playwright and axe-core. One service worker using the Vite PWA plugin's injectManifest strategy. Generate API types using openapi-typescript. Use npm and commit the lockfile when commits are authorized. Select compatible stable dependency versions during implementation, not guessed versions from this plan.

Baseline: backend inspected 18 September 2026, main `8f87265`. Recheck contracts if the checkout changes. Paths in this document are repository-relative.

## 1. Scope and ownership

This is the core frontend handoff, not a backend redesign. Production changes belong under `PS2/frontend`; documentation/index changes are allowed. Report incompatible backend behavior rather than silently changing backend semantics.

Included:

- Appointment creation for the fixed corridor, one locally active journey, coherent route/status refresh.
- Ordered walking/train/walking instructions, accessibility uncertainty and freshness.
- Read-only alternatives comparison, offline written guidance, optional browser push enrollment.
- Privacy/deletion controls, explicitly gated demonstration controls, responsive/accessibility/performance verification.

Excluded:

- Text-to-speech, voice conversation, microphone access, architecture diagrams.
- GPS tracking, automatic journey progress, turn-by-turn navigation, arbitrary destinations, accounts, translations, taxi booking.
- Selecting an alternative as the saved route: no adoption endpoint exists.
- Offline map tiles, backend deployment redesign, claiming the current backend is production-hardened.

Separate engineer handoffs: [read-aloud notes](PS2_READ_ALOUD_HANDOFF.md) and [architecture draft](PS2_ARCHITECTURE.md). Leave those documents and their implementation alone during frontend tasks. Do not add dead speech buttons.

**Map scope decision:** first release uses a collapsible lightweight route sketch from returned geometry, labelled **Route overview — not a navigation map**. No base tiles, provider key, GPS or invented street detail. This keeps a provider/licensing decision from blocking the core UI. A full interactive base map is a separate enhancement, not something an implementation model should choose unprompted.

## 2. Screen and interaction specification

| Route | Required content | Actions |
|---|---|---|
| `/` | No active trip: appointment entry. Active trip: upcoming appointment, departure, arrival range, status/freshness | Plan journey / Open journey; new appointment with replacement explanation |
| `/plan` | Fixed home and SGH Block 3; Singapore appointment date/time; sheltered preference and buffer | Plan journey, cancel; preserve input on error |
| `/trip/:tripId` | Departure hero, status notice, ordered timeline, collapsible sketch, detail | Check again, See options, Save written steps offline, reminder settings |
| `/trip/:tripId/options` | Original viability, ranked options, reasons for unavailable options | Expand details, return; no adoption/booking |
| `/settings` | Reminder state, saved-copy timestamp, privacy controls, attribution | Enable reminders, explicitly destructive unsubscribe/delete, remove local copy |
| `/demo` | Only when `VITE_ENABLE_DEMO=true`; shared-server simulation warning | Supported scenario switches; deliberate push test |

Do not add empty bottom navigation tabs. Use compact header/back navigation and one contextual primary action. Deep links must survive reload, including `/trip/:tripId` from notifications.

### Visual direction: calm, precise, journey-first

- Starting tokens: background `#F6F7F4`, surface white, ink `#17251F`, primary `#145A42`; restrained amber/red warning surfaces. Verify actual text/background contrast pairs.
- System font, no remote fonts. Body 18px/1.5; secondary information at least 16px; departure time 40–48px, without clipping on small screens.
- Continuous vertical journey timeline: leg icon/number, connector, instruction, duration, station/exit, access uncertainty and surface warnings. No moving progress marker or completed-leg claim.
- 8px spacing rhythm; 20px mobile gutter; 16px card radius; subtle borders and sparse shadows. No glass effects, decorative gradients, carousels or animated backgrounds.
- 320–767px single column. At 768px+, centered shell up to 1120px with journey column and optional 360px detail column. Preserve DOM reading order.
- Controls at least 48×48 CSS pixels; visible focus; semantic elements; no essential icon-only controls. Dialogs trap/restore focus and support Escape where appropriate.
- Opacity/transform transitions only, 120–180ms; reduced-motion disables them. No automatic height animation or scroll jumps during refresh.
- Skeleton only on initial load. Later checks retain content, focus, scroll and expanded details, with a small “Checking…” indicator.

### Content invariants

1. Retain arrival ranges and timing basis. An estimate is never a promise.
2. `step_free: unknown` displays **Step-free access not confirmed**, not a green accessibility tick. Outdoor geometry does not establish station-interior accessibility.
3. Stale, simulated and offline are independent labels; show all applicable states.
4. Stale `overall.severity=ok` becomes a visibly qualified **Last reported status**, not a current all-clear. Missing weather/crowd means unavailable.
5. `replan_failed` puts a critical warning above the route. Retained steps are **Previous plan — may not be usable**, not primary safe instructions.
6. No “you are here”, “you have arrived” or automatic progress based on clock time.
7. Device receipt time differs from upstream `observed_at`. Display Singapore time, with date when needed. `next_check_at` is backend schedule information, not proof this browser will receive a push.
8. Keep attribution visible on route-derived screens, including offline views.

## 3. Backend contract

Read `PS2/backend/app/api/schemas.py`, the relevant route modules and `PS2/PS2_API_CONTRACT.md`. Runtime OpenAPI is the type source of truth; prose may lag. Inspect `PS2/backend/tests/data/api_surface.json` before using it as test data.

| Operation | Endpoint | Constraint |
|---|---|---|
| Create | `POST /api/trips` | Explicit `+08:00` appointment; destination `SGH`; omit origin to use backend default |
| Read/delete | `GET/DELETE /api/trips/{id}` | No list/update endpoint; 404 means missing/expired |
| Status | `GET /api/trips/{id}/status` | Can persist a changed route; follow with plan retrieval |
| Alternatives | `GET /api/trips/{id}/alternatives` | Nullable fields and informational options only |
| Offline | `GET /api/trips/{id}/offline` | Can replan; coherent plan/status/warnings bundle; no tiles |
| Metadata | `GET /api/destinations`, `/api/attribution`, `/api/health` | Fixture indicator is useful, not a freshness guarantee |
| Push | `GET /api/push/key`; `POST /api/push/subscribe` | Browser subscription plus explicit `trip_ids` |
| Unsubscribe | `DELETE /api/push/subscribe?endpoint=...` | Deletes linked server trips too; not a harmless mute |
| Demo | `GET/POST /api/scenario`; `POST /api/push/test?trip_id=...` | Shared server state, not browser-local |

No address autocomplete in this scope: search results do not imply arbitrary origins are supported. Keep `walking_pace: "slow"`, `avoid_stairs: true`. Expose sheltered preference and buffer integer 0–120, initially 15 minutes (`planner.DEFAULT_BUFFER_MIN` at the inspected baseline). Do not offer stairs as an alternate routing mode.

Errors use `{error:{code,message,retryable}}`; handle invalid JSON/gateway HTML, empty bodies, fetch failure, abort and timeout too. No secrets in `VITE_*`. Prefer same-origin `/api` in production; dev proxy to localhost:8000. SPA fallback must not rewrite API requests to HTML.

### Journey consistency boundary

One coordinator owns status, plan, offline-download and demo-triggered refreshes. Components cannot independently poll status.

```ts
// API type aliases come from generated components['schemas'].
type JourneySnapshot = {
  tripId: string;
  plan: TripPlan;
  status: RouteStatus | null;
  receivedAt: string;
  source: 'network' | 'saved';
  routeConfirmed: boolean;
};
type JourneyPhase = 'loading' | 'ready' | 'refreshing' | 'degraded' | 'missing';
```

- Initial entry reads plan promptly, labelled **Status not checked**, then refreshes.
- Refresh requests status, then effective plan; publish the pair together. Coalesce concurrent triggers.
- Status success + plan failure: show the new warning separately; retained route becomes unconfirmed. Never present old directions as newly checked. Next retry repeats the transaction.
- Status failure: retain previous content with check-failure/age labels; never invent an all-clear.
- Trip switch/delete/unmount invalidates a generation token, aborts requests and ignores late responses. Request cancellation does not undo server mutations.
- Offline save shares this serialization boundary. Normalize bundle plan using its top-level trip ID, publish the returned snapshot and persist it atomically.
- Poll every 60 seconds only on visible, online journey screen. Pause hidden. Visibility/reconnect triggers one refresh if last attempt was ≥30 seconds ago. Backoff failed checks to 120 then 300 seconds; manual retry remains available. Actual request failures override optimistic `navigator.onLine`.
- No backend revision ID exists: this prevents local races but does not guarantee multi-device transactional consistency.

## 4. Offline, privacy and push requirements

Store one active trip reference and explicitly saved bundles in versioned IndexedDB. Do not persist all API traffic. No analytics or coordinate/trip-ID logging. Treat trip IDs as private access links; deploy with `Referrer-Policy: no-referrer` and safe external links.

- Service worker precaches hashed app-shell assets only. `/api/*` is network-only; explicit IndexedDB fallback supplies offline content. Never let generic cache-first behavior serve stale API responses as live.
- Save success appears only after IndexedDB commit; failed/quota write leaves previous saved bundle intact.
- Show offline bundle date/time, notice, warnings and written steps. `steps_plain` starts with warnings: if rendering warning cards separately, strip only that exact matching prefix, not every repeated string.
- Missing status is **Not checked**. Failed-replan flags on either status or bundle plan trigger unsafe-previous-plan treatment.
- On reconnect, keep saved labels until refresh succeeds. Saved bundle updates only through explicit save.
- Purge local bundles 24 hours after appointment on startup/read. Server 404 clears the active server reference; a surviving bundle is labelled historical, not valid ongoing travel guidance.
- Creating another appointment changes active reference only after success; it does not implicitly delete the old server trip. Explain this and offer explicit deletion. Never automatically retry an ambiguous POST timeout; no idempotency key exists.
- Delete confirmation calls server first, then clears local state and invalidates pending work. Failure/offline must not claim server deletion; local-only removal is separately labelled.
- Push permission is requested only by deliberate action. Unsupported/denied/unconfigured push leaves journey fully usable. Successful browser subscription alone is not successful server registration.
- Unsubscribe confirmation explicitly says linked server trips will be deleted. Remove server registration first, then browser subscription; reconcile partial failures accurately. Do not implement a benign “Pause reminders” toggle using this endpoint.
- Validate notification destinations as same-origin `/trip/{id}` paths; never navigate arbitrary payload URLs. Reuse a matching open app window where possible.
- Service-worker updates prompt for user-controlled reload; no automatic reload mid-journey.

## 5. File map

All paths below are under `PS2/frontend/`. Use coordinator + React context, not a second global-state framework.

| Files | Responsibility |
|---|---|
| `package.json`, `vite.config.ts`, `tsconfig*.json`, `index.html` | Toolchain, scripts, proxy, chunking |
| `src/main.tsx`, `src/app/{App,routes}.tsx` | Providers, routing, error boundaries |
| `src/styles/{tokens,global}.css` | Tokens, layout, focus, reduced motion |
| `src/components/{Button,Notice,Dialog,PageShell,Attribution}.tsx` | Accessible primitives |
| `src/api/{generated.d.ts,types.ts,client.ts,trips.ts,push.ts,scenario.ts}` | Generated aliases, transport, typed operations |
| `src/lib/singaporeTime.ts` | Explicit-offset input and Singapore display |
| `src/features/planning/{PlanPage,AppointmentForm}.tsx` | Fixed-corridor form |
| `src/features/journey/{journeyCoordinator.ts,JourneyProvider.tsx,useJourney.ts}` | Serialized state |
| `src/features/journey/{JourneyPage,JourneyHero,JourneyTimeline,StatusPanel,RouteSketch}.tsx` | Journey presentation; lazy sketch |
| `src/features/alternatives/{AlternativesPage,OptionCard}.tsx` | Read-only comparison |
| `src/features/offline/{storage.ts,OfflineNotice.tsx,SaveOfflineButton.tsx}` | Persistence and explicit offline handling |
| `src/features/settings/{SettingsPage,DeleteTripDialog}.tsx` | Privacy/destructive actions |
| `src/features/push/{pushController.ts,ReminderControls.tsx}` | Permission/subscription states |
| `src/features/demo/DemoPage.tsx` | Gated shared-server controls |
| `src/sw.ts`, `public/manifest.webmanifest`, `public/icons/*` | One service worker and install metadata |
| `src/test/{setup.ts,fixtures.ts}`, colocated `*.test.ts(x)` | Deterministic unit/component tests |
| `e2e/{journey,offline,push,accessibility}.spec.ts`, `playwright.config.ts` | Browser flows |
| `README.md`, `.env.example` | Commands, deployment requirements, limits |

No frontend module parses lift descriptions, reconciles station names or recalculates timing. Those remain backend responsibilities.

## 6. Sequential implementation tasks

Each task is a bounded handoff. Write the listed failing tests, run the focused test, implement, rerun, then typecheck. Record commands/results. Do not proceed past a failed gate. Commit only task-owned files if authorized; preserve other engineers' drafts.

### Task 1 — Bootstrap and shell

Files: toolchain, app/router, styles, primitives, test setup, README.

- [ ] Confirm Node/npm and compatible package versions; scaffold under `PS2/frontend` without another nested app directory.
- [ ] Add `dev`, `build`, `preview`, `typecheck`, `test`, `test:run`, `test:e2e`, `lint` scripts. Configure strict TS and lint without blanket suppressions.
- [ ] Test keyboard access to primary action, unknown-route recovery, dialog focus restoration and reduced-motion rules.
- [ ] Implement shell/primitives and real empty/loading/error states, without fake functional buttons.
- [ ] Gate: `npm run test:run`, `npm run typecheck`, `npm run build` succeed from frontend directory; deep-link reload works in preview configuration.

### Task 2 — Contract, transport and time

Files: `src/api/*`, `src/lib/singaporeTime.ts`, associated tests. Read backend schemas/main/routes.

- [ ] Start controlled backend from `PS2/backend`: `.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`, with fixture environment enabled. Fixture mode is not a universal network firewall; automated browser tests must intercept network.
- [ ] Add `api:generate`: `openapi-typescript http://127.0.0.1:8000/openapi.json -o src/api/generated.d.ts`. Track generated file so ordinary builds need no running backend.
- [ ] Alias API types from generated schemas; creation body uses generated request type. Do not create parallel handwritten models.
- [ ] Tests: valid response, structured 422/503, HTML 502 fallback, timeout, abort, encoded query, no auto-retry POST.
- [ ] Implement AbortSignal-aware fetch, 20-second timeout, normalized API error and text-only safe error display.
- [ ] Time tests: New York browser submits chosen Singapore time `2026-10-20T09:00:00+08:00`; midnight boundary; invalid input. Never convert Singapore wall time with browser-local `new Date(datetimeLocal).toISOString()`.
- [ ] Gate: focused tests/typecheck pass; regenerating schema requires no manual fix.

### Task 3 — Home and appointment

Files: planning feature, home route, storage active-reference helpers. Read backend request validation and buffer default.

- [ ] Tests: empty home, valid creation, double tap submits once, 422 retains input, timeout retains input without resubmission, failed replacement preserves old active ID.
- [ ] Implement fixed origin/destination, explicit Singapore time, future default computed in Singapore, constrained preferences, inline errors and pending state.
- [ ] On success persist ID then navigate; storage failure leaves usable in-memory journey with restart warning.
- [ ] Gate: keyboard and 320px creation flow passes; no arbitrary routing/search UI.

### Task 4 — Journey coordinator

Files: coordinator/provider/hook, typed trip operations, tests.

- [ ] Tests: status→plan ordering, initial plan-only state, partial failure, status failure, coalesced taps, late result after trip switch/delete, 404, offline-save serialization, visibility/backoff.
- [ ] Implement section 3 rules with injectable API and clock; orchestration lives outside presentational components.
- [ ] Publish coherent snapshots, expose partial-failure warning separately, clean up timers/listeners and invalidate request generations.
- [ ] Gate: fake-timer tests prove no overlapping transaction or cross-trip overwrite. Obtain focused review of this boundary before continuing.

### Task 5 — Journey/status UI

Files: journey presentation, notice/attribution, component tests.

- [ ] Typed fixtures: clear fresh, stale clear, simulation, reroute, unresolved station-only lift, failed replan, absent weather, null rail duration, retained content while checking.
- [ ] Build hero/timeline/detail/status using section 2. Allowlist action kinds `view_trip`, `view_reroute`, `view_alternatives`; unknown kinds do not execute.
- [ ] “Route updated” highlights current exit/instruction. Do not invent original-route geometry or before/after comparison unavailable in API.
- [ ] Lazy-load route sketch; validate finite coordinates and handle empty/degenerate bbox. Invalid geometry falls back to text, not a broken page.
- [ ] One polite live region announces meaningful changes, not the entire journey every poll.
- [ ] Gate: safety states distinguishable without color; focus/scroll/expanded detail survive refresh; sketch not in initial chunk.

### Task 6 — Alternatives

Files: alternatives feature and tests.

- [ ] Tests: rail not viable; bus unknown ETA/access; taxi unknown fare; no options; not-offered reasons; fetch error/retry.
- [ ] Display server rank, timing basis, nullable duration/delta and mode-specific fields. Unknown is never zero. Show bus stop and taxi stand information only when returned.
- [ ] View details expands information, never changes route. `options[].legs` is heterogeneous, not a typed TripPlan leg list; use known mode-specific fields rather than unsafe casts.
- [ ] Gate: all actions work, limitations survive formatting, browser back retains journey state/scroll.

### Task 7 — Offline and installable shell

Files: offline storage/UI, service worker/manifest/icons, offline e2e.

- [ ] Tests: atomic save failure, schema/corrupt-storage recovery, exact warning prefix removal, missing status, failed replan on plan, post-appointment expiry.
- [ ] Implement explicit save and normalized bundle fallback with dates/warnings and local-copy removal.
- [ ] Implement shell-only precache, network-only APIs, install metadata and user-controlled update prompt.
- [ ] Production-build e2e: load online→save→disable network→reload deep link→read warnings/steps; repeat without saved bundle; reconnect→refresh.
- [ ] Gate: offline reload works after initial online shell load; no API response in CacheStorage; no tile requests; save confirmation follows committed write. Review offline safety treatment before continuing.

### Task 8 — Push and deletion

Files: push/settings features, service-worker handlers, tests.

- [ ] Test unsupported/default/denied/subscribing/subscribed/not-configured/partial-failure states. Permission prompt only on user action.
- [ ] Register browser subscription with active trip ID; new active trip explicitly updates subscribed IDs. Failed server registration never appears enabled.
- [ ] Implement safe notification-click route handling; reuse an app window when possible.
- [ ] Confirm destructive trip deletion and unsubscribe. Tests cover server failure, browser unsubscribe failure after server success, and late refresh after delete.
- [ ] Gate: app remains usable without push; no startup permission prompt, no misleading mute toggle. Record real-device HTTPS results separately from mocks before claiming mobile push support.

### Task 9 — Demo controls

Files: demo page/gating, scenario wrapper, test fixtures.

- [ ] Test route absent when disabled, nested scenario flags with master switch, error rollback, simulation labels, push test `sent=false` wording.
- [ ] GET scenario before changing it; POST intended master/nested state then refresh through coordinator. Display shared-server warning.
- [ ] Never reset scenarios on ordinary mount/unmount. Automated tests use isolated mocked backend; no real push is sent. Explicit user confirmation precedes manual push test.
- [ ] Gate: isolated clear→lift outage→disruption→clear flow works. Document that hiding demo UI is not backend authorization.

### Task 10 — Integration and polish

Files: e2e suite, responsive styles, README, focused fixes.

- [ ] Run `npm run lint`, `npm run typecheck`, `npm run test:run`, `npm run build`, `npm run test:e2e`; record results and distinguish mocked versus backend/device tests.
- [ ] Test 320×568, 390×844, 768×1024, 1440×900; 200% text zoom, keyboard, reduced motion, VoiceOver/TalkBack spot checks. Axe: zero serious/critical violations on main routes; manual checks still required.
- [ ] E2E: create→journey→reroute→options→save→offline reload→reconnect→delete; invalid deep link; backend outage. Deterministic CI uses mocks; separate smoke test uses isolated fixture backend.
- [ ] Initial app JS budget ≤200KB gzip, excluding lazy demo/sketch chunks. No remote font/map SDK on startup, no overlapping refresh. Report and fix measured excess rather than quietly raising budget.
- [ ] Measure production build against mobile lab LCP ≤2.5s and CLS ≤0.1 with documented throttle/device. Target scripted interaction response ≤200ms under CPU throttle; do not claim field INP from lab-only evidence. Report backend latency separately.
- [ ] Document HTTPS, same-origin proxy, SPA fallback, service-worker/update behavior, environment setup, device results and backend security/deployment limitations. No production-ready claim from mocked tests alone.
- [ ] Gate: all supported actions functional, critical safety cases passing, no console errors or dead controls, accurate implemented/deferred documentation.

## 7. Mandatory acceptance matrix

Build typed fixtures from inspected captures, overriding only relevant fields. Unit/browser tests must not call live feeds.

| Case | Required assertion |
|---|---|
| Stale + overall ok | Last-reported qualifier; no unqualified current all-clear |
| Simulated + stale | Both labels visible |
| Status success + plan 500 | New warning visible; old route unconfirmed; retry |
| Replan failed | Critical warning before previous instructions |
| Step-free unknown | Unknown label; no accessibility tick |
| Null bus duration/ETA/access | Unknown, not 0 or accessible |
| Offline status missing | Warning before steps; no current status badge |
| Delete during refresh | Late response cannot restore trip |
| Push denied/key 503 | Usable app; no prompt loop or enabled state |
| Trip 404 | Recovery view, polling stops |

Example component assertions (using implementation-local fixture builders):

```ts
expect(screen.getByText(/step-free access not confirmed/i)).toBeVisible();
expect(screen.queryByRole('button', { name: /use this route/i })).toBeNull();
expect(screen.getByText(/previous plan.*may not be usable/i)).toBeVisible();
expect(screen.getByRole('button', { name: /plan journey/i })).toBeDisabled();
```

## 8. Smaller-model handoff prompt

> Implement Task N of `PS2/PS2_FRONTEND_PLAN.md` only. Inspect git status and completed dependencies; preserve other engineers' work. Read the specified backend contracts. Keep speech and architecture documentation out of scope. Write/run the listed focused tests, implement the smallest complete slice, then typecheck. Never invent endpoints, route adoption, freshness or accessibility guarantees. Report a contract blocker rather than changing backend semantics. Finish with changed files, commands/results, acceptance checks and next task number. Do not start the next task or commit/push without authorization.

Dependency order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10. Avoid parallel tasks touching coordinator, schema or service worker. Tasks 4 and 7 require focused review because errors could present obsolete directions as current.

Complete means: working fixed-corridor frontend against the current backend, honest offline/uncertainty behavior, supported functional actions and recorded accessibility/performance evidence. Speech and architecture completion are separate handoffs, not hidden work inside these tasks.
