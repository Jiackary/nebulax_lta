// Region stability. The journey page puts optional notices, errors, feedback and warnings
// straight into the layout grid, so at desktop widths a transient message in the first column
// re-flows content in the second — the route map moved 119px because a status check failed.
// Every region keeps a named slot, and an empty one collapses without moving its neighbours.
import { expect, test } from '@playwright/test'

import { FIXTURE_TRIP_ID, mockApi, type MockApiOptions } from './fixtures/mockApi'
import { planReady, savedBundle, statusCurrent, statusDisrupted } from './fixtures/states'

const TRIP = `/trip/${FIXTURE_TRIP_ID}`

const states: { name: string; api: MockApiOptions }[] = [
  { name: 'ready', api: { plan: planReady, status: statusCurrent } },
  {
    name: 'status check failed',
    api: { plan: planReady, status: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'We could not check current conditions.' } },
  },
  { name: 'disrupted', api: { plan: planReady, status: statusDisrupted } },
  {
    name: 'saved offline',
    api: { plan: { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'Offline.' }, savedOffline: savedBundle },
  },
]

async function regionBoxes(width: number, api: MockApiOptions, page: import('@playwright/test').Page) {
  await page.setViewportSize({ width, height: 1400 })
  await mockApi(page, api)
  await page.goto(TRIP)
  await page.locator('.departure-card').waitFor()
  await expect(page.getByRole('heading', { name: /journey steps/i })).toBeVisible()
  return page.evaluate(() => {
    const read = (selector: string) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const rect = element.getBoundingClientRect()
      return { x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width) }
    }
    return {
      summary: read('.journey-summary'),
      overview: read('.journey-overview'),
      directions: read('.journey-directions'),
      actions: read('.journey-actions'),
    }
  })
}

test.describe('the journey regions hold their place at desktop width', () => {
  for (const state of states) {
    test(`${state.name} keeps the overview aligned with the summary`, async ({ page }) => {
      const boxes = await regionBoxes(960, state.api, page)

      expect(boxes.summary, 'summary region is present').not.toBeNull()
      expect(boxes.overview, 'overview region is present').not.toBeNull()
      // The second column starts level with the first, whatever optional content exists.
      expect(boxes.overview!.y).toBe(boxes.summary!.y)
      // Directions continue the first column — same left edge, same measure — so the route
      // map stays beside the steps it illustrates instead of leaving a tall empty band.
      expect(boxes.directions!.x).toBe(boxes.summary!.x)
      expect(boxes.directions!.width).toBe(boxes.summary!.width)
      expect(boxes.directions!.y).toBeGreaterThan(boxes.summary!.y)
      // Actions run the full width underneath both columns.
      expect(boxes.actions!.y).toBeGreaterThan(boxes.directions!.y)
      expect(boxes.actions!.width).toBeGreaterThan(boxes.summary!.width)
    })
  }

  test('a transient notice does not move the second column', async ({ page }) => {
    const ready = await regionBoxes(960, states[0].api, page)
    const failed = await regionBoxes(960, states[1].api, page)

    expect(failed.overview!.x).toBe(ready.overview!.x)
    expect(failed.overview!.y).toBe(ready.overview!.y)
    expect(failed.overview!.width).toBe(ready.overview!.width)
  })
})

test('the journey regions stack in reading order on a phone', async ({ page }) => {
  const boxes = await regionBoxes(390, states[3].api, page)

  expect(boxes.summary!.y).toBeLessThan(boxes.overview!.y)
  expect(boxes.overview!.y).toBeLessThan(boxes.directions!.y)
  expect(boxes.directions!.y).toBeLessThan(boxes.actions!.y)
  for (const box of [boxes.summary!, boxes.overview!, boxes.directions!, boxes.actions!]) {
    expect(box.x).toBe(boxes.summary!.x)
    expect(box.width).toBe(boxes.summary!.width)
  }
})
