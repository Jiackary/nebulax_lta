// Screenshot capture for the design-refinement gates. Not an assertion suite: it writes the
// images the plan asks to be inspected. Run with `npx playwright test e2e/screenshots.spec.ts`;
// output lands in `PS2/evidence/screens/` and is deliberately not committed.
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'

import { expect, test, type Page } from '@playwright/test'

import { FIXTURE_TRIP_ID, mockApi, type MockApiOptions } from './fixtures/mockApi'
import {
  alternativesEmpty,
  alternativesReady,
  planLongNames,
  planNoOverview,
  planReady,
  planReplanFailed,
  savedBundle,
  statusCurrent,
  statusDisrupted,
  statusReplanFailed,
  statusStale,
} from './fixtures/states'

const OUT = resolve(import.meta.dirname, '../../evidence/screens')
const TRIP = `/trip/${FIXTURE_TRIP_ID}`
const WIDTHS = [320, 390, 1280]

type Shot = { name: string; path: string; api: MockApiOptions; settled: (page: Page) => Promise<void> }

const heading = (pattern: RegExp) => async (page: Page) => {
  await expect(page.getByRole('heading', { name: pattern })).toBeVisible()
}

const shots: Shot[] = [
  { name: 'home', path: '/', api: { plan: planReady, status: statusCurrent }, settled: heading(/your journey/i) },
  { name: 'plan', path: '/plan', api: { plan: planReady, status: statusCurrent }, settled: async (page) => void (await expect(page.getByLabel(/appointment date and time/i)).toBeVisible()) },
  { name: 'journey-ready', path: TRIP, api: { plan: planReady, status: statusCurrent }, settled: heading(/journey steps/i) },
  { name: 'journey-stale', path: TRIP, api: { plan: planReady, status: statusStale }, settled: heading(/journey steps/i) },
  { name: 'journey-warning', path: TRIP, api: { plan: planReady, status: statusDisrupted }, settled: heading(/journey steps/i) },
  { name: 'journey-replan-failed', path: TRIP, api: { plan: planReplanFailed, status: statusReplanFailed }, settled: heading(/journey steps/i) },
  { name: 'journey-no-overview', path: TRIP, api: { plan: planNoOverview, status: statusCurrent }, settled: heading(/journey steps/i) },
  { name: 'journey-long-names', path: TRIP, api: { plan: planLongNames, status: statusCurrent }, settled: heading(/journey steps/i) },
  { name: 'journey-offline', path: TRIP, api: { plan: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'Offline.' }, savedOffline: savedBundle }, settled: heading(/journey steps/i) },
  { name: 'journey-loading', path: TRIP, api: { hang: true }, settled: async (page) => void (await expect(page.locator('.journey-skeleton')).toBeVisible()) },
  { name: 'options', path: `${TRIP}/options`, api: { plan: planReady, status: statusDisrupted, alternatives: alternativesReady }, settled: heading(/compare your options/i) },
  { name: 'options-empty', path: `${TRIP}/options`, api: { plan: planReady, status: statusDisrupted, alternatives: alternativesEmpty }, settled: heading(/compare your options/i) },
  { name: 'settings', path: '/settings', api: { plan: planReady, status: statusCurrent }, settled: heading(/journey settings/i) },
]

test.describe.configure({ mode: 'serial' })

for (const shot of shots) {
  for (const width of WIDTHS) {
    test(`capture ${shot.name} at ${width}`, async ({ page }) => {
      const file = `${OUT}/${width}/${shot.name}.png`
      await mkdir(dirname(file), { recursive: true })
      await page.setViewportSize({ width, height: 900 })
      await mockApi(page, shot.api)
      await page.goto(shot.path)
      await shot.settled(page)
      await page.screenshot({ path: file, fullPage: true })
    })
  }
}
