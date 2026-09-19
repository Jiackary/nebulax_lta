# Nusa UI/UX polish results

> **Qualified — historical record. Reconciled 19 Sep 2026; see `PS2_INDEX.md` §11.1.**
> `PS2_DESIGN_REFINEMENT_PLAN.md`, written 38 minutes after this file, reviews the same
> code and states: "the results document is not evidence that every earlier item was
> completed." Treat the list below as what was *attempted*, not what shipped.
>
> Two corrections. (1) The "map-tile provider choice" listed under optional future work
> contradicts `PS2_DECISION_RECORD.md` D14, a "never cut" list whose first item is the
> OSM map — see `PS2_INDEX.md` §11.2. (2) The fixture-mode limitation recorded below has
> since been lifted: the stack has been run against live LTA/OneMap credentials — see
> `PS2_INDEX.md` §11.5.

Completed 19 September 2026 on branch `codex/frontend`.

## Delivered

- Journey state now records real operation, provenance and freshness information.
  A failed status check explicitly qualifies retained directions; saving an offline
  bundle commits its returned plan and status as one snapshot.
- The form explains active trip creation, keeps its contents on errors, disables
  duplicate submissions and uses clearer Singapore-time and buffer language.
- A shared feedback component supplies accessible indeterminate progress and a
  five-second slow-request message. The UI does not report invented percentages or
  backend substeps.
- Initial journey loading keeps a route-shaped layout instead of replacing the page
  with plain text. Settled journeys show a low-cost schematic derived from actual
  legs and labelled “Schematic · not to scale.”
- Alternatives show option-shaped placeholders while loading. Offline saving reports
  the saved time; deletion distinguishes a server deletion from a failed local-copy
  removal. Settings no longer links to itself.
- Route changes reset scroll position and move keyboard focus to the new page's main
  landmark; background refreshes do neither.
- The completed journey is now an art-directed companion surface: a prominent
  departure-time card, tactile condition refresh control, route trace, more legible
  step hierarchy, and an intentional wide-screen composition that collapses to one
  reading column on mobile.

## Validation

Run from `PS2/frontend`:

| Command | Result |
|---|---|
| `npm run lint` | Passed |
| `npm run typecheck` | Passed |
| `npm run test:run` | Passed: 15 files, 32 tests |
| `npm run build` | Passed; PWA precache 6 entries / 312.42 KiB |
| `PLAYWRIGHT_CHROME_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'; npm run test:e2e` | Passed: Pixel 5 home flow and no horizontal overflow |
| Live local fixture journey | Passed: backend health check and Bedok-to-SGH plan returned `200`; reviewed at desktop and 390 × 844 mobile viewport |

The production build emitted the existing `vite-plugin-pwa` warning that
`inlineDynamicImports` is deprecated. It did not fail the build.

## Remaining verification limits

- The Playwright bundled Chromium binary is not installed. The mobile smoke test
  used the installed local Chrome executable instead.
- No real iPhone/Android, screen-reader, axe, or production service-worker offline
  deep-link run was completed in this pass.
- The local backend needs to be started for the client to plan a journey. The current
  development server was started in fixture mode, which makes Bedok-to-SGH available
  but does not validate live external LTA/OneMap data.
- The larger UX plan still contains optional future work: map-tile provider choice,
  broader end-to-end state coverage, voice read-aloud and general station routing.
