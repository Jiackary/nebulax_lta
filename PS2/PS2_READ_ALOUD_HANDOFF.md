# PS2 — Read-aloud handoff notes

Updated 18 September 2026. Separate engineer handoff, excluded from core frontend implementation. This records
agreed scope for the later design and implementation pass; it is not a completed
implementation specification. React, TypeScript and Vite PWA are the accepted
foundation. See [current architecture](PS2_ARCHITECTURE.md) for implemented capabilities.

## Accepted addition: read my journey/status aloud

**Goal:** let Mdm Lim explicitly request a spoken reading of the journey or status
already available to her on screen. This is the small read-aloud capability, not
automatic progress announcements, voice conversation, or location tracking.

### Planned behavior

- Provide clearly labelled **Read journey**, **Read status**, **Repeat**, and **Stop**
  controls. Speech begins only after a user action; ordinary refreshes do not speak.
- Read journey: appointment, departure time, arrival window, relevant warnings, then
  walking/rail instructions in order. Preserve uncertainty and avoid claiming the
  person has reached a particular stop.
- Read status: concise overall headline/detail and relevant freshness or simulation
  wording. Do not describe an old successful check as a current all-clear.
- Capture one coherent plan/status snapshot for an utterance. A successful status
  check can persist a reroute: retrieve the effective plan afterward before offering
  refreshed journey speech. If that retrieval fails, explain the uncertainty instead
  of combining the new status with silently outdated instructions.
- When `replan_failed` is true, speak the warning and do not narrate retained unsafe
  steps as directions to follow. For an offline bundle, announce its age and warnings
  before any usable instructions; avoid repeating warnings already in `steps_plain`.
- Cancel speech when the user stops it, changes trips, leaves the journey screen,
  or a route-changing update makes the spoken snapshot obsolete. Let the user start
  the revised reading explicitly. Repeated taps must not accumulate speech queues.
- Keep all content readable visually. Speech must not be the only route to information
  or conflict with continuous screen-reader live announcements.

### Initial technical approach

Use browser speech synthesis behind a small frontend adapter and a pure function
that converts typed API data into concise speech text. No LLM, microphone permission,
new speech backend endpoint, or paid provider is required for this first scope.
Treat available voice quality, pronunciation, and offline support as device-dependent;
prefer an available suitable local voice and retain a clear text-only fallback.
Do not promise voice when the page is closed or the phone is locked.

Proposed module responsibilities for the later frontend plan:

| Module | Responsibility |
|---|---|
| `src/features/read-aloud/buildSpeechText.ts` | Format a coherent snapshot, warnings, timing ranges and provenance |
| `src/features/read-aloud/speechAdapter.ts` | Feature detection, voice availability, speak/cancel, completion/error events |
| `src/features/read-aloud/ReadAloudControls.tsx` | Accessible controls and idle/speaking/unavailable feedback |
| Journey data coordinator | Refresh status then plan; invalidate obsolete spoken snapshots |

### Implementation checklist for the later pass

- [ ] Define typed speech inputs from generated OpenAPI types and the journey snapshot.
- [ ] Test text generation for normal, rerouted, stale, simulated, offline, unavailable
  status, and failed-replan cases; retain dates and arrival uncertainty in speech.
- [ ] Implement synthesis adapter and accessible controls with cancellation/queue handling.
- [ ] Integrate into the journey/status views without delaying their initial rendering.
- [ ] Test repeated taps, route changes during speech, unsupported synthesis, missing
  voices, synthesis errors, and cleanup on navigation.
- [ ] Check actual iPhone and Android voice quality, station-name pronunciation,
  interruption controls, screen-reader coexistence, and airplane-mode behavior.

**Acceptance:** one deliberate tap reads the selected current or explicitly dated
snapshot; Stop interrupts it; obsolete instructions never continue after a known route
change; failed accessibility checks are not spoken as safe guidance; unsupported audio
leaves a fully usable visual journey. Record real-device results before promising
offline speech support.

## Integration boundary

The [core frontend plan](PS2_FRONTEND_PLAN.md) now defines screens, journey state,
offline behavior and implementation tasks. This separate speech handoff should
integrate with its journey coordinator; it must not introduce independent status
polling or change the core frontend scope. The receiving engineer owns completing
the speech design and device validation.
