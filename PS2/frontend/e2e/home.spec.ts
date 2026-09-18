import { expect, test } from '@playwright/test'

test('mobile home page leads clearly into journey planning without horizontal overflow', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Your journey', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /plan journey/i })).toBeVisible()
  expect(await page.locator('html').evaluate((element) => element.scrollWidth <= window.innerWidth)).toBe(true)

  await page.getByRole('link', { name: /plan journey/i }).click()
  await expect(page.getByLabel(/appointment date and time/i)).toBeVisible()
})
