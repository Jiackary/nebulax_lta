import { defineConfig, devices } from '@playwright/test'

const executablePath = process.env.PLAYWRIGHT_CHROME_EXECUTABLE

const SCREENSHOTS = /screenshots\.spec\.ts/

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure', ...(executablePath ? { launchOptions: { executablePath } } : {}) },
  projects: [
    // The assertion suite. `npm run test:e2e` runs this one.
    { name: 'mobile-chromium', use: { ...devices['Pixel 5'] }, testIgnore: SCREENSHOTS },
    // Capture only: writes the images the design gates ask to be inspected, asserts nothing.
    { name: 'screens', use: { ...devices['Pixel 5'] }, testMatch: SCREENSHOTS },
  ],
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 5173', url: 'http://127.0.0.1:5173', reuseExistingServer: true },
})
