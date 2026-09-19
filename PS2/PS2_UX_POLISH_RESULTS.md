# Nusa UI/UX polish results

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

## Validation

Run from `PS2/frontend`:

| Command | Result |
|---|---|
| `npm run lint` | Passed |
| `npm run typecheck` | Passed |
| `npm run test:run` | Passed: 15 files, 31 tests |
| `npm run build` | Passed; PWA precache 6 entries / 304.77 KiB |
| `PLAYWRIGHT_CHROME_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'; npm run test:e2e` | Passed: Pixel 5 home flow and no horizontal overflow |

The production build emitted the existing `vite-plugin-pwa` warning that
`inlineDynamicImports` is deprecated. It did not fail the build.

## Remaining verification limits

- The Playwright bundled Chromium binary is not installed. The mobile smoke test
  used the installed local Chrome executable instead.
- No real iPhone/Android, screen-reader, axe, or production service-worker offline
  deep-link run was completed in this pass.
- The local backend was unavailable during the earlier design review, so live
  Bedok-to-SGH planning was not revalidated through the browser. Unit tests cover
  coordinator and loading-state behaviour with deterministic responses.
- The larger UX plan still contains optional future work: map-tile provider choice,
  broader end-to-end state coverage, voice read-aloud and general station routing.
