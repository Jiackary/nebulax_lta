// Reflow coverage. A user reported horizontal scrolling that earlier passes never reproduced,
// because the only check ran on Home at one width. This sweeps every screen and every state the
// journey can be in, across the widths in PS2_DESIGN_REFINEMENT_PLAN.md, and reports the
// offending element rather than only that something overflowed.
import { expect, test, type Page } from '@playwright/test'

import { FIXTURE_TRIP_ID, mockApi, type MockApiOptions } from './fixtures/mockApi'
import { formatReport, measureOverflow } from './fixtures/overflow'
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

const WIDTHS = [320, 360, 375, 390, 430, 767, 768, 820, 960, 1280]
const HEIGHT = 900

const TRIP = `/trip/${FIXTURE_TRIP_ID}`

type Scenario = {
  name: string
  path: string
  api: MockApiOptions
  /** A locator that proves the intended state is on screen before anything is measured. */
  settled: (page: Page) => Promise<void>
}

const scenarios: Scenario[] = [
  {
    name: 'home with a saved journey',
    path: '/',
    api: { plan: planReady, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: 'Your journey', exact: true })).toBeVisible()),
  },
  {
    name: 'plan form',
    path: '/plan',
    api: { plan: planReady, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByLabel(/appointment date and time/i)).toBeVisible()),
  },
  {
    name: 'journey ready, status current',
    path: TRIP,
    api: { plan: planReady, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'journey loading',
    path: TRIP,
    api: { hang: true },
    settled: async (page) => void (await expect(page.locator('.journey-skeleton')).toBeVisible()),
  },
  {
    name: 'journey failed to load',
    path: TRIP,
    api: { plan: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'The service is temporarily unavailable. Please try again.' } },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /could not load this journey/i })).toBeVisible()),
  },
  {
    name: 'journey missing',
    path: TRIP,
    api: { plan: { status: 404, code: 'TRIP_NOT_FOUND', message: 'This journey is no longer available.' } },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /no longer available/i })).toBeVisible()),
  },
  {
    name: 'journey with stale status',
    path: TRIP,
    api: { plan: planReady, status: statusStale },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'journey with a disruption warning',
    path: TRIP,
    api: { plan: planReady, status: statusDisrupted },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'journey with a failed replan',
    path: TRIP,
    api: { plan: planReplanFailed, status: statusReplanFailed },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'journey whose status check failed',
    path: TRIP,
    api: { plan: planReady, status: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'We could not check current conditions. Please try again.' } },
    settled: async (page) => void (await expect(page.getByRole('alert')).toBeVisible()),
  },
  {
    name: 'journey read from the offline copy',
    path: TRIP,
    api: {
      plan: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'The service is temporarily unavailable.' },
      savedOffline: savedBundle,
    },
    settled: async (page) => void (await expect(page.locator('.offline-notice')).toBeVisible()),
  },
  {
    name: 'journey with long station and destination names',
    path: TRIP,
    api: { plan: planLongNames, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'journey with no route overview',
    path: TRIP,
    api: { plan: planNoOverview, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()),
  },
  {
    name: 'alternatives',
    path: `${TRIP}/options`,
    api: { plan: planReady, status: statusDisrupted, alternatives: alternativesReady },
    settled: async (page) => void (await expect(page.getByRole('heading', { level: 1 })).toBeVisible()),
  },
  {
    name: 'alternatives with nothing to offer',
    path: `${TRIP}/options`,
    api: { plan: planReady, status: statusDisrupted, alternatives: alternativesEmpty },
    settled: async (page) => void (await expect(page.getByRole('heading', { level: 1 })).toBeVisible()),
  },
  {
    name: 'settings',
    path: '/settings',
    api: { plan: planReady, status: statusCurrent },
    settled: async (page) => void (await expect(page.getByRole('heading', { level: 1 })).toBeVisible()),
  },
  {
    name: 'unknown route',
    path: '/nowhere',
    api: {},
    settled: async (page) => void (await expect(page.getByRole('heading', { name: /page not found/i })).toBeVisible()),
  },
]

/** Chrome's "Very large" font setting doubles the 16px default. Only relative units follow it. */
async function enlargeText(page: Page) {
  await page.addStyleTag({ content: 'html { font-size: 32px; }' })
}

async function open(page: Page, scenario: Scenario, width: number) {
  await page.setViewportSize({ width, height: HEIGHT })
  await mockApi(page, scenario.api)
  await page.goto(scenario.path)
  await scenario.settled(page)
}

test.describe('no horizontal overflow', () => {
  for (const scenario of scenarios) {
    for (const width of WIDTHS) {
      test(`${scenario.name} at ${width}px`, async ({ page }) => {
        await open(page, scenario, width)
        const report = await measureOverflow(page)
        const label = `${scenario.name} @ ${width}`
        expect(report.overflowBy, formatReport(label, report)).toBeLessThanOrEqual(1)
        expect(report.offscreenControls, formatReport(label, report)).toEqual([])
      })
    }
  }
})

test.describe('no horizontal overflow with enlarged text', () => {
  const enlargedWidths = [320, 390, 768]
  for (const scenario of scenarios) {
    for (const width of enlargedWidths) {
      test(`${scenario.name} at ${width}px, 200% text`, async ({ page }) => {
        await open(page, scenario, width)
        await enlargeText(page)
        const report = await measureOverflow(page)
        const label = `${scenario.name} @ ${width} with 32px root font`
        expect(report.overflowBy, formatReport(label, report)).toBeLessThanOrEqual(1)
        expect(report.offscreenControls, formatReport(label, report)).toEqual([])
      })
    }
  }
})
