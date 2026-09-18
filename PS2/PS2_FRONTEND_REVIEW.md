# Independent frontend review — 19 September 2026

Scope: review the current implementation against PS2_FRONTEND_PLAN.md and revise the mobile design. The earlier completion report overstated plan coverage: passing 21 unit tests and one home-screen browser test did not establish completion of all ten tasks.

## Design changes implemented

- Replaced promotional home hero with a compact journey home, a route ticket, explicit endpoint addresses, appointment state and full-width primary action.
- Added persistent back/settings controls and safe-area spacing. Grouped appointment inputs, consistent mobile typography, quieter surfaces, and bottom-sheet presentation on phones.
- Improved journey information hierarchy and larger instruction text. Retained uncertainty and disruption labels.
- Added keyboard focus containment to the existing dialog and corrected document title, icon and viewport metadata.
- Made the supported Bedok → SGH corridor explicit. Backend configuration fixes origin/destination stations to EW5/EW16; POST /api/trips rejects a destination other than SGH. General routing requires a separate backend feature.

## Outstanding functional findings

These findings are recorded for implementation follow-up, not represented as fixed by the visual pass.

1. **High: offline save bypasses the journey coordinator.** `SaveOfflineButton.tsx` calls the offline endpoint directly; that endpoint can replan. Visible directions may then disagree with the saved bundle or a concurrent status request. Route all status-changing reads through one serialized coordinator.
2. **High: offline recovery is incomplete.** `sw.ts` precaches assets but has no navigation fallback for a cold `/trip/:id` request. Saved bundle hydration omits bundle warnings/generated time, expiry and plan-level replan failure. It may also run after a 404. Implement the planned offline safety contract and test a production build with network disabled.
3. **High: refresh failure can leave an optimistic headline.** Coordinator retains previous route/status after status failure, and StatusPanel can still show the old fresh all-clear. Qualify all retained status after a failed check; missing status must not perpetually say it is checking.
4. **Medium: automatic refresh absent.** No visible-page polling, reconnect/visibility refresh or failure backoff is implemented. Initial/manual checks alone do not satisfy the plan.
5. **Medium: reminder lifecycle incomplete.** Enrollment waits indefinitely for service-worker readiness in development, enabled state is not restored on reload, unsubscribe UI is absent, and route-click validation changes only pathname on an external URL. Complete permission/lifecycle handling and normalize notification navigation to the app origin.
6. **Medium: local state differs from the plan.** Active trip ID uses localStorage rather than IndexedDB; a storage failure warning is discarded on navigation. Deletion reports generic failure if local cleanup fails after server success. Preserve and report distinct outcomes.
7. **Medium: remaining product/verification gaps.** No route sketch, full active-home appointment summary, update prompt, complete alternative details, demo push test, or broad accessibility/offline browser suite. Several unit fixtures bypass typing with `as never`; they do not validate realistic backend integration.

## Completion standard

The redesign is a local implementation preview. Treat the existing frontend as a functional first slice requiring the above follow-up, not a fully verified production release. Real-device push, screen-reader testing, offline deep-link recovery and representative end-to-end route scenarios remain required.
